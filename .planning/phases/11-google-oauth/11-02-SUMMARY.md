---
phase: 11-google-oauth
plan: 02
subsystem: auth
tags: [oauth, google, authlib, session, middleware, starlette]

requires:
  - phase: 11-google-oauth/01
    provides: "User model, Alembic migration, auth fixtures em conftest.py"
provides:
  - "Fluxo OAuth completo: login, callback, logout via Authlib"
  - "SessionMiddleware com max_age de 1 ano (cookie httpOnly assinado)"
  - "AuthMiddleware global protegendo rotas (exceto publicas)"
  - "Flash messages de auth (login_required, login_erro, login_cancelado)"
affects: [11-google-oauth/03, 13-landing-page]

tech-stack:
  added: [authlib]
  patterns: [global-auth-middleware, signed-session-cookie, oauth-authorize-redirect]

key-files:
  created:
    - app/auth/oauth.py
    - app/auth/routes.py
    - app/auth/middleware.py
  modified:
    - main.py
    - app/routes/dashboard.py
    - tests/conftest.py
    - tests/test_auth.py

key-decisions:
  - "client fixture autenticado por padrao via session cookie assinado (itsdangerous) para nao quebrar 188 testes existentes"
  - "unauthenticated_client fixture separada para testar middleware de protecao"
  - "PUBLIC_PREFIXES inclui /api/airports/ para nao bloquear autocomplete de aeroportos"

patterns-established:
  - "Session cookie assinado via _make_session_cookie() helper no conftest.py para testes"
  - "AuthMiddleware com PUBLIC_PATHS (frozenset) e PUBLIC_PREFIXES (tuple) para rotas publicas"
  - "OAuth mock via unittest.mock.patch no authorize_access_token para testes de callback"

requirements-completed: [AUTH-01, AUTH-02, AUTH-03, AUTH-05]

duration: 3min
completed: 2026-03-28
---

# Phase 11 Plan 02: OAuth Authentication Flow Summary

**Fluxo OAuth completo via Authlib com SessionMiddleware (1 ano), AuthMiddleware global, e 10 testes cobrindo login/callback/logout/middleware**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-28T21:49:59Z
- **Completed:** 2026-03-28T21:53:30Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 7

## Accomplishments
- Fluxo OAuth funcional: /auth/login redireciona para Google, /auth/callback cria/reutiliza User e seta sessao, /auth/logout limpa sessao
- SessionMiddleware configurado com max_age de 1 ano, https_only condicional (sqlite=dev=False, postgres=prod=True), same_site=lax
- AuthMiddleware protege todas as rotas exceto / (landing), /auth/* (OAuth), /static/ (assets), /api/airports/ (autocomplete), HEAD / (UptimeRobot)
- Flash messages de auth integradas ao sistema existente (login_required, login_erro, login_cancelado)
- 198 testes passando (188 existentes + 10 novos), zero regressao

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Failing auth tests** - `d9927e9` (test)
2. **Task 1 (GREEN): OAuth routes + middlewares + implementation** - `eba49ff` (feat)

## Files Created/Modified
- `app/auth/oauth.py` - Authlib OAuth client registration para Google (OIDC auto-discovery)
- `app/auth/routes.py` - Rotas /auth/login, /auth/callback, /auth/logout
- `app/auth/middleware.py` - AuthMiddleware global com PUBLIC_PATHS e PUBLIC_PREFIXES
- `main.py` - SessionMiddleware + AuthMiddleware + auth router integration
- `app/routes/dashboard.py` - Flash messages de auth adicionadas ao FLASH_MESSAGES dict
- `tests/conftest.py` - client fixture autenticado por padrao, unauthenticated_client, _make_session_cookie helper
- `tests/test_auth.py` - 10 testes cobrindo OAuth login, callback, logout, middleware

## Decisions Made
- client fixture agora cria test_user automaticamente e injeta session cookie assinado via itsdangerous, garantindo que todos os 188 testes existentes continuem funcionando sem alteracao
- Criada fixture unauthenticated_client separada para testar comportamento do middleware (redirecionamento de nao-logados)
- PUBLIC_PREFIXES inclui /api/airports/ para nao bloquear o endpoint de busca de aeroportos usado pelo autocomplete

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None - todos os fluxos estao implementados e testados.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. Google OAuth credentials (GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, SESSION_SECRET_KEY) ja estao no config.py com defaults vazios.

## Next Phase Readiness
- Fluxo OAuth completo e funcional, pronto para Plan 03 (header UI com avatar/nome/logout)
- get_current_user dependency disponivel para injetar User em rotas que precisam dos dados do usuario

---
## Self-Check: PASSED

All files verified present. All commit hashes found in git log.

---
*Phase: 11-google-oauth*
*Completed: 2026-03-28*
