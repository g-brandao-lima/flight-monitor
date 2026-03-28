# Project Research Summary

**Project:** Flight Monitor v2.0
**Domain:** Multi-user flight price monitoring SaaS (upgrade from single-user v1)
**Researched:** 2026-03-28
**Confidence:** HIGH

## Executive Summary

Flight Monitor v2.0 is a server-rendered SaaS upgrade that adds Google OAuth authentication, PostgreSQL persistence, and multi-user data isolation to an existing single-user FastAPI/Jinja2 app. The research is unambiguous on the approach: the existing stack (FastAPI, SQLAlchemy 2.0, APScheduler, Jinja2, SerpAPI) requires only 4 new dependencies — Authlib for OAuth, psycopg[binary] 3.x for PostgreSQL, Alembic for schema migrations, and itsdangerous (already a transitive dependency) for session signing. All 4 have HIGH-confidence sources and clear integration patterns with the current codebase.

The recommended build order is strictly dependency-driven and non-negotiable: PostgreSQL migration must come first (everything else depends on it), then Google OAuth with the User model, then data isolation with user_id foreign keys, then the public landing page. The PostgreSQL migration is the highest-risk phase because it touches `database.py`, all existing models, and the 188-test suite simultaneously. Neon.tech is the only viable free-tier PostgreSQL host — Render's free PostgreSQL expires after 30 days and would destroy user data.

The critical risk is data leakage between users. The existing codebase has six service files that query `route_groups` without any ownership filter. Adding `user_id` to `RouteGroup` and forgetting to update even one service function means User A sees User B's data. The mitigation is a single `get_user_route_groups(db, user_id)` helper that all services call, plus an explicit two-user isolation test that verifies no endpoint leaks data across accounts. The secondary risk is SerpAPI quota exhaustion: with the current polling model, 9 active users (each with 3 groups, polled every 6 hours) would exhaust the 250 searches/month free tier.

## Key Findings

### Recommended Stack

The v2.0 stack additions are minimal and deliberate. The existing production stack is validated and unchanged. New additions serve exactly one purpose each and were chosen by eliminating heavier alternatives.

**Core technologies:**
- Authlib 1.6.x: Google OAuth OIDC client — lighter than fastapi-users (which adds password reset and email verification, both unnecessary for Google-only auth)
- psycopg[binary] 3.3.x: PostgreSQL driver — psycopg2 is in maintenance mode; psycopg3 has a dedicated SQLAlchemy 2.0 dialect (`postgresql+psycopg`)
- Alembic 1.18.x: Schema migrations — non-negotiable for PostgreSQL; `create_all()` cannot alter existing tables, which blocks adding `user_id` to the existing `route_groups` table
- itsdangerous 2.2.x: Session cookie signing — already a Starlette transitive dependency; becomes explicit for session security

**Infrastructure additions:**
- Neon.tech (free tier): 0.5 GB PostgreSQL, no expiration, auto-suspend with reconnect. Use pooled connection string (`-pooler` hostname) for application code; direct string only for Alembic migrations
- Google Cloud Console: OAuth 2.0 Client ID (Web application). Only `openid`, `email`, `profile` scopes needed — no Google verification review required

**What NOT to use:** fastapi-users, python-jose, asyncpg (requires full async rewrite), Render free PostgreSQL (expires in 30 days), Neon Auth (JavaScript-only, no Python SDK).

See `.planning/research/STACK.md` for full alternatives comparison and version compatibility matrix.

### Expected Features

**Must have for v2.0 launch (table stakes):**
- PostgreSQL on Neon.tech with Alembic migrations — current SQLite is ephemeral on Render; data is lost on every deploy
- Google OAuth login (Authlib) with session persistence via signed cookie
- User model: id, google_id, email, name, picture_url, created_at
- Complete data isolation: `user_id` FK on `route_groups`, all service queries filtered by user_id
- Public landing page with hero section and "Entrar com Google" CTA
- Logout endpoint that clears session
- User avatar and name in dashboard header
- Per-user email alerts (recipient from `user.email`, not hardcoded `settings.gmail_recipient`)
- Auth error handling (redirect to landing with message, not 500 page)

