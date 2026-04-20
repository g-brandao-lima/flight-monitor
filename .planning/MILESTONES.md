# Milestones

## v2.1 Clareza de Preco e Robustez (Shipped: 2026-04-20)

**Phases completed:** 11 phases (15, 15.1, 16, 17, 17.1, 19, 20, 21, 21.5, 22, 23). Phase 18 (JWT Sessions) deferida como over-engineering para 200 users em 1 worker.

**Key accomplishments:**

- Fix critico de vazamento de dados na API REST /api/v1/route-groups/ (Phase 15.1)
- Rate limiting em 6 endpoints com limites por custo (login, escrita, polling, autocomplete)
- CI pipeline GitHub Actions rodando pytest em push/PR
- passengers propagado corretamente para SerpAPI e fast-flights (antes hardcoded 1)
- Rotulo "por pessoa, ida e volta" em todos os contextos + total para multi-pax
- Coluna source em FlightSnapshot + badge visual unificado Google Flights
- Cache in-memory 30min reduzindo chamadas duplicadas a API externas
- BookingClassSnapshot e amadeus_client removidos (legacy v1.0, -400 linhas)
- Sentry integrado em producao com LGPD-aware scrubbing e user context
- Contexto historico no email "X% abaixo da media dos ultimos 90 dias"
- Script analyze_signals.py para validacao empirica de sinais
- 258 testes passando, zero regressoes

---

## v2.0 Multi-usuario (Shipped: 2026-03-30)

**Phases completed:** 5 phases, 10 plans, 20 tasks

**Key accomplishments:**

- database.py condicional por dialeto (SQLite/PostgreSQL) com Alembic baseline migration das 4 tabelas e pool_pre_ping para Neon.tech
- render.yaml com alembic upgrade head no build e DATABASE_URL como env var secreta para PostgreSQL via Neon.tech
- User model com google_id/email, Authlib instalado, Alembic migration para tabela users, e fixtures test_user/authenticated_client prontas para uso
- Fluxo OAuth completo via Authlib com SessionMiddleware (1 ano), AuthMiddleware global, e 10 testes cobrindo login/callback/logout/middleware
- Conditional header with avatar/name/logout for logged users and "Entrar com Google" for anonymous, plus render.yaml OAuth env vars with proxy trust
- user_id FK on route_groups with full query filtering, ownership checks on all routes, and 6 isolation tests
- Email alerts sent to group owner's Google email via recipient_email param, with Meus Alertas page showing per-user signal history
- Global SerpAPI usage counter with monthly reset, dashboard indicator, and polling auto-stop at 250 searches/month
- Landing page publica com hero, 3 passos "Como funciona", 3 cards diferenciais com SVG e CTA Google OAuth, rota / condicional por estado de login
- Dashboard queries dialect-agnostic (sem func.strftime) e APP_BASE_URL declarado no render.yaml para links de silenciar alerta

---
