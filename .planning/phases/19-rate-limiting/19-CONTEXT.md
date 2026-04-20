# Phase 19: Rate Limiting Completo - Context

**Gathered:** 2026-04-20
**Status:** Implemented

<domain>
Expandir rate limiting da Phase 15.1 (apenas login) para endpoints criticos. Diferenciar limites por custo de operacao: polling consome SerpAPI quota, autocomplete e barato, escrita de grupos cria dados.
</domain>

<decisions>
- key_func hibrido `get_user_or_ip`: usa user_id da sessao quando autenticado, senao IP
  - Evita que IP corporativo compartilhado afete todos os usuarios
  - Evita que usuario malicioso contorne limite trocando IP
- Constantes declarativas em app/rate_limit.py:
  - LIMIT_LOGIN = 10/minute (Phase 15.1)
  - LIMIT_READ = 60/minute
  - LIMIT_WRITE = 20/minute
  - LIMIT_POLLING = 5/minute (protege quota SerpAPI)
  - LIMIT_AUTOCOMPLETE = 30/minute
- Endpoints protegidos:
  - POST /groups/create, POST /groups/{id}/edit, POST /groups/{id}/toggle, POST /groups/{id}/delete (WRITE)
  - GET /api/airports/search (AUTOCOMPLETE)
  - POST /polling/manual (POLLING)
- GET de leitura (dashboard, detail) sem limite no momento: caching local do browser + middleware auth ja filtram
</decisions>

<code_context>
### Arquivos alterados
- app/rate_limit.py: get_user_or_ip, constantes LIMIT_*
- app/routes/dashboard.py: decorators em 5 endpoints
- tests/test_auth_rate_limit.py: +2 testes (autocomplete, polling)
</code_context>

<specifics>
- Para escalar apos 200 users, avaliar migrar storage de slowapi para Redis (hoje e in-memory e reseta em cada deploy).
</specifics>

<deferred>
- Redis como backend: quando 1 worker virar 2+ (apos 500 users ou multi-container)
- X-Forwarded-For trust config: hoje get_remote_address default funciona no Render (proxy unico). Revisitar se mudar de provider.
</deferred>