**Should have — add in v2.1 after core validation:**
- "Meus alertas" history page (DetectedSignal table already exists; just needs a new template)
- Shared SerpAPI budget indicator in dashboard (global counter, low implementation effort)
- Demo group seeding on first login (helps new users understand the product immediately)
- "Como funciona" section on landing page

**Defer to v3+:**
- Per-user SerpAPI quota limits (only relevant when user count exceeds 20)
- Admin panel for user management (SQL DELETE suffices until user count exceeds 50)
- Additional OAuth providers
- Amadeus API integration (the original booking class intelligence vision; paused in favor of SerpAPI)
- PWA with push notifications

**Anti-features to reject outright:** email/password registration, real-time WebSocket prices, social sharing, Telegram/WhatsApp alerts, collaborative route groups.

See `.planning/research/FEATURES.md` for full feature prioritization matrix and competitor analysis.

### Architecture Approach

The v2.0 architecture evolves the existing layered FastAPI app by adding a new `app/auth/` module (OAuth client, routes, dependencies), a `User` model with a FK on `RouteGroup`, and a middleware layer (SessionMiddleware + `get_current_user` dependency) that gates all authenticated routes. The app remains server-rendered Jinja2 — no JavaScript framework. Alembic replaces the current `Base.metadata.create_all()` call in the FastAPI lifespan. The polling scheduler does NOT filter by user; it processes all active groups globally and reads the group owner's email from `group.user.email` for alert sending.

**Major components:**
1. `app/auth/` (NEW) — OAuth client setup, `/auth/login` + `/auth/callback` + `/auth/logout` routes, `get_current_user` and `require_auth` FastAPI dependencies
2. `User` model (NEW) — Google identity anchor; FK target for `RouteGroup.user_id`; source of per-user alert email
3. `alembic/` (NEW) — Baseline migration from current schema + user migration; replaces `create_all()`; run as Render build command step before Gunicorn starts
4. `app/routes/landing.py` (NEW) — Public pages separated from authenticated dashboard routes
5. Modified service layer — all 6 service files gain `user_id: int` parameter; all `route_groups` queries add `.where(RouteGroup.user_id == user_id)`
6. Neon.tech connection — `pool_pre_ping=True`, `pool_recycle=300`, pooled connection string to handle serverless cold starts

**Data isolation cascade:** Filtering `RouteGroup.user_id == current_user.id` at the service layer automatically isolates `FlightSnapshot`, `BookingClassSnapshot`, and `DetectedSignal` (all have FK to `route_group_id`). No changes needed to child table models.

**Session pattern:** Store only `user_id` (integer) in the signed session cookie. Never store email, name, or picture in the cookie (signed but not encrypted). Fetch user data from the DB on each request via `get_current_user` dependency.

See `.planning/research/ARCHITECTURE.md` for detailed code examples, file-level change inventory, and anti-patterns.

### Critical Pitfalls

1. **`check_same_thread` crash on PostgreSQL startup** — `connect_args={"check_same_thread": False}` is SQLite-specific; crashes app on startup when `DATABASE_URL` points to PostgreSQL. Fix: conditional `connect_args` based on `database_url.startswith("sqlite")`. Must be the first code change in Phase 1.

2. **Data leakage from incomplete user_id filtering** — Six service files query `route_groups` without an ownership filter today. Missing the filter in any one after the migration is a security incident. Fix: create a single `get_user_route_groups(db, user_id)` helper; write a two-user isolation test that covers every API endpoint and dashboard aggregate query before considering Phase 3 complete.

3. **All 188 existing tests break after adding auth middleware** — Every endpoint returns 401 once `require_auth` is added. Fix: create `conftest.py` auth fixtures that override the dependency with a fake user BEFORE adding auth middleware to any route.

4. **Google OAuth consent screen stuck in "Testing" mode** — New users see "Google hasn't verified this app" warning and cannot log in. Fix: only request non-sensitive scopes (`openid`, `email`, `profile`) which require no review, add a privacy policy page, and publish the consent screen to "Production" in Google Cloud Console before the first public deploy.

