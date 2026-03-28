# Stack Research

**Domain:** Flight monitoring SaaS (v2.0 multi-user upgrade)
**Researched:** 2026-03-28
**Confidence:** HIGH

## Scope

This document covers ONLY the new libraries/changes needed for v2.0. The existing stack (FastAPI 0.115.12, SQLAlchemy 2.0.40, APScheduler 3.11.2, Jinja2 3.1.6, Pydantic 2.11.1, SerpAPI, Chart.js, Gunicorn) is validated and unchanged.

For data API layer research (SerpAPI, Amadeus, etc.), see the prior version of this file in git history.

## Recommended Stack Additions

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Authlib | 1.6.x | Google OAuth client (OIDC) | The standard Python OAuth library. Native FastAPI integration via `StarletteOAuth2App`. Handles token exchange, OIDC discovery, JWT validation. More lightweight than fastapi-users for a single-provider scenario. |
| psycopg[binary] | 3.3.x | PostgreSQL driver (psycopg3) | SQLAlchemy 2.0 has a dedicated `psycopg` dialect (separate from psycopg2). Better connection handling, native async support if needed later, actively maintained. The `[binary]` extra bundles compiled C extensions for Render deploy without build tools. |
| Alembic | 1.18.x | Database schema migrations | The only production-grade migration tool for SQLAlchemy. Autogenerate from models, version tracking, upgrade/downgrade. Essential for PostgreSQL (no more `create_all()` in prod). |
| itsdangerous | 2.2.x | Session cookie signing | Already a Starlette dependency (used by SessionMiddleware). Needed for secure server-side session cookies after OAuth login. No extra install, but listing explicitly as it becomes a core auth dependency. |

### Infrastructure

| Technology | Purpose | Why Recommended |
|------------|---------|-----------------|
| Neon.tech (free tier) | Managed PostgreSQL | 0.5 GB storage, 100 CU-hours/month, no expiration, no credit card. Render's free PostgreSQL EXPIRES after 30 days and deletes data after 44 days. Neon.tech is the correct choice for persistent data. |
| Google Cloud Console | OAuth 2.0 credentials | Required for Google OAuth. Create OAuth 2.0 Client ID (Web application type). Free, no billing needed for OAuth-only usage. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-jose[cryptography] | 3.3.x | JWT decode/verify for Google ID tokens | Only if you need to manually verify Google ID tokens outside Authlib's flow. Authlib handles this internally, so likely NOT needed. Listed as optional fallback. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| Alembic CLI | Generate and run migrations | `alembic init`, `alembic revision --autogenerate`, `alembic upgrade head` |

## Installation

```bash
# New core dependencies for v2.0
pip install authlib==1.6.9
pip install "psycopg[binary]==3.3.2"
pip install alembic==1.18.4
pip install itsdangerous==2.2.0
```

New lines for `requirements.txt`:
```
authlib==1.6.9
psycopg[binary]==3.3.2
alembic==1.18.4
itsdangerous==2.2.0
```

## Migration Details: SQLite to PostgreSQL

### database.py Changes

The current `database.py` uses `connect_args={"check_same_thread": False}` which is SQLite-specific. For PostgreSQL:

```python
# BEFORE (SQLite)
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
)

# AFTER (PostgreSQL via Neon.tech)
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,      # Neon.tech closes idle connections aggressively
    pool_recycle=300,         # Recycle connections every 5 min
)
```

### Connection String Format

```
# Neon.tech provides this format:
postgresql+psycopg://user:password@ep-xxx.region.aws.neon.tech/dbname?sslmode=require

# The "+psycopg" dialect tells SQLAlchemy to use psycopg3 (NOT psycopg2)
```

### Model Compatibility

The existing models use `Mapped[]`, `mapped_column()`, `JSON`, `String`, `Integer`, `Float`, `Boolean`, `Date`, `DateTime`, `ForeignKey`. ALL of these are fully compatible with PostgreSQL via SQLAlchemy. No model changes needed for the database migration itself.

The `JSON` column type (used in `RouteGroup.origins` and `RouteGroup.destinations`) maps to PostgreSQL native JSON. Could upgrade to `JSONB` for indexing, but generic `JSON` works and keeps the codebase portable for tests.

### Alembic Setup

```bash
alembic init alembic
# Edit alembic/env.py to import Base.metadata from app.models
# Edit alembic.ini to use DATABASE_URL from environment
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

## OAuth Flow Architecture

### Authlib Integration Pattern

```
1. User clicks "Login with Google" on landing page
2. FastAPI redirects to Google OAuth (via Authlib)
3. Google returns authorization code to callback URL
4. Authlib exchanges code for access token + ID token
5. Extract user info (email, name, picture) from ID token
6. Create or update User record in PostgreSQL
7. Set signed session cookie (via SessionMiddleware + itsdangerous)
8. Redirect to dashboard
```

### Required Google Cloud Console Setup

- OAuth 2.0 Client ID (Web application type)
- Authorized redirect URI: `https://flight-monitor-ly3p.onrender.com/auth/callback`
- For local dev: `http://localhost:8000/auth/callback`
- Scopes: `openid`, `email`, `profile` (standard OIDC, no special approval needed)

### New Environment Variables

```
GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=xxx
SESSION_SECRET_KEY=xxx          # For SessionMiddleware cookie signing
DATABASE_URL=postgresql+psycopg://...  # Neon.tech connection string
```

