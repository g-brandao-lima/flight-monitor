# Pitfalls Research

**Domain:** Adding Google OAuth, PostgreSQL migration, and multi-user isolation to existing single-user FastAPI app
**Researched:** 2026-03-28
**Confidence:** HIGH (based on codebase inspection + verified documentation)

## Critical Pitfalls

### Pitfall 1: check_same_thread Breaks PostgreSQL Connection

**What goes wrong:**
The current `app/database.py` passes `connect_args={"check_same_thread": False}` to `create_engine()`. This parameter is SQLite-specific. When the DATABASE_URL switches to PostgreSQL, psycopg2 raises `ProgrammingError: invalid connection option 'check_same_thread'` and the app crashes on startup.

**Why it happens:**
The FastAPI tutorial itself recommends `check_same_thread=False` for SQLite. Developers copy this pattern and forget it is dialect-specific. When they change only the DATABASE_URL env var to point to PostgreSQL, the connect_args are still passed through.

**How to avoid:**
Conditionally apply connect_args based on the database dialect:
```python
connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
engine = create_engine(settings.database_url, connect_args=connect_args)
```
This must be done in the same commit that adds PostgreSQL support, not after.

**Warning signs:**
App fails to start with a cryptic psycopg2 error about "invalid dsn" or "unexpected keyword argument."

**Phase to address:**
Database migration phase (first phase of v2.0). This is the very first line of code to change.

---

### Pitfall 2: JSON Columns Silently Behave Differently in PostgreSQL

**What goes wrong:**
The `RouteGroup` model uses `mapped_column(JSON)` for `origins` and `destinations`. In SQLite, JSON is stored as text with no indexing or querying capability. In PostgreSQL, SQLAlchemy's `JSON` type maps to native JSON, but the real power is in `JSONB`. More critically, mutation tracking for JSON fields does not work by default in SQLAlchemy. If you modify a list in-place (e.g., `group.origins.append("GRU")`), SQLAlchemy will not detect the change and will not flush it to the database.

**Why it happens:**
SQLAlchemy's `JSON` type does not track in-place mutations. This "works" in SQLite during development because the test patterns tend to replace entire values, not mutate them. In PostgreSQL with connection pooling, stale reads become more visible.

**How to avoid:**
1. Keep using `sqlalchemy.JSON` (it adapts per dialect automatically). Do not switch to `JSONB` explicitly unless you need JSON path queries.
2. Use `MutableList.as_mutable(JSON)` from `sqlalchemy.ext.mutable` to enable change detection on list fields.
3. Alternatively, always assign new lists instead of mutating: `group.origins = [*group.origins, "GRU"]`.

**Warning signs:**
Updates to origins/destinations "disappear" after save. Tests pass locally (SQLite) but fail in staging (PostgreSQL) due to unflushed mutations.

**Phase to address:**
Database migration phase. Must be addressed in the model changes, not deferred.

---

### Pitfall 3: Missing user_id on Every Existing Table Causes Data Leakage

**What goes wrong:**
The current schema has no concept of ownership. `RouteGroup`, `FlightSnapshot`, `DetectedSignal`, and `BookingClassSnapshot` have no `user_id` column. If you add users but forget to add `user_id` to even one table, or forget to filter by `user_id` in even one query, User A sees User B's data.

**Why it happens:**
Adding a column is easy. The hard part is ensuring every single query path filters by it. In this codebase, `route_group_service.py`, `snapshot_service.py`, `signal_service.py`, `dashboard_service.py`, `polling_service.py`, and `alert_service.py` all query route_groups or related tables. Missing the filter in any one of them is a data leak.

**How to avoid:**
1. Add `user_id` as a non-nullable foreign key to `route_groups` only. Child tables (`flight_snapshots`, `booking_class_snapshots`, `detected_signals`) inherit isolation through `route_group_id`.
2. Create a helper function like `get_user_route_groups(db, user_id)` that all services call, so there is exactly one place where the filter lives.
3. Write a test that creates data for two users and verifies User A cannot see User B's groups, snapshots, or signals through any API endpoint.

**Warning signs:**
Any query on `route_groups` that does not include `WHERE user_id = :current_user`. The dashboard endpoint showing "all groups" instead of "my groups."

**Phase to address:**
Multi-user isolation phase. Must be a dedicated phase AFTER auth works, specifically focused on data isolation with explicit tests.

---

### Pitfall 4: Google OAuth Consent Screen Stuck in "Testing" Mode

**What goes wrong:**
Google's OAuth consent screen defaults to "Testing" status, which limits login to 100 manually-added test users. Refresh tokens expire after 7 days. When you share the app URL publicly, new users see a scary "This app isn't verified" warning and cannot proceed unless they are on the test user list.

