# Architecture Research

**Domain:** Flight price monitoring SaaS (multi-user evolution from single-user v1)
**Researched:** 2026-03-28
**Confidence:** HIGH

## System Overview (v2.0 Target)

```
                         INTERNET
                            |
                   +-----------------+
                   |  Render (Web)   |
                   +-----------------+
                            |
                   +-----------------+
                   |  Gunicorn/Uvi   |
                   +-----------------+
                            |
+---------------------------------------------------------------+
|                       FastAPI App                              |
|                                                                |
|  +-----------+  +------------+  +----------+  +----------+    |
|  | Landing   |  | Auth       |  | Dashboard|  | API v1   |    |
|  | (public)  |  | (OAuth)    |  | (authed) |  | (authed) |    |
|  +-----------+  +-----+------+  +----+-----+  +----+-----+    |
|                       |              |              |           |
|                  +----v--------------v--------------v----+     |
|                  |         Middleware Layer               |     |
|                  |  SessionMiddleware + get_current_user  |     |
|                  +----+----------------------------------+     |
|                       |                                        |
|  +--------------------v--------------------------------------+ |
|  |              Service Layer                                | |
|  |  dashboard_service  polling_service  signal_service  ...  | |
|  |  (all queries now filtered by user_id)                    | |
|  +----+------------------------------------------------------+ |
|       |                                                        |
|  +----v------------------------------------------------------+ |
|  |              SQLAlchemy ORM + Alembic                     | |
|  |  User  RouteGroup  FlightSnapshot  DetectedSignal  ...   | |
|  +----+------------------------------------------------------+ |
+-------|--------------------------------------------------------+
        |
+-------v---------+     +------------------+
|  Neon.tech       |     |  Google OAuth    |
|  PostgreSQL      |     |  (accounts.      |
|  (persistent)    |     |   google.com)    |
+------------------+     +------------------+
```

## Component Responsibilities

| Component | Responsibility | New vs Modified |
|-----------|----------------|-----------------|
| Landing page routes | Public pages (about, login button) | NEW |
| Auth routes | OAuth flow (login, callback, logout) | NEW |
| User model | Store Google profile, link to data | NEW |
| SessionMiddleware | Signed cookie for login state | NEW |
| get_current_user dependency | Extract user from session, inject into routes | NEW |
| Dashboard routes | HTML pages for authenticated users | MODIFIED (add auth dependency) |
| API v1 routes | JSON API for authenticated users | MODIFIED (add auth dependency) |
| RouteGroup model | Add user_id foreign key | MODIFIED |
| Service layer | Filter all queries by user_id | MODIFIED |
| database.py | Switch engine URL to PostgreSQL, conditional connect_args | MODIFIED |
| config.py | Add OAuth and PostgreSQL settings | MODIFIED |
| Alembic | Schema versioning and migration | NEW |
| Scheduler | Poll for all users' active groups | MODIFIED (iterate users) |

## Recommended Project Structure (v2.0 changes)

```
flight-monitor/
├── main.py                    # MODIFIED: add SessionMiddleware, landing router
├── alembic.ini                # NEW: Alembic config
├── alembic/                   # NEW: migration scripts
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 001_initial.py     # baseline from current schema
├── app/
│   ├── __init__.py
│   ├── config.py              # MODIFIED: add google_client_id, google_client_secret, etc.
│   ├── database.py            # MODIFIED: remove check_same_thread, use DATABASE_URL
│   ├── models.py              # MODIFIED: add User model, user_id FK on RouteGroup
│   ├── schemas.py             # MODIFIED: user-aware schemas
│   ├── scheduler.py           # MODIFIED: query all users' groups
│   ├── auth/                  # NEW: entire module
│   │   ├── __init__.py
│   │   ├── oauth.py           # Authlib OAuth client setup
│   │   ├── routes.py          # /auth/login, /auth/callback, /auth/logout
│   │   └── dependencies.py    # get_current_user, require_auth
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── landing.py         # NEW: public pages
│   │   ├── dashboard.py       # MODIFIED: add Depends(require_auth)
│   │   ├── route_groups.py    # MODIFIED: filter by user_id
│   │   └── alerts.py          # MODIFIED: filter by user_id
│   ├── services/              # MODIFIED: all accept user_id parameter
│   │   ├── ...existing...
│   │   └── user_service.py    # NEW: find_or_create_user
│   └── templates/
│       ├── base.html           # MODIFIED: show user avatar/logout in header
│       ├── landing/            # NEW
│       │   └── index.html      # Public landing page
│       ├── dashboard/          # MODIFIED: minor auth-aware tweaks
│       │   ├── index.html
│       │   ├── detail.html
│       │   ├── create.html
│       │   └── edit.html
│       └── error.html
```

