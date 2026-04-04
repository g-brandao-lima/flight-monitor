# Architecture: v2.1 Integration Map

**Domain:** Flight price monitoring, existing multi-user FastAPI app
**Researched:** 2026-04-03
**Confidence:** HIGH (based on full codebase inspection + verified library docs)

## Current Architecture Snapshot

```
main.py (app, middlewares, exception handlers)
  +-- SessionMiddleware (Starlette, cookie-based, itsdangerous)
  +-- AuthMiddleware (checks session["user_id"])
  |
  +-- app/auth/
  |     routes.py      (login/callback/logout via Authlib)
  |     middleware.py   (AuthMiddleware: PUBLIC_PATHS/PREFIXES check)
  |     dependencies.py (get_current_user: session -> DB lookup)
  |     oauth.py        (Authlib OAuth config)
  |
  +-- app/routes/
  |     dashboard.py    (HTML: index, detail, create, edit, alerts, polling)
  |     route_groups.py (REST API: CRUD route groups)
  |     alerts.py       (REST API: silence alerts)
  |
  +-- app/services/
  |     flight_search.py    (fast-flights primary, SerpAPI fallback)
  |     serpapi_client.py   (SerpApiClient wrapper)
  |     polling_service.py  (run_polling_cycle, _poll_group)
  |     snapshot_service.py (save/dedup snapshots)
  |     signal_service.py   (detect_signals)
  |     alert_service.py    (email compose/send, silence tokens)
  |     dashboard_service.py(summary, history, formatting)
  |     quota_service.py    (SerpAPI usage tracking)
  |
  +-- app/models.py (User, RouteGroup, FlightSnapshot, BookingClassSnapshot, DetectedSignal, ApiUsage)
  +-- app/database.py (engine, SessionLocal, Base)
  +-- app/config.py (Settings via pydantic-settings)
  +-- app/scheduler.py (APScheduler: 2 cron jobs)
  +-- tests/ (221 testes, conftest.py com SQLite in-memory)
```

## Feature Integration Map (7 features)

---

### 1. CI Pipeline (GitHub Actions)

**Tipo:** Infraestrutura nova, zero impacto no codigo existente.

**Arquivos novos:**

| Arquivo | Proposito |
|---------|-----------|
| `.github/workflows/ci.yml` | Workflow pytest on push/PR to main |

**Arquivos modificados:** Nenhum.

**Integracao:** Completamente desacoplado. Roda `pip install -r requirements.txt` + `pytest` em Python 3.12. Nao precisa de banco externo (testes usam SQLite in-memory via conftest.py). Nao precisa de secrets do GitHub.

**Workflow minimo:**
```yaml
name: CI
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt
      - run: pytest --tb=short -q
```

**Dependencias de outras features:** Nenhuma. Primeira a implementar.

---

### 2. JWT Stateless Sessions

**Tipo:** Refatoracao da camada de autenticacao. Escopo contido mas toca muitos arquivos.

**Arquivos novos:**

| Arquivo | Proposito |
|---------|-----------|
| `app/auth/jwt_service.py` | `create_token(user_id) -> str`, `decode_token(token) -> dict | None` |

**Arquivos modificados:**

| Arquivo | O que muda |
|---------|-----------|
| `app/config.py` | Adicionar `jwt_secret_key: str`, `jwt_expiry_hours: int = 168` (7 dias) |
| `app/auth/middleware.py` | Extrair JWT do cookie `access_token` em vez de `request.session["user_id"]`. Decodificar com jwt_service. Setar `request.state.user_id` |
| `app/auth/dependencies.py` | `get_current_user`: ler `request.state.user_id` em vez de `request.session.get("user_id")` |
| `app/auth/routes.py` | `/callback`: gerar JWT via jwt_service, setar cookie `access_token` (httponly, secure, samesite=lax, max_age=7d). `/logout`: deletar cookie (set max_age=0) |
| `main.py` | Remover `SessionMiddleware` e import de `SessionMiddleware`. Manter `AuthMiddleware` |
| `requirements.txt` | Adicionar `PyJWT>=2.8`. Remover `itsdangerous` (era dependencia do SessionMiddleware para signing) |
| `tests/conftest.py` | `_make_session_cookie` -> `_make_jwt_token` usando PyJWT. client_fixture seta cookie `access_token` |
| `tests/test_auth.py` | Adaptar assercoes: verificar cookie JWT em vez de sessao |