**Why it happens:**
Developers set up OAuth in testing mode during development and forget to publish it. Publishing requires setting up a privacy policy URL, terms of service URL, and an authorized domain. For sensitive scopes (like reading email), Google requires a full review that takes weeks.

**How to avoid:**
1. Only request `openid`, `email`, and `profile` scopes. These are non-sensitive and do not require Google verification review.
2. Set up a privacy policy page (can be a simple static page on the landing) from day one.
3. Publish the consent screen to "Production" in Google Cloud Console before the first public deploy. With non-sensitive scopes, this is instant (no review needed).
4. Use a proper domain (not localhost) for the authorized redirect URI in production.

**Warning signs:**
Login works for you but fails for anyone else. Users report seeing "Google hasn't verified this app" screen.

**Phase to address:**
Auth phase. The Google Cloud Console project must be configured with production settings before the landing page goes live.

---

### Pitfall 5: APScheduler Polls for ALL Users' Groups, Exhausting SerpAPI Quota

**What goes wrong:**
The current scheduler polls all active groups every 6 hours via a single CronTrigger. When multiple users create groups, the total active groups across all users can quickly exceed the SerpAPI free tier (250 searches/month). With 10 users having 3 active groups each, that is 30 groups x 4 polls/day x 30 days = 3,600 searches/month (14x over the limit).

**Why it happens:**
The single-user design assumed one user's 10 groups max. Multi-user multiplies this. The scheduler has no concept of a global quota budget.

**How to avoid:**
1. Implement a global daily/monthly quota counter in the database. Before each poll, check remaining budget.
2. Reduce polling frequency as user count grows. Priority-based scheduling: groups with active signals or approaching travel dates get polled more often.
3. Set a system-wide cap on total active groups (e.g., 30 across all users) and show a "system at capacity" message when reached.
4. Consider a per-user active group limit lower than 10 (e.g., 3-5 per user).

**Warning signs:**
SerpAPI returns 429 errors or "quota exceeded" mid-month. Multiple users complain about stale data.

**Phase to address:**
Multi-user phase (quota management). Must be designed before launch, not after the first month's bill.

---

### Pitfall 6: Neon.tech Cold Starts Break Scheduler and UptimeRobot

**What goes wrong:**
Neon's free tier suspends compute after 5 minutes of inactivity. When the APScheduler CronTrigger fires (or UptimeRobot pings), the first database query takes 500ms-2s while Neon wakes up. If the application has a short timeout or the scheduler expects instant responses, polls can fail or timeout.

**Why it happens:**
Neon's serverless model scales to zero to save resources. The app was designed for a local SQLite file that is always available.

**How to avoid:**
1. Use Neon's pooled connection string (with PgBouncer, the `-pooler` hostname suffix) instead of the direct connection string. This masks most cold starts.
2. Set SQLAlchemy's `pool_pre_ping=True` to handle stale connections after Neon suspends.
3. Add a retry with short delay on the scheduler's database calls.
4. UptimeRobot's 5-minute interval should keep Neon warm most of the time, but be aware of edge cases.

**Warning signs:**
Intermittent `ConnectionError` or `OperationalError` in logs, especially in the early morning or after quiet periods.

**Phase to address:**
Database migration phase. Connection configuration must account for serverless behavior from day one.

---

### Pitfall 7: Existing 188 Tests All Assume No Auth and SQLite

**What goes wrong:**
All 188 existing tests use SQLite in-memory databases with no authentication context. When auth middleware is added, every endpoint returns 401 Unauthorized in tests. When PostgreSQL-specific features are used (JSONB, connection pooling), tests that pass on SQLite fail on PostgreSQL.

**Why it happens:**
Tests were written for a single-user, no-auth, SQLite world. The migration touches every layer of the application.

**How to avoid:**
1. Create a test fixture that provides an authenticated user context (mock the OAuth dependency).
2. Keep using SQLite for unit tests (speed) but add a separate integration test suite for PostgreSQL-specific behavior.
3. Add the auth dependency as an overridable FastAPI dependency, so tests can inject a fake user.
4. Migrate tests incrementally: first make them work with the new auth layer (mock user), then verify data isolation.

**Warning signs:**
All 188 tests fail after adding auth middleware. Test suite becomes unmaintainable because every test needs auth boilerplate.

