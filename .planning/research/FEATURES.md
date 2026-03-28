# Feature Research

**Domain:** Multi-user flight price monitoring SaaS (v2.0 upgrade from single-user tool)
**Researched:** 2026-03-28
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist when they see a login page and multi-user app. Missing these = product feels broken or insecure.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Google OAuth login (one-click) | Users see "Login com Google" and expect a single click to enter. No password forms, no email confirmation flows. | MEDIUM | Requires Google Cloud Console project, OAuth consent screen, Authlib integration with FastAPI. Callback URL must match Render domain exactly. |
| Session persistence across tabs | After login, opening a new tab should not require re-authentication. | LOW | Server-side session via signed cookie (itsdangerous) or JWT in httpOnly cookie. Jinja2 templates already render server-side, so cookie-based session is the natural fit. |
| Logout button visible on every page | Users need a clear way to sign out. | LOW | Clear session cookie + redirect to landing page. |
| User avatar and name in header | After OAuth, users expect to see their Google profile photo and name. | LOW | Google userinfo endpoint returns name, email, picture. Store on first login. Display in base.html header. |
| Complete data isolation between users | User A must never see User B's route groups, snapshots, or signals. No data leaks. | MEDIUM | Every query must filter by user_id. This is the single most critical multi-tenant requirement. Foreign key on route_groups.user_id cascades to all child tables. |
| Landing page before login | Visitors who arrive at the URL without being logged in must see a public page explaining what the product does, not a blank dashboard or login redirect. | MEDIUM | Separate route (/) for landing page vs. authenticated dashboard (/dashboard). Current index.html becomes the authenticated view. |
| Mobile-responsive landing page | 83% of landing page visits are mobile. A non-responsive page causes immediate bounce. | LOW | Already using Jinja2 + CSS. Landing page needs viewport meta, flexbox/grid layout, and touch-friendly CTA. |
| HTTPS everywhere | OAuth requires HTTPS callback. Render provides this by default on *.onrender.com domains. | LOW | Already handled by Render. No extra work needed. |
| Error handling on auth failure | If Google OAuth fails (user denies consent, token expired, network error), show a clear error message, not a 500 page. | LOW | Catch exceptions in OAuth callback, redirect to landing with flash message. |
| PostgreSQL data persistence | Data must survive Render deploys. Current SQLite is ephemeral on Render (file system resets on each deploy). | HIGH | Full database migration: schema + existing data. Neon.tech free tier provides 0.5 GB storage, connection pooling. Alembic for schema management going forward. |

### Differentiators (Competitive Advantage)

Features that set Flight Monitor apart from Google Flights, Hopper, Skyscanner, and Kayak. These align with the core value proposition of booking class intelligence.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Landing page with "Por que somos diferentes" section | Google Flights/Skyscanner show price history. Flight Monitor shows *why* prices will change (booking class velocity). No competitor explains this to consumers. A clear "what we do that they don't" section converts visitors who already use other tools. | LOW | Static content. Hero + 3 comparison points + CTA button. No dynamic data needed. |
| Shared SerpAPI budget indicator | Multiple users share the 250 searches/month free tier. Showing "X buscas restantes este mes" in the dashboard builds trust and prevents surprise quota exhaustion. | LOW | Global counter in database. Display in dashboard header. |
| Pre-filled demo group on first login | New users who sign up and see an empty dashboard don't understand the value. Creating one example route group (ex: GRU-LIS next month) with a few sample snapshots gives immediate context. | MEDIUM | Seed data on first user creation. Must not count against the user's 10-group limit until they explicitly keep it. |
| "Meus alertas" history page | Google Flights sends email alerts but provides no history. Showing all past signals with timestamps and prices gives users a sense of ongoing value, even when no new signals fire. | LOW | Already have DetectedSignal table. Just need a new Jinja2 template filtered by user_id. |
| Per-user email configuration | Users set their own email for alerts instead of relying on a single admin Gmail. Google OAuth already provides their email. | LOW | Store user email from OAuth profile. Use it as recipient in alert_service. Sender remains the app's Gmail SMTP. |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Email/password registration | "Some users don't have Google" | Adds password hashing, reset flow, email verification, security liability. PROJECT.md explicitly excludes this. Google accounts are universal in the target audience (Brazilian travelers). | Keep Google OAuth only. Revisit only if actual user feedback demands it. |
| Social sharing of deals | "Let users share cheap flights on Twitter/WhatsApp" | Exposes internal signal data publicly. Competitors could scrape. Sharing alerts from a niche tool feels spammy. | Users can manually share. No built-in social features. |
| Real-time price updates (WebSocket) | "Show live prices" | SerpAPI has 250 calls/month. Real-time is impossible at this budget. WebSocket adds complexity to the Jinja2 SSR architecture. Polling runs every 24h. | Show "ultima coleta: X horas atras" timestamp. Honest about update frequency. |
| Admin panel for user management | "Need to manage users" | Premature. At the current scale (early multi-user), an admin panel is YAGNI. If a user needs removal, a direct SQL DELETE suffices. | Direct database access for admin operations until user count justifies a panel (50+ users). |
| Multiple alert channels (Telegram, WhatsApp, push) | "Email is not enough" | PROJECT.md explicitly excludes Telegram (user silences it). WhatsApp Business API costs money. Push notifications require a service worker and PWA setup. | Gmail only. The user has already validated this works for their use case. |
| Collaborative route groups (shared between users) | "Let friends track the same route" | Breaks data isolation model. Complicates permission logic. SerpAPI quota is shared anyway, so group deduplication would be needed. | Each user creates their own groups. Same route monitored twice costs 2x SerpAPI calls, acceptable at current scale. |
| Automatic price comparison across date ranges | "Show me the cheapest day to fly in a 3-month window" | This is what Google Flights Explore already does well. Duplicating this feature is both technically expensive (many API calls) and strategically wrong (compete on signal intelligence, not search breadth). | Keep the existing model: user defines date range, system finds cheapest combinations within it. |
| Free tier usage limiting per user | "Limit heavy users from consuming all SerpAPI quota" | Over-engineering for a tool with likely 5-10 users initially. Per-user quota tracking, rate limiting, and enforcement add significant complexity. | Global quota display (differentiator above). If a single user dominates, handle it manually. Build per-user limits only when user count exceeds 20. |