**Fluxo de dados ANTES:**
```
Browser -> Cookie "session" (itsdangerous signed dict {user_id: N})
  -> SessionMiddleware (decodifica, popula request.session)
  -> AuthMiddleware (le request.session["user_id"])
  -> get_current_user (le request.session["user_id"], query User)
```

**Fluxo de dados DEPOIS:**
```
Browser -> Cookie "access_token" (JWT com {sub: user_id, exp: timestamp})
  -> AuthMiddleware (decodifica JWT, seta request.state.user_id)
  -> get_current_user (le request.state.user_id, query User)
```

**Decisao:** JWT em cookie httponly, NAO em header Authorization. Razao: frontend e Jinja2 server-rendered, nao SPA. Cookies httponly sao enviados automaticamente pelo browser. Header Authorization exigiria JavaScript em cada pagina.

**Simplificacao:** Remove SessionMiddleware inteira (1 camada a menos no stack de middlewares).

---

### 3. Rate Limiting (slowapi)

**Tipo:** Middleware/decorator sobre endpoints existentes.

**Arquivos novos:**

| Arquivo | Proposito |
|---------|-----------|
| `app/rate_limit.py` | Instancia `Limiter` com key function customizada |

**Arquivos modificados:**

| Arquivo | O que muda |
|---------|-----------|
| `requirements.txt` | Adicionar `slowapi>=0.1.9` |
| `main.py` | `app.state.limiter = limiter`, registrar handler `RateLimitExceeded` (retorna 429 com template amigavel) |
| `app/routes/dashboard.py` | Decorators `@limiter.limit` por endpoint |
| `app/routes/route_groups.py` | Idem |
| `app/routes/alerts.py` | Idem |

**Limites sugeridos por endpoint:**

| Endpoint | Limite | Razao |
|----------|--------|-------|
| `POST /polling/manual` | 5/min | Dispara busca real, consome cota SerpAPI |
| `POST /groups/create` | 10/min | Escrita no banco |
| `POST /groups/{id}/edit` | 10/min | Escrita no banco |
| `POST /groups/{id}/delete` | 10/min | Escrita no banco |
| `GET /` (dashboard) | 30/min | Leitura, queries complexas |
| `GET /groups/{id}` | 30/min | Leitura |
| `GET /alerts` | 30/min | Leitura |
| `GET /api/airports/search` | 60/min | Autocomplete, sem DB |
| `PUT/DELETE /api/v1/*` | 20/min | REST API |

**Key function:**
```python
def _key_func(request):
    user_id = getattr(request.state, "user_id", None)
    return f"user:{user_id}" if user_id else get_remote_address(request)
```

**Dependencias:** Funciona com sessao ou JWT. Key function fica mais limpa apos JWT (request.state.user_id ja disponivel), mas nao bloqueia.

---

### 4. Rotulo de Preco ("por pessoa, ida e volta") + Total Multiplos Passageiros

**Tipo:** Mudanca de apresentacao. Zero mudanca no backend/modelos/banco.

**Arquivos novos:** Nenhum.

**Arquivos modificados:**

| Arquivo | O que muda |
|---------|-----------|
| `app/templates/dashboard/index.html` | Subtexto "por pessoa, ida e volta" abaixo de cada preco. Bloco "Total para N passageiros: R$ X" quando passengers > 1 |
| `app/templates/dashboard/detail.html` | Idem no header e no eixo Y do grafico |
| `app/templates/dashboard/alerts.html` | Idem na lista de sinais |
| `app/services/alert_service.py` | Em `_render_html`, `_render_plain`, `_render_consolidated_html`, `_render_consolidated_plain`: adicionar rotulo. Acesso a `group.passengers` ja disponivel nos parametros |
| `app/services/dashboard_service.py` | Novo helper: `format_price_with_label(price, passengers)` retornando dict com `unit_label`, `total_label` |

**Logica de calculo:**
```python
def format_price_with_label(price: float, passengers: int = 1) -> dict:
    unit = format_price_brl(price)
    result = {"unit": unit, "label": "por pessoa, ida e volta"}
    if passengers > 1:
        total = format_price_brl(price * passengers)
        result["total"] = f"Total {passengers} passageiros: {total}"
    return result
```