**Phase to address:**
Auth phase (test infrastructure). A `conftest.py` fixture for authenticated requests must be created BEFORE adding auth middleware to routes.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Keep SQLite for dev, PostgreSQL for prod only | Faster local dev, no local PG needed | Dialect differences cause bugs that only appear in prod | Acceptable if integration tests run against PostgreSQL in CI |
| Store user session in server memory (no Redis) | Zero infra, simple setup | Sessions lost on Render redeploy; cannot scale horizontally | Acceptable for free tier with single dyno |
| Global SerpAPI key shared by all users | No per-user API key management | One user's heavy usage affects everyone; no accountability | Acceptable for MVP with quota cap; must add usage tracking |
| Skip Alembic migrations, use `create_all()` | Faster initial setup | Cannot evolve schema without dropping tables; data loss | Never in production with real user data |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Google OAuth + FastAPI | Using `request.session` without adding `SessionMiddleware` to the app | Add `SessionMiddleware` with a secret key before registering OAuth routes |
| Google OAuth redirect URI | Using `http://localhost:8000/callback` in production | Configure separate OAuth credentials for dev (localhost) and prod (render domain); use HTTPS in prod |
| Neon.tech connection | Using the direct connection string in application code | Use the pooled connection string (`-pooler` suffix in hostname) for application connections; direct string only for migrations |
| Neon.tech + PgBouncer | Using prepared statements through PgBouncer in transaction mode | Set `statement_cache_size=0` in engine connect_args or use `NullPool` to avoid `InvalidCachedStatementError` |
| Render + Neon.tech | Hardcoding DATABASE_URL in code or render.yaml | Use Render environment variables; Neon connection string contains password that must not be in git |
| SerpAPI in scheduler | Polling synchronously blocks the scheduler thread | Use async or run polling in a thread pool; APScheduler's default thread pool is fine but add timeouts |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| N+1 queries loading route groups with snapshots | Dashboard loads slowly as groups accumulate | Use `joinedload()` or `selectinload()` in SQLAlchemy queries | At 50+ groups with 100+ snapshots each |
| No index on `route_groups.user_id` | Group listing slows down as users grow | Add index on `user_id` column at creation time | At 100+ users |
| Unbounded snapshot history | Database grows without limit; queries slow | Add a retention policy (delete snapshots older than 90 days) | At 10,000+ snapshots per group |
| Neon 0.5 GB storage limit on free tier | Database operations fail silently or with storage errors | Monitor storage usage; implement snapshot cleanup cron | At ~6-12 months of active usage with 10+ users |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Storing Google OAuth tokens in plain text in the database | If DB is compromised, attacker can impersonate users on Google services | Only store the user's Google ID (`sub` claim) and email, not access/refresh tokens. The app only needs identity, not API access to Google |
| Not validating `state` parameter in OAuth callback | CSRF attack can link attacker's Google account to victim's session | Use Authlib or similar library that handles state validation automatically |
| Using user email as the primary identifier | Users can change their Google email; email is not immutable | Use Google's `sub` claim (unique, immutable user ID) as the primary identifier |
| Exposing route_group IDs in URLs without ownership check | User A can access `/api/groups/5` even if group 5 belongs to User B | Every endpoint must verify `group.user_id == current_user.id` before returning data |
| Secret key for SessionMiddleware in source code | Session hijacking if repo is public (this repo IS public on GitHub) | Store secret key in environment variable, never in code |
| Gmail app password in .env committed to public repo | Anyone can send email from your account | Add `.env` to `.gitignore`; verify it is not in git history; rotate credentials if exposed |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Redirecting to login on every page load (no session persistence) | User logs in, refreshes page, has to log in again | Use HTTP-only cookies with reasonable expiration (7 days); check session before redirect |
| Landing page with no clear call-to-action | User arrives, reads about the product, but does not know how to try it | Single prominent "Entrar com Google" button above the fold |
| Showing empty dashboard to new users | New user logs in, sees empty page, does not know what to do | Show an onboarding prompt: "Crie seu primeiro grupo de rotas" with a guided example |
| Losing the user's place after OAuth redirect | User was configuring a group, clicks login, returns to homepage instead of their group | Store the intended destination in session before redirect; return to it after auth |
| No feedback when system quota is exhausted | User creates a group but it never gets polled; no explanation | Show clear status: "Seu grupo sera atualizado em X horas" or "Sistema em capacidade maxima" |

## "Looks Done But Isn't" Checklist