## Feature Dependencies

```
[PostgreSQL Migration]
    └──requires──> [Alembic Setup]
    └──enables──> [User Table with foreign keys]

[Google OAuth Login]
    └──requires──> [User Table in PostgreSQL]
    └──requires──> [Google Cloud Console OAuth credentials]
    └──enables──> [Session Management]

[Data Isolation (user_id on route_groups)]
    └──requires──> [User Table]
    └──requires──> [Google OAuth Login (to know who the user is)]
    └──enables──> [Per-user Dashboard]

[Landing Page]
    └──independent (no backend dependencies)
    └──enhances──> [Google OAuth Login (provides CTA to login)]

[Per-user Email Alerts]
    └──requires──> [User Table (email from Google profile)]
    └──requires──> [Data Isolation (know whose groups to alert)]

[Demo Group Seeding]
    └──requires──> [Data Isolation]
    └──requires──> [Google OAuth Login (triggered on first login)]
```

### Dependency Notes

- **PostgreSQL Migration must come first:** All subsequent features (User table, data isolation, OAuth) depend on PostgreSQL being operational. Cannot add a users table to ephemeral SQLite on Render.
- **Google OAuth requires User table:** The OAuth callback needs somewhere to store/lookup user records. User table must exist in PostgreSQL before OAuth can work.
- **Data isolation requires both User table and OAuth:** Without knowing who the current user is (OAuth) and having a user_id column (User table), isolation is impossible.
- **Landing page is independent:** Can be built in parallel with backend work. No database or auth dependencies. Pure Jinja2 template + static CSS.
- **Per-user email alerts require the full chain:** User table (for email) + data isolation (for filtering groups by user) + existing alert_service (for sending).

## MVP Definition

### Launch With (v2.0)

Minimum viable multi-user release. What's needed before other people can use the app.