## Multi-User Data Isolation

### New Model: User

```python
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    google_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    picture_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

### Existing Model Change: RouteGroup

Add `user_id` foreign key to isolate data per user:
```python
user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
```

All queries on `RouteGroup` (and downstream `FlightSnapshot`, `DetectedSignal`) must filter by `user_id` from session. This is the data isolation boundary. No row-level security needed at DB level because all access goes through the application layer.

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| Authlib | fastapi-users | fastapi-users adds user management, password hashing, email verification. All unnecessary for Google-only OAuth. Authlib is lighter and does exactly what we need. |
| Authlib | python-social-auth | Heavier, Django-centric heritage, over-abstracted for a single OAuth provider. |
| psycopg[binary] 3.x | psycopg2-binary | psycopg2 is in maintenance mode. psycopg3 is the actively developed successor with better connection handling and a dedicated SQLAlchemy 2.0 dialect. |
| psycopg[binary] 3.x | asyncpg | Would require rewriting all DB access to async. Current codebase uses sync SQLAlchemy sessions. Not worth the rewrite for this project's scale. |
| Neon.tech | Render PostgreSQL | Render free PostgreSQL EXPIRES after 30 days and deletes data after 44 days. Unacceptable for persistent user data. Neon.tech has no expiration on free tier. |
| Neon.tech | Supabase | Supabase free tier pauses after 1 week of inactivity (cold start delay). Neon.tech scales to zero more gracefully and reconnects faster. |
| Alembic | create_all() | `create_all()` cannot alter existing tables. Multi-user requires adding `user_id` to existing `route_groups`. Alembic is non-negotiable for production PostgreSQL. |
| Session cookies | JWT in localStorage | Server-rendered Jinja2 templates work naturally with cookies. JWT in localStorage requires JavaScript on every page and is vulnerable to XSS. Cookies with httpOnly flag are more secure for this architecture. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| fastapi-users | Adds password reset, email verify, multiple auth backends. All dead weight for Google-only OAuth. | Authlib direct integration |
| python-jose | Authlib already handles JWT internally for OIDC. Adding python-jose duplicates functionality and adds confusion. | Authlib built-in JWT |
| Flask-Dance / social-auth | Flask-specific or overly generic. Not designed for FastAPI/Starlette. | Authlib (framework-agnostic, Starlette-native) |
| psycopg2 / psycopg2-binary | Maintenance mode only. No new features. psycopg3 is the future. | psycopg 3.x |
| Render PostgreSQL (free) | 30-day expiration destroys all data. Grace period is only 14 days. | Neon.tech (no expiration) |
| Neon Auth | Built on Better Auth (JavaScript library). No Python/FastAPI SDK. Designed for Next.js frontends only. | Authlib + Google OAuth directly |
| SQLAlchemy async mode | Would require rewriting all database access patterns, test fixtures, and middleware. Sync works fine at this scale. | Sync SQLAlchemy (current) |
| Any JS framework (React, Vue, etc.) | PROJECT.md constraint: "sem JS framework no frontend". Jinja2 templates are sufficient. | Jinja2 + vanilla JS (current) |

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| psycopg[binary] 3.3.x | SQLAlchemy 2.0.40 | Use dialect `postgresql+psycopg` (NOT `postgresql+psycopg2`) in connection string |
| Alembic 1.18.x | SQLAlchemy 2.0.40 | Requires SQLAlchemy >= 1.4. Uses bulk reflection for PostgreSQL (O(1) queries). |
| Authlib 1.6.x | FastAPI 0.115.x / Starlette | Uses `starlette.config` and `SessionMiddleware`. Requires `httpx` (already in requirements at v0.28.1). |
| itsdangerous 2.2.x | Starlette (bundled) | Already a transitive dependency of Starlette. Pin explicitly for visibility. |

## Sources

- [Authlib PyPI](https://pypi.org/project/Authlib/) - v1.6.9 released 2026-03-02 (HIGH confidence)
- [Authlib FastAPI OAuth Client docs](https://docs.authlib.org/en/latest/client/fastapi.html) - Official integration guide (HIGH confidence)
- [psycopg PyPI](https://pypi.org/project/psycopg/) - v3.3.2 released 2026-02-18 (HIGH confidence)
- [SQLAlchemy PostgreSQL dialects](https://docs.sqlalchemy.org/en/21/dialects/postgresql.html) - psycopg3 dialect documentation (HIGH confidence)
- [Alembic documentation](https://alembic.sqlalchemy.org/en/latest/) - v1.18.4 (HIGH confidence)
- [Neon.tech pricing](https://neon.com/pricing) - Free tier: 0.5 GB, 100 CU-hours/month, no expiration (HIGH confidence)
- [Render free tier docs](https://render.com/docs/free) - PostgreSQL expires after 30 days (HIGH confidence)
- [Neon Auth overview](https://neon.com/docs/auth/overview) - JS-only / Better Auth, not suitable for FastAPI (MEDIUM confidence)
- [Google OAuth 2.0 with FastAPI guide (Feb 2026)](https://manabpokhrel7.medium.com/secure-google-oauth-2-0-integration-with-fastapi-a-comprehensive-guide-2cdb77dcd1e1) - Community tutorial (MEDIUM confidence)

---
*Stack research for: Flight Monitor v2.0 multi-user upgrade*
*Researched: 2026-03-28*