### Structure Rationale

- **app/auth/**: Isolated auth module. OAuth logic, routes, and dependencies in one place. Easy to test independently and swap providers later.
- **app/routes/landing.py**: Public routes separated from authenticated dashboard routes. Clear boundary between what requires login and what does not.
- **alembic/**: Standard Alembic layout at project root. Required for PostgreSQL migration and ongoing schema evolution.

## Architectural Patterns

### Pattern 1: Session-Based Auth via Authlib + Starlette SessionMiddleware

**What:** Use Authlib's OAuth client with Starlette's SessionMiddleware to handle Google login. The session cookie stores the user ID after successful OAuth callback. No JWT needed for server-rendered pages.

**When to use:** Server-rendered apps (Jinja2 templates) where the browser is the only client. Simpler than JWT for this use case.

**Trade-offs:** Simpler than JWT but requires server-side session storage (cookie is signed, not encrypted, so only store user ID). Session middleware requires a secret key.

**Example:**

```python
# app/auth/oauth.py
from authlib.integrations.starlette_client import OAuth
from app.config import settings

oauth = OAuth()
oauth.register(
    name="google",
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)
```

```python
# app/auth/routes.py
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.auth.oauth import oauth
from app.services.user_service import find_or_create_user
from app.database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])

@router.get("/login")
async def login(request: Request):
    redirect_uri = request.url_for("auth_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get("/callback")
async def auth_callback(request: Request, db: Session = Depends(get_db)):
    token = await oauth.google.authorize_access_token(request)
    userinfo = token.get("userinfo")
    user = find_or_create_user(db, userinfo)
    request.session["user_id"] = user.id
    return RedirectResponse(url="/")

@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/landing")
```

```python
# app/auth/dependencies.py
from fastapi import Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User

def get_current_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return db.get(User, user_id)

def require_auth(request: Request, db: Session = Depends(get_db)) -> User:
    user = get_current_user(request, db)
    if not user:
        # For HTML routes, redirect to login
        raise HTTPException(status_code=303, headers={"Location": "/auth/login"})
    return user
```

```python
# main.py addition
from starlette.middleware.sessions import SessionMiddleware
app.add_middleware(SessionMiddleware, secret_key=settings.session_secret)
```

**Confidence:** HIGH. Authlib + SessionMiddleware is the standard pattern for FastAPI server-rendered Google OAuth. Confirmed by official Authlib docs and multiple 2025/2026 guides.

### Pattern 2: User ID Foreign Key for Data Isolation (Shared Schema)

**What:** Add `user_id` column to `RouteGroup`. Since all other tables (FlightSnapshot, DetectedSignal, BookingClassSnapshot) already reference RouteGroup via foreign key, filtering RouteGroup by user_id automatically isolates all downstream data.

**When to use:** Small multi-tenant apps with a single shared database. This project has a flat ownership hierarchy (user owns groups, groups own snapshots).

**Trade-offs:** Simple and effective. No need for PostgreSQL Row-Level Security (overkill for this scale). Requires discipline in always filtering by user_id, but the existing architecture already funnels through service functions.

**Example:**

```python
# app/models.py - New User model
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    google_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    picture_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

# app/models.py - Modified RouteGroup (add user_id)
class RouteGroup(Base):
    __tablename__ = "route_groups"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)  # NEW
    # ...rest of existing columns unchanged...

    user: Mapped["User"] = relationship("User", backref="route_groups")  # NEW
```

**Data isolation cascade:**
```
User (user_id filter applied here)
  └── RouteGroup (has user_id FK)
        ├── FlightSnapshot (FK to route_group)
        │     └── BookingClassSnapshot (FK to flight_snapshot)
        └── DetectedSignal (FK to route_group)
```

Filtering `RouteGroup.user_id == current_user.id` in every service function isolates the entire data tree. No changes needed to FlightSnapshot, BookingClassSnapshot, or DetectedSignal models.

**Confidence:** HIGH. Standard shared-schema multi-tenancy. The existing FK chain makes this clean.

### Pattern 3: Alembic for Database Migration (SQLite to PostgreSQL)

**What:** Replace `Base.metadata.create_all()` with Alembic-managed migrations. Create a baseline migration from the current schema, then add subsequent migrations for User model and user_id FK.

**When to use:** Any project moving beyond SQLite or needing schema evolution tracking.

**Trade-offs:** Adds a migration step to deployment, but eliminates the "drop and recreate" fragility of create_all(). Required for PostgreSQL in production.

**Migration strategy:**

1. Initialize Alembic (`alembic init alembic`)
2. Configure `alembic/env.py` to import `Base` and use `settings.database_url`
3. Create baseline migration: `alembic revision --autogenerate -m "baseline v1"`
4. Create user migration: `alembic revision --autogenerate -m "add users table and user_id to route_groups"`
5. Remove `Base.metadata.create_all(bind=engine)` from lifespan
6. Run `alembic upgrade head` on deployment

**Database URL change in config.py:**

```python
class Settings(BaseSettings):
    database_url: str = "sqlite:///./flight_monitor.db"  # Keep SQLite for local dev
    session_secret: str = "change-me-in-production"
    google_client_id: str = ""
    google_client_secret: str = ""
    # ...existing fields unchanged...
```

**database.py change:**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import settings

connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

**Confidence:** HIGH. Alembic is the de facto standard for SQLAlchemy migrations. The conditional connect_args pattern is well-established for supporting both SQLite (dev) and PostgreSQL (prod).

## Data Flow

### OAuth Login Flow

```
User clicks "Login with Google"
    |
    v
GET /auth/login
    |
    v
Authlib redirects to accounts.google.com
    |
    v
User authorizes, Google redirects to /auth/callback?code=XXX
    |
    v
GET /auth/callback
    |-- Authlib exchanges code for token (server-to-server)
    |-- Extract userinfo (email, name, picture, google_id)
    |-- find_or_create_user(db, userinfo) -> User
    |-- request.session["user_id"] = user.id
    v
RedirectResponse(url="/")  -> dashboard (now authenticated)
```

### Authenticated Request Flow

```
Browser sends request with session cookie
    |
    v
SessionMiddleware decodes cookie -> request.session["user_id"]
    |
    v
require_auth dependency -> db.get(User, user_id)
    |
    v
Route handler receives `user: User` via Depends
    |
    v
Service function called with user_id filter
    |
    v
SQLAlchemy query: WHERE route_groups.user_id = :user_id
    |
    v
Template rendered with user-specific data + user info in context
```

### Polling Service Flow (Modified)

```
APScheduler triggers run_polling_cycle()
    |
    v
Query ALL active RouteGroups (across all users)
    |
    v
For each group: call SerpAPI, create snapshots, detect signals
    |
    v
If signal detected: send email to group.user.email (not global config)
```

Key change: The polling service itself does NOT filter by user. It processes all active groups globally. The user isolation is only for the web interface. Email alerts use the group owner's email address (from User model) instead of a global config variable.

## Integration Points with Existing Code

### Changes per File (Explicit Inventory)

**main.py (3 changes):**
1. Add `SessionMiddleware` with secret key
2. Include `landing_router` and `auth_router`
3. Remove `Base.metadata.create_all(bind=engine)` (Alembic handles this)

**app/config.py (4 new settings):**
- `session_secret`: For SessionMiddleware signing
- `google_client_id`: From Google Cloud Console
- `google_client_secret`: From Google Cloud Console
- `database_url` default stays SQLite for local dev; Render env var overrides to PostgreSQL

**app/database.py (1 change):**
- Conditional `check_same_thread` based on database URL prefix

**app/models.py (2 changes):**
- Add `User` model (new class)
- Add `user_id` FK + relationship to `RouteGroup` (new column)

**app/routes/dashboard.py (all route handlers modified):**
- Add `user: User = Depends(require_auth)` to every route
- Pass `user.id` to service functions
- Pass `user` to template context (for header avatar/name)

**app/routes/route_groups.py (all route handlers modified):**
- Add `user: User = Depends(require_auth)` to every route
- Filter queries by `user_id`
- Set `user_id` on new RouteGroup creation

**app/services/dashboard_service.py (all functions modified):**
- Add `user_id: int` parameter to `get_groups_with_summary`, `get_dashboard_summary`, `get_recent_activity`
- Add `.where(RouteGroup.user_id == user_id)` to all queries

**app/services/route_group_service.py:**
- `check_active_group_limit`: filter by user_id (per-user limit, not global)

**app/services/alert_service.py:**
- Send to `group.user.email` instead of `settings.gmail_recipient`
- Eagerly load user relationship when fetching groups for polling

**app/templates/base.html:**
- Header: show user avatar + name + logout link when `user` is in context
- Header: show "Login" link when on public pages

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Google OAuth | Authlib OAuth client, server-to-server token exchange | Requires Google Cloud Console project with OAuth consent screen and authorized redirect URI (`/auth/callback`) |
| Neon.tech PostgreSQL | SQLAlchemy engine with `postgresql+psycopg2://` URL | Free tier: 0.5 GB storage, auto-suspend after 5 min idle, cold start around 1-2s |
| SerpAPI | Unchanged from v1 | Shared free tier across all users (250 searches/month total) |
| Gmail SMTP | Modified: per-user recipient from User.email | Sender still uses app's Gmail credentials |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Auth module -> Routes | `Depends(require_auth)` returns User or redirects | All authenticated routes use this dependency |
| Routes -> Services | Function call with explicit user_id param | All service functions gain user_id parameter |
| Scheduler -> Services | Direct function call (no user context) | Polls all users' groups globally, no auth needed |
| Landing -> Dashboard | Redirect after OAuth callback | `/landing` (public) -> `/auth/login` -> Google -> `/auth/callback` -> `/` (private) |

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 1-50 users | Current design is sufficient. Neon free tier handles it. SerpAPI free tier is the bottleneck (250 searches/month shared). |
| 50-500 users | Need paid SerpAPI. Consider per-user polling quotas. Neon paid tier for more storage. |
| 500+ users | Background worker (Celery/RQ) instead of embedded APScheduler. Connection pooling. Rate limiting per user. |

### First Bottleneck: SerpAPI Free Tier

250 searches/month shared across ALL users. With daily polling and 3 active groups per user, 10 users would need around 900 searches/month. This hits the wall at roughly 8-9 active users.

**Mitigation:** Display remaining API quota on dashboard. Implement per-user group limits lower than the global 10. Consider Amadeus API as primary source (2,000 calls/month free).

### Second Bottleneck: Neon Cold Start

Neon free tier auto-suspends after 5 min of inactivity. First request after suspend takes 1-2 seconds. With UptimeRobot pinging every 5 min, this is mostly mitigated but not fully.

**Mitigation:** UptimeRobot keep-alive already exists. Landing page can be served without DB access (static content). Auth callback is the first DB-heavy hit after cold start; 1-2s is acceptable there.

## Anti-Patterns

### Anti-Pattern 1: Storing User Data in Session Cookie

**What people do:** Store email, name, picture URL in the session cookie directly.
**Why it is wrong:** Starlette SessionMiddleware signs but does not encrypt the cookie. Anyone can base64-decode and read the data. Cookie size grows. Data goes stale if user updates their Google profile.
**Do this instead:** Store only `user_id` (integer) in the session. Fetch user data from DB on each request via `get_current_user` dependency.

### Anti-Pattern 2: Filtering by user_id Only in Routes

**What people do:** Add user_id filtering in route handlers but not in service functions.
**Why it is wrong:** Any new route or internal call that skips the filter leaks data across users. The polling service calls service functions directly.
**Do this instead:** Make user_id a required parameter in all service functions that return user-specific data. The route handler passes it, the service enforces it. The scheduler calls separate "all groups" queries that do not go through user-filtered service functions.

### Anti-Pattern 3: Running Alembic Migrations in App Startup

**What people do:** Put `alembic upgrade head` inside the FastAPI lifespan.
**Why it is wrong:** Race condition with multiple Gunicorn workers. Migration errors crash the app. Migrations should be intentional, not automatic.
**Do this instead:** Run `alembic upgrade head` as a separate step in the Render build command (before `gunicorn` starts). Example build command: `pip install -r requirements.txt && alembic upgrade head`.

### Anti-Pattern 4: Global Gmail Recipient for Multi-User Alerts

**What people do:** Keep `settings.gmail_recipient` as the alert target for all users.
**Why it is wrong:** All users' alerts go to one email address (the app owner's).
**Do this instead:** Use `user.email` from the User model. The Gmail SMTP sender remains global (the app's Gmail account sends on behalf of the system), but the recipient is the group owner's email.

## Build Order (Dependency-Driven)

The features have hard dependencies that dictate build order:

```
1. PostgreSQL + Alembic       (no dependencies, foundational)
   |
2. User model + Auth (OAuth)  (requires PostgreSQL for User table)
   |
3. Data isolation (user_id)   (requires User model to exist)
   |
4. Landing page               (requires auth to exist for login redirect)
```

**Phase 1: PostgreSQL + Alembic** - Change database.py, config.py, init Alembic, create baseline migration, test locally with PostgreSQL (Docker or local install), deploy to Neon.

**Phase 2: User model + Google OAuth** - Create User model, Alembic migration, auth module (oauth.py, routes.py, dependencies.py), SessionMiddleware, Google Cloud Console setup.

**Phase 3: Data isolation** - Add user_id to RouteGroup (Alembic migration), modify all services and routes to filter by user_id, modify scheduler to use user email for alerts.

**Phase 4: Landing page** - Create public landing page template, landing routes, modify base.html header for auth-aware navigation.

Phases 3 and 4 can be parallelized if needed, but Phase 3 is higher priority (security concern: without user_id filtering, any logged-in user sees all data).

## Sources

- [Authlib FastAPI OAuth Client docs](https://docs.authlib.org/en/latest/client/fastapi.html) - Official Authlib documentation (HIGH confidence, verified against multiple sources)
- [Google OAuth 2.0 Integration with FastAPI (Feb 2026)](https://manabpokhrel7.medium.com/secure-google-oauth-2-0-integration-with-fastapi-a-comprehensive-guide-2cdb77dcd1e1) - Recent comprehensive guide
- [Multitenancy with FastAPI, SQLAlchemy and PostgreSQL](https://mergeboard.com/blog/6-multitenancy-fastapi-sqlalchemy-postgresql/) - Shared schema multi-tenancy patterns
- [FastAPI Multi-Tenant Design Patterns (March 2026)](https://blog.greeden.me/en/2026/03/10/introduction-to-multi-tenant-design-with-fastapi-practical-patterns-for-tenant-isolation-authorization-database-strategy-and-audit-logs/) - Current best practices
- [Alembic with FastAPI and PostgreSQL guide](https://medium.com/@rajeshpachaikani/using-alembic-with-fastapi-and-postgresql-no-bullshit-guide-b564ae89f4be) - Practical setup
- [FastAPI GitHub Discussion #6056: Multi-tenancy](https://github.com/fastapi/fastapi/discussions/6056) - Community patterns

---
*Architecture research for: Flight Monitor v2.0 multi-user evolution*
*Researched: 2026-03-28*