5. **SerpAPI quota exhaustion with multiple users** — The scheduler polls all active groups globally. At 9+ users with 3 active groups each, the 250 searches/month free tier is exhausted mid-month. Fix: implement a global quota counter in the database; check remaining budget before each poll cycle; display remaining searches in the dashboard.

6. **Neon.tech cold starts causing connection errors** — Neon free tier suspends after 5 minutes of inactivity; first query after suspend takes 1-2 seconds. Fix: use pooled connection string, set `pool_pre_ping=True` on the engine. UptimeRobot (already configured) provides keepalive mitigation.

7. **JSON mutation tracking bug on PostgreSQL** — In-place list mutations on `RouteGroup.origins` and `RouteGroup.destinations` (SQLAlchemy `JSON` type) are not detected and silently disappear on PostgreSQL. Fix: always assign new lists instead of mutating (`group.origins = [*group.origins, "GRU"]`) or use `MutableList.as_mutable(JSON)`.

See `.planning/research/PITFALLS.md` for full recovery strategies, security mistakes checklist, and pitfall-to-phase mapping.

## Implications for Roadmap

Based on research, the build order is strictly dependency-driven. Four phases emerge with hard dependencies that make parallelization impossible until Phase 4.

### Phase 1: PostgreSQL Foundation

**Rationale:** Every subsequent feature requires PostgreSQL and a `users` table. SQLite cannot persist user records on Render (file system resets on deploy). This phase has no dependencies on other v2.0 work and must be fully validated before proceeding.

**Delivers:** Working FastAPI app on Neon.tech PostgreSQL with Alembic schema management. All existing v1 features (route groups, polling, alerts) verified working on PostgreSQL.

**Addresses:** PostgreSQL persistence (table stakes), Alembic migration management

**Avoids:** Pitfall 1 (`check_same_thread` crash), Pitfall 6 (Neon cold start failures), Pitfall 7 (JSON mutation tracking), Render free PostgreSQL 30-day expiration

**Key tasks:**
- Install psycopg[binary] 3.x and Alembic; add to requirements.txt
- Fix `database.py` conditional `connect_args`; add `pool_pre_ping=True` and `pool_recycle=300`
- Initialize Alembic; create baseline migration from current schema
- Decide on v1 data migration strategy (delete existing rows or assign to bootstrap user)
- Configure Neon.tech; set `DATABASE_URL` env var on Render; use pooled connection string
- Add `alembic upgrade head` to Render build command (before Gunicorn)
- Remove `Base.metadata.create_all()` from lifespan
- Verify all 188 existing tests still pass

### Phase 2: Google OAuth and User Model

**Rationale:** Authentication requires the User table (PostgreSQL must already exist). This phase establishes identity — without it, data isolation is impossible and the landing page has nothing to redirect to.

**Delivers:** Working Google login, session management, user records in PostgreSQL, test infrastructure for authenticated routes.

**Uses:** Authlib 1.6.x, itsdangerous 2.2.x, SessionMiddleware, Google Cloud Console credentials

**Implements:** `app/auth/` module (oauth.py, routes.py, dependencies.py), `User` model, Alembic migration for users table

**Avoids:** Pitfall 3 (test suite breakage — auth fixtures must come FIRST), Pitfall 4 (OAuth consent screen in Testing mode), security mistake of storing OAuth tokens or using email as primary identifier

**Key tasks:**
- Create Google Cloud Console project; configure consent screen in Production mode with privacy policy URL
- Add auth environment variables to config.py and Render env vars
- Create `User` model; generate Alembic migration
- Implement `app/auth/` module (oauth.py, routes.py, dependencies.py)
- Add SessionMiddleware to main.py
- Create `conftest.py` auth fixtures BEFORE adding `require_auth` to any route
- Verify: a Google account NOT on the test user list can log in successfully

### Phase 3: Data Isolation and Multi-user Wiring

**Rationale:** Without this phase, any logged-in user sees all other users' data. This is a security requirement, not a feature enhancement. Must come before any public sharing of the URL.

**Delivers:** Complete per-user data isolation across all API endpoints and dashboard aggregates. Scheduler sends alerts to group owner's email. Global SerpAPI quota counter prevents over-polling. Two-user isolation test proves no data leaks.