**Pontos de exibicao de preco (lista exaustiva):**
1. Dashboard index: card de cada grupo (cheapest_snapshot.price)
2. Dashboard index: summary bar (cheapest_price)
3. Dashboard detail: header do grupo
4. Dashboard detail: grafico de historico (eixo Y e tooltips)
5. Dashboard alerts: preco na lista de sinais
6. Email HTML: header "Melhor preco", tabela top 3, outras rotas
7. Email plain: todas as linhas de preco

**Dependencias:** Nenhuma. Feature mais isolada do milestone.

---

### 5. Fix passengers hardcoded no fast-flights

**Tipo:** Bug fix pontual na camada de servico.

**Arquivos modificados:**

| Arquivo | O que muda |
|---------|-----------|
| `app/services/flight_search.py` | `search_flights()` recebe `passengers: int = 1`, repassa para `_search_fast_flights`. Linha 68: `Passengers(adults=passengers)` em vez de `Passengers(adults=1)` |
| `app/services/polling_service.py` | Linha 113: `search_flights(... passengers=group.passengers)` |
| `tests/test_flight_search.py` | Novo teste: busca com passengers=2, verificar que Passengers(adults=2) e passado |
| `tests/test_polling_service.py` | Verificar que group.passengers e propagado para search_flights |

**Linha exata do bug (flight_search.py:68):**
```python
# ANTES
passengers=Passengers(adults=1),
# DEPOIS
passengers=Passengers(adults=passengers),
```

**Tambem precisa propagar na assinatura:**
```python
# flight_search.py:17 search_flights
def search_flights(..., passengers: int = 1) -> ...:

# flight_search.py:50 _search_fast_flights
def _search_fast_flights(..., passengers: int = 1) -> ...:
```

**Dependencias:** Nenhuma. Bug fix isolado.

---

### 6. Otimizacao SerpAPI (cache de resultados)

**Tipo:** Nova camada entre flight_search e serpapi_client.

**Arquivos novos:**

| Arquivo | Proposito |
|---------|-----------|
| `app/services/flight_cache.py` | Cache in-memory com TTL de 6h |

**Arquivos modificados:**

| Arquivo | O que muda |
|---------|-----------|
| `app/services/flight_search.py` | Apos falha do fast-flights, verificar cache antes de chamar SerpAPI. Apos SerpAPI retornar, salvar no cache |

**Estrategia:** Cache in-memory (dict Python com timestamp). Razao: app roda em instancia unica no Render, sem necessidade de Redis. TTL de 6 horas alinhado com ciclo de polling.

**Chave de cache:** `{origin}:{destination}:{departure}:{return}:{max_stops}:{passengers}`

**Fluxo:**
```
search_flights():
  1. Tenta fast-flights (sem custo API) -> sucesso? return
  2. Gera chave de cache
  3. Verifica cache -> hit? return cached (nao incrementa quota)
  4. Chama SerpAPI -> incrementa quota, salva no cache, return
```

**Economia estimada:** Pollings consecutivos para o mesmo grupo com mesmas rotas: ~50% reducao de chamadas SerpAPI (quando fast-flights falha).

**Dependencias:** Implementar apos fix de passengers para que a chave de cache inclua passengers correto.

---

### 7. Remocao do BookingClassSnapshot (legado Amadeus)

**Tipo:** Limpeza de codigo + migration Alembic.

**Arquivos novos:**

| Arquivo | Proposito |
|---------|-----------|
| `alembic/versions/xxx_drop_booking_class_snapshots.py` | Migration: DROP TABLE booking_class_snapshots |

**Arquivos modificados:**

| Arquivo | O que muda |
|---------|-----------|
| `app/models.py` | Remover classe `BookingClassSnapshot` (linhas 83-90). Remover `booking_classes` relationship de `FlightSnapshot` (linhas 78-80) |
| `app/services/polling_service.py` | Remover `"booking_classes": []` de snapshot_data (linha 222) |
| `app/routes/dashboard.py` | Remover import e query de `BookingClassSnapshot` na cascata de `delete_group` (linhas 413-416) |
| `app/services/snapshot_service.py` | Verificar se referencia booking_classes na logica de save |
| Testes que referenciam BookingClassSnapshot | Atualizar/remover |

**Risco:** BAIXO. A tabela existe mas nunca foi populada apos migracao de Amadeus para SerpAPI. Nenhum dado sera perdido.

**Cuidado:** Gerar migration com `alembic revision --autogenerate` e revisar o SQL. Deve conter apenas `DROP TABLE booking_class_snapshots` e `DROP INDEX` se houver.

---