- [ ] **Google OAuth:** Often missing HTTPS redirect URI for production. Verify that the Google Cloud Console has the Render production URL as an authorized redirect URI, not just localhost.
- [ ] **Data isolation:** Often missing filter on dashboard aggregate queries. Verify that the "best price" and "signal count" dashboard queries filter by user_id.
- [ ] **Database migration:** Often missing data migration script for existing data. Verify that existing route_groups in the SQLite database can be exported/imported to PostgreSQL with a user_id assigned.
- [ ] **Session expiry:** Often missing session cleanup. Verify that expired sessions do not accumulate in memory/database.
- [ ] **Scheduler:** Often missing user context in background jobs. Verify that email alerts include the correct recipient (the group owner's email, not a hardcoded GMAIL_RECIPIENT).
- [ ] **Landing page:** Often missing meta tags for social sharing. Verify that `og:title`, `og:description`, and `og:image` are set.
- [ ] **Error handling:** Often missing graceful degradation when Neon is cold. Verify that the app shows a loading state, not a 500 error, during cold start.
- [ ] **Consent screen:** Often left in "Testing" mode. Verify by logging in with a Google account NOT on the test user list.

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Data leakage (missing user_id filter) | HIGH | Audit all queries, add filters, notify affected users, consider it a security incident |
| check_same_thread crash on deploy | LOW | One-line fix in database.py, redeploy |
| OAuth consent screen in testing mode | LOW | Publish to production in Google Cloud Console, add privacy policy URL |
| SerpAPI quota exhausted mid-month | MEDIUM | Reduce polling frequency immediately, implement quota tracking, consider upgrading to paid tier ($25/month) |
| All tests broken after adding auth | MEDIUM | Create auth fixture in conftest.py, systematically update test files. Expect 2-4 hours of work |
| Neon cold start failures in scheduler | LOW | Add pool_pre_ping=True, switch to pooled connection string, add retry logic |
| JSON mutation tracking bug | MEDIUM | Switch to immutable assignment pattern across all services that modify origins/destinations. Requires auditing every service file |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| check_same_thread crash | Phase 1: Database Migration | App starts successfully with PostgreSQL connection string |
| JSON column differences | Phase 1: Database Migration | Test that modifying origins/destinations persists correctly on PostgreSQL |
| Neon cold start handling | Phase 1: Database Migration | App survives a 10-second database suspension without crashing |
| PgBouncer prepared statement error | Phase 1: Database Migration | No `InvalidCachedStatementError` when using pooled connection string |
| OAuth consent screen stuck | Phase 2: Google OAuth | A Google account NOT in the test user list can log in successfully |
| Test suite breakage | Phase 2: Google OAuth | All 188 existing tests pass with auth fixtures; no test requires real Google login |
| Missing user_id isolation | Phase 3: Multi-user Isolation | Test with 2 users proves complete data isolation across all endpoints |
| Scheduler quota exhaustion | Phase 3: Multi-user Isolation | Global quota counter prevents polling when monthly limit reached |
| Security (token storage, CSRF, sub claim) | Phase 2: Google OAuth | OAuth tokens not stored; state parameter validated; sub used as user ID |
| Email alerts to wrong user | Phase 3: Multi-user Isolation | Alert email sent to group owner's email, not hardcoded recipient |

## Sources

- [FastAPI SQL Databases tutorial (check_same_thread)](https://fastapi.tiangolo.com/tutorial/sql-databases/)
- [SQLAlchemy PostgreSQL dialect docs](https://docs.sqlalchemy.org/en/21/dialects/postgresql.html)
- [SQLAlchemy check_same_thread discussion](https://github.com/sqlalchemy/sqlalchemy/discussions/8551)
- [Beware of JSON fields in SQLAlchemy](https://amercader.net/blog/beware-of-json-fields-in-sqlalchemy/)
- [Neon.tech connection pooling docs](https://neon.com/docs/connect/connection-pooling)
- [Neon.tech free plan guide](https://neon.com/blog/how-to-make-the-most-of-neons-free-plan)
- [Google OAuth consent screen setup](https://support.google.com/cloud/answer/10311615?hl=en)
- [Google unverified apps policy](https://support.google.com/cloud/answer/7454865?hl=en)
- [Authlib FastAPI OAuth client docs](https://docs.authlib.org/en/latest/client/fastapi.html)
- [SQLite to PostgreSQL migration checklist](https://www.fmularczyk.pl/posts/2023_06_sqlite_to_postgresql/)
- [Alembic batch migrations for SQLite](https://alembic.sqlalchemy.org/en/latest/batch.html)
- [WorkOS multi-tenant architecture guide](https://workos.com/blog/developers-guide-saas-multi-tenant-architecture)
- [Neon serverless pricing 2026 breakdown](https://vela.simplyblock.io/articles/neon-serverless-postgres-pricing-2026/)
- Codebase inspection: `app/database.py`, `app/models.py`, `app/config.py` (verified 2026-03-28)

---
*Pitfalls research for: Flight Monitor v2.0 multi-user migration*
*Researched: 2026-03-28*