**Avoids:** Pitfall 2 (data leakage), global Gmail recipient bug, Pitfall 5 (SerpAPI quota exhaustion)

**Key tasks:**
- Add `user_id` FK to `RouteGroup`; generate Alembic migration
- Create `get_user_route_groups(db, user_id)` helper function
- Add `user_id: int` parameter to all 6 service files; apply `user_id` filter to all `route_groups` queries
- Add `Depends(require_auth)` to all dashboard and route group route handlers
- Update alert_service to use `group.user.email` as recipient (not `settings.gmail_recipient`)
- Implement global SerpAPI quota counter in DB; check before each poll cycle
- Write two-user isolation test covering all API endpoints and dashboard aggregates
- Verify: User A cannot see User B's groups, snapshots, or signals through any route

### Phase 4: Public Landing Page and UX Polish

**Rationale:** Can be partially developed in parallel with Phase 3 (HTML/CSS work has no backend dependencies). The logout endpoint and header avatar require Phase 2 to be complete. Must exist before sharing the URL publicly.

**Delivers:** Public landing page with hero, value proposition, "Entrar com Google" CTA, mobile-responsive layout. User avatar and name in authenticated dashboard header. Auth error handling. Logout button on every page.

**Addresses:** Landing page (table stakes), mobile-responsive design, user avatar in header, logout endpoint, error handling on auth failure

**Key tasks:**
- Create `app/routes/landing.py` and `templates/landing/index.html`
- Update `base.html` header for auth-aware navigation (avatar + logout when logged in; login link when not)
- Create auth error template (redirect from OAuth callback on failure)
- Add OG meta tags (`og:title`, `og:description`, `og:image`)
- Verify Google consent screen is in Production mode before sharing URL

### Phase Ordering Rationale

- Phase 1 before Phase 2: Alembic and the `users` table must exist before OAuth can store user records; psycopg3 must be installed before the `User` model can be tested
- Phase 2 before Phase 3: The `require_auth` dependency provides `current_user.id` that Phase 3 uses for filtering; without an authenticated user identity there is no `user_id` to filter by
- Phase 3 before public launch: Data isolation is a security requirement; shipping without it means a logged-in user can access any other user's data through the existing API endpoints
- Phase 4 overlaps Phase 3 (HTML/CSS only): Static landing page content has no database or auth dependencies; only the header avatar and logout endpoint require Phase 2 to be complete first

### Research Flags

Phases with standard, well-documented patterns (skip `/gsd:research-phase`):
- **Phase 1 (PostgreSQL Foundation):** Alembic and psycopg3 are well-documented. The `database.py` changes are prescriptive and fully specified in ARCHITECTURE.md. The conditional `connect_args` pattern is established.
- **Phase 4 (Landing Page):** Pure Jinja2 and CSS work. No novel integration required.

Phases that warrant targeted investigation during planning:
- **Phase 2 (Google OAuth):** The Authlib integration pattern is documented, but Google Cloud Console setup (especially publishing the consent screen with a privacy policy URL, and configuring redirect URIs for both local dev and Render production) has real-world gotchas documented in PITFALLS.md. Recommend tracing through the full OAuth flow in a dev environment before writing tests.
- **Phase 3 (Data Isolation):** The SerpAPI quota counter needs a concrete schema decision (simple monthly counter row vs. per-poll audit log) before implementation. The fairness policy for multi-user polling order (random, round-robin, priority by travel date) is an open question that affects the scheduler modification.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All 4 new dependencies verified against official docs and PyPI release dates. Alternatives rigorously compared and rejected with documented reasoning. Version compatibility matrix validated. |
| Features | HIGH | MVP feature set derived from hard dependency analysis and competitor comparison. Anti-features clearly reasoned with explicit rejections. Table stakes vs. differentiators cleanly separated. |
| Architecture | HIGH | Build order is dependency-driven, not opinion-driven. Code examples for all 3 major patterns are production-grade. File-level change inventory is explicit (every modified file listed). |
| Pitfalls | HIGH | Based on codebase inspection of actual project files (`app/database.py`, `app/models.py`, `app/config.py`) plus verified documentation. Pitfalls mapped to specific phases with recovery cost estimates. |