- [ ] PostgreSQL on Neon.tech replacing SQLite, with Alembic migrations
- [ ] User model (id, google_id, email, name, picture, created_at)
- [ ] Google OAuth login via Authlib (consent screen, callback, session cookie)
- [ ] user_id foreign key on route_groups with cascading isolation
- [ ] All existing queries filtered by current user's ID
- [ ] Landing page with hero, value proposition, and "Entrar com Google" CTA
- [ ] Logout endpoint clearing session
- [ ] User avatar/name in dashboard header
- [ ] Per-user email alerts (recipient = user's Google email)
- [ ] Error page for auth failures

### Add After Validation (v2.1)

Features to add once multi-user is working and 3+ users have tried the app.

- [ ] "Meus alertas" history page (signal log per user)
- [ ] Shared SerpAPI budget indicator in dashboard
- [ ] Demo group seeding on first login
- [ ] "Como funciona" section on landing page with visual explanation
- [ ] User settings page (toggle alerts on/off, change alert email)

### Future Consideration (v3+)

Features to defer until product-market fit is established and user count justifies the effort.

- [ ] Per-user SerpAPI quota limits (when user count > 20)
- [ ] Admin panel for user management (when user count > 50)
- [ ] Additional OAuth providers (Apple, GitHub) if user feedback demands
- [ ] PWA with push notifications
- [ ] Amadeus API integration for booking class intelligence (the original v1 vision, currently paused in favor of SerpAPI)

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| PostgreSQL migration + Alembic | HIGH | HIGH | P1 |
| User model + Google OAuth | HIGH | MEDIUM | P1 |
| Data isolation (user_id filtering) | HIGH | MEDIUM | P1 |
| Landing page (hero + CTA) | HIGH | LOW | P1 |
| Session management (cookie-based) | HIGH | LOW | P1 |
| User avatar/name in header | MEDIUM | LOW | P1 |
| Logout endpoint | HIGH | LOW | P1 |
| Per-user email alerts | MEDIUM | LOW | P1 |
| Auth error handling | MEDIUM | LOW | P1 |
| Signal history page | MEDIUM | LOW | P2 |
| SerpAPI budget indicator | LOW | LOW | P2 |
| Demo group seeding | MEDIUM | MEDIUM | P2 |
| User settings page | LOW | MEDIUM | P3 |
| Per-user quota limits | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for v2.0 launch (multi-user would be broken without it)
- P2: Should have, add in v2.1 when core is stable
- P3: Nice to have, future consideration

## Competitor Feature Analysis

| Feature | Google Flights | Hopper | Skyscanner | Flight Monitor (our approach) |
|---------|---------------|--------|------------|-------------------------------|
| Price alerts | Email when price drops | Push notification with buy/wait prediction | Email/push alerts | Email with signal context (not just "price dropped" but *why*) |
| Price history | "Prices are currently low/high" label | Predictive graph (95% accuracy claim) | Basic price chart | Chart.js history + signal overlay showing booking class events |
| Login required | Google account (implicit) | App account (email/social) | Email/Google/Facebook/Apple | Google OAuth only (simplicity) |
| Data isolation | Per-Google-account | Per-app-account | Per-account | Per-Google-account via user_id FK |
| Landing/onboarding | None (integrated into Google search) | App store listing + in-app tutorial | Homepage with search bar | Dedicated landing page explaining booking class intelligence value |
| Multi-route tracking | Implicit via search history | Explicit "watched trips" | "Price alerts" list | Explicit Route Groups with CRUD |
| Mobile experience | Responsive web + Android app | Mobile-first app | Responsive web + apps | Responsive web only (no native app) |
| Free tier limits | Unlimited | Unlimited (monetizes via booking) | Unlimited | 250 SerpAPI searches/month shared across all users |

### Key Competitive Insight

The landing page is the single most important conversion feature for v2.0. Google Flights, Hopper, and Skyscanner are all immediate-search tools: you type a route and get results. Flight Monitor is a *monitoring* tool: you set up a route and wait for signals. This difference in mental model must be communicated clearly on the landing page. The hero section should answer: "O que acontece depois que eu configuro uma rota?" with a visual showing the alert flow.

## Existing v1 Features (already built, context for v2.0 planning)

These features are already implemented and working. v2.0 must not break them, only add user isolation on top.

| Feature | Status | v2.0 Impact |
|---------|--------|-------------|
| Route Groups CRUD with IATA validation | Working | Add user_id FK, filter all queries |
| SerpAPI polling with price snapshots | Working | Polling loop must iterate all users' active groups |
| Signal detection (PRECO_ABAIXO_HISTORICO, JANELA_OTIMA) | Working | Signal detection logic unchanged, just scoped per user |
| Consolidated Gmail alerts with silence link | Working | Recipient changes from hardcoded email to user's email |
| Dark mode dashboard with cards, Chart.js, summary bar | Working | Add user avatar/name to header, protect routes with auth middleware |
| Visual polish (paleta profissional, tipografia) | Working | Landing page should match existing dark mode aesthetic |

## Sources

- [FastAPI OAuth2 scopes documentation](https://fastapi.tiangolo.com/advanced/security/oauth2-scopes/)
- [Authlib FastAPI OAuth Client documentation](https://docs.authlib.org/en/latest/client/fastapi.html)
- [AWS: Multi-tenant data isolation with PostgreSQL RLS](https://aws.amazon.com/blogs/database/multi-tenant-data-isolation-with-postgresql-row-level-security/)
- [Nile.dev: Shipping multi-tenant SaaS using Postgres RLS](https://www.thenile.dev/blog/multi-tenant-rls)
- [Unbounce: 26 SaaS landing pages examples and best practices](https://unbounce.com/conversion-rate-optimization/the-state-of-saas-landing-pages/)
- [SaaS Hero: High-Converting SaaS Landing Pages 2026](https://www.saashero.net/design/enterprise-landing-page-design-2026/)
- [Upgraded Points: Flight Search, Comparison and Monitoring Apps](https://upgradedpoints.com/travel/travel-resources-flight-search-comparison-monitoring/)
- [Alembic: Batch Migrations for SQLite](https://alembic.sqlalchemy.org/en/latest/batch.html)
- [Hanchon: Google Login with FastAPI and JWT](https://blog.hanchon.live/guides/google-login-with-fastapi-and-jwt/)
- [Amadeus availabilityClasses description](https://developers.amadeus.com/self-service/apis-docs/guides/developer-guides/resources/flights/)
- [SerpAPI price_history field](https://serpapi.com/google-flights-price-insights)

---
*Feature research for: Flight Monitor v2.0 Multi-user*
*Researched: 2026-03-28*