## Suggested Build Order

```
Phase 1: CI Pipeline                       [0 deps, rede de seguranca]
Phase 2: Fix passengers hardcoded          [0 deps, bug fix simples]
Phase 3: Rotulo de preco + total pax       [0 deps, valor UX imediato]
Phase 4: JWT Stateless Sessions            [CI como rede, refatoracao ampla]
Phase 5: Rate Limiting                     [melhor apos JWT, request.state.user_id]
Phase 6: Cache SerpAPI                     [apos passengers fix, chave correta]
Phase 7: Remocao BookingClassSnapshot      [CI como rede, limpeza final]
```

**Rationale:**
- CI primeiro: qualquer regressao nas 6 features seguintes e detectada imediatamente.
- Bug fix cedo: corrige comportamento errado antes de construir cache sobre ele.
- Labels cedo: entrega valor visivel ao usuario com risco zero.
- JWT e o item mais complexo mas bem contido; CI protege.
- Rate limiting se beneficia de request.state.user_id (JWT), mas nao bloqueia se feito antes.
- Cache apos passengers fix: evita invalidar cache por mudanca de chave.
- Limpeza por ultimo: nao bloqueia nenhuma outra feature.

---

## New vs Modified Files Summary

| Feature | Novos | Modificados | Testes Impactados |
|---------|-------|-------------|-------------------|
| CI | 1 | 0 | 0 |
| Passengers Fix | 0 | 2 | 2 |
| Price Labels | 0 | 5 | 0 (novos) |
| JWT | 1 | 7 | 2 (conftest, test_auth) |
| Rate Limiting | 1 | 4 | 0 (novos) |
| SerpAPI Cache | 1 | 1 | 0 (novos) |
| Legacy Removal | 1 (migration) | 4 | 2-3 |
| **Total** | **5 novos** | **~16 mods** | **~6 existentes** |

---

## Anti-Patterns to Avoid

### JWT em header Authorization com frontend Jinja2
**Problema:** Templates server-rendered nao enviam headers customizados. Todas as paginas quebram.
**Solucao:** JWT em cookie httponly. Browser envia automaticamente.

### Cache no banco de dados (PostgreSQL)
**Problema:** Overhead de I/O, migration, limpeza periodica. Complexidade desnecessaria.
**Solucao:** Dict in-memory com TTL. Instancia unica no Render, estado compartilhado desnecessario.

### Rate limiting global uniforme
**Problema:** Polling manual (caro, consome cota) e autocomplete de aeroporto (barato) com mesmo limite.
**Solucao:** Limites por endpoint segundo custo real da operacao.

### Remover BookingClassSnapshot sem migration Alembic
**Problema:** Alembic perde sincronia. Tabela orfã no PostgreSQL de producao.
**Solucao:** `alembic revision --autogenerate` + revisar SQL + testar up/down.

### Mudar SessionMiddleware e conftest.py simultaneamente sem CI
**Problema:** 221 testes podem quebrar silenciosamente.
**Solucao:** CI ativo antes. Mudar middleware, rodar testes, ajustar conftest, rodar testes novamente.

---

## Data Flow Changes

### Auth (antes vs depois do JWT)

**Antes:**
```
Request -> SessionMiddleware (itsdangerous decode -> request.session)
        -> AuthMiddleware (request.session["user_id"])
        -> Route (get_current_user via request.session)
```

**Depois:**
```
Request -> AuthMiddleware (PyJWT decode cookie -> request.state.user_id)
        -> Route (get_current_user via request.state)
```

### Flight Search (antes vs depois do cache)

**Antes:**
```
fast-flights falha -> SerpAPI (1 credito) -> snapshot
```

**Depois:**
```
fast-flights falha -> cache hit? return (0 creditos)
                   -> cache miss? SerpAPI (1 credito) -> cache set -> snapshot
```

## Sources

- [SlowAPI GitHub](https://github.com/laurentS/slowapi) - Confirmacao de API, storage backends
- [FastAPI JWT Official](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/) - Padrao recomendado
- [Neon FastAPI JWT Guide](https://neon.com/guides/fastapi-jwt) - Integracao com PostgreSQL/Neon
- [GitHub Actions CI for FastAPI](https://retz.dev/blog/continuous-integration-github-fastapi-and-pytest/) - Workflow de referencia
- [SlowAPI Docs](https://slowapi.readthedocs.io/) - Configuracao de limiter e key functions