**Overall confidence:** HIGH

### Gaps to Address

- **Data migration strategy for existing v1 data:** Existing `route_groups` rows have no `user_id`. The Alembic migration must handle making `user_id` non-nullable. Decision needed before Phase 1 Alembic setup: (a) delete all v1 data during migration — acceptable since it is single-user dev data with no other users — or (b) assign all existing rows to a bootstrap user created during migration. This decision gates Phase 1 completion.

- **SerpAPI quota counter schema:** Research recommends implementing a global quota counter but does not specify the schema. Options: a simple `api_usage` table with a monthly counter row vs. per-poll audit logging. This needs a concrete decision in Phase 3 planning before implementation begins.

- **Neon PgBouncer prepared statement compatibility:** PITFALLS.md flags that using PgBouncer in transaction mode requires `statement_cache_size=0` in engine connect_args (or `NullPool`) to avoid `InvalidCachedStatementError`. This must be tested in Phase 1 with the actual Neon pooled connection string before finalizing the engine configuration.

- **Scheduler fairness policy:** When multiple users have active groups and SerpAPI quota is limited, some users' groups will not be polled if quota runs out mid-cycle. The fairness policy (random order, round-robin, priority by travel date proximity) is undecided and needs resolution in Phase 3.

## Sources

### Primary (HIGH confidence)
- [Authlib PyPI + official FastAPI docs](https://docs.authlib.org/en/latest/client/fastapi.html) — OAuth OIDC integration pattern
- [psycopg PyPI](https://pypi.org/project/psycopg/) — psycopg3 dialect for SQLAlchemy 2.0
- [Alembic documentation](https://alembic.sqlalchemy.org/en/latest/) — migration setup and autogenerate
- [Neon.tech pricing and free plan](https://neon.com/pricing) — 0.5 GB, no expiration confirmed
- [Render free tier docs](https://render.com/docs/free) — PostgreSQL 30-day expiration confirmed
- [SQLAlchemy PostgreSQL dialect docs](https://docs.sqlalchemy.org/en/21/dialects/postgresql.html) — psycopg3 dialect string
- [Neon.tech connection pooling docs](https://neon.com/docs/connect/connection-pooling) — pooled connection string and PgBouncer behavior
- [Google OAuth consent screen setup](https://support.google.com/cloud/answer/10311615?hl=en) — non-sensitive scopes require no Google review
- Codebase inspection: `app/database.py`, `app/models.py`, `app/config.py`, 6 service files (verified 2026-03-28)

### Secondary (MEDIUM confidence)
- [Google OAuth 2.0 with FastAPI guide (Feb 2026)](https://manabpokhrel7.medium.com/secure-google-oauth-2-0-integration-with-fastapi-a-comprehensive-guide-2cdb77dcd1e1) — community tutorial, corroborates Authlib docs
- [Multitenancy with FastAPI, SQLAlchemy and PostgreSQL](https://mergeboard.com/blog/6-multitenancy-fastapi-sqlalchemy-postgresql/) — shared schema multi-tenancy patterns
- [FastAPI Multi-Tenant Design Patterns (March 2026)](https://blog.greeden.me/en/2026/03/10/introduction-to-multi-tenant-design-with-fastapi-practical-patterns-for-tenant-isolation-authorization-database-strategy-and-audit-logs/) — current best practices
- [Beware of JSON fields in SQLAlchemy](https://amercader.net/blog/beware-of-json-fields-in-sqlalchemy/) — JSON mutation tracking issue

### Tertiary (LOW confidence)
- [Neon Auth overview](https://neon.com/docs/auth/overview) — determined to be JavaScript-only, not suitable; listed to document the rejection
- [Nile.dev: Shipping multi-tenant SaaS using Postgres RLS](https://www.thenile.dev/blog/multi-tenant-rls) — Row-Level Security approach considered and rejected as overkill for this scale

---
*Research completed: 2026-03-28*
*Ready for roadmap: yes*
