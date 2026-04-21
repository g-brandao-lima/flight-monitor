# Phase 32 Summary — Cache Layer Travelpayouts

**Data:** 2026-04-21
**Duracao:** ~45min
**Status:** SHIPPED (pushado pra master)

## Entregue

### Plan 01 — Foundation
- Modelo `RouteCache` com indice composto em (origin, destination, departure_date, return_date)
- Migration `g7h8i9j0k1l2_add_route_cache_table`
- `Settings.travelpayouts_token` lendo `TRAVELPAYOUTS_TOKEN` do .env

### Plan 02 — Cliente Travelpayouts
- Classe `TravelpayoutsClient` em [app/services/travelpayouts_client.py](../../../app/services/travelpayouts_client.py)
- 3 metodos: `fetch_cheap`, `fetch_calendar`, `fetch_month_matrix`
- Auth via header `X-Access-Token`
- Tratamento gracioso de erro HTTP e `success=false` (retornam [])
- **Fix da pegadinha IATA cidade:** normalizacao preserva IATA aeroporto pedido (GRU) ao inves do IATA cidade retornado (SAO)

### Plan 03 — Integracao
- [app/services/route_cache_service.py](../../../app/services/route_cache_service.py) com:
  - `get_cached_price(db, origin, dest, dep, ret, ttl_hours=6)` — retorna menor preco dentro do TTL
  - `refresh_top_routes(db, client, routes, months)` — upsert de precos via Travelpayouts
  - `TOP_BR_ROUTES`: lista canonica de 28 rotas BR (15 domesticas + 13 internacionais)
  - `_next_n_months(n)`: helper pra gerar YYYY-MM dos proximos N meses
- [app/services/flight_search.py](../../../app/services/flight_search.py) `search_flights_ex` agora consulta:
  1. `flight_cache` in-memory (30 min)
  2. `route_cache` persistente (6h, Travelpayouts)
  3. SerpAPI (fallback)
- Cache hit retorna `source="travelpayouts_cached"`, was_cache_hit=True
- [app/scheduler.py](../../../app/scheduler.py) job `travelpayouts_refresh` agendado 4x/dia (00:30, 06:30, 12:30, 18:30 UTC) — offset de 30min dos pollings SerpAPI

### Plan 04 — Admin metrics
- Modelo `CacheLookupLog` + migration `h8i9j0k1l2m3`
- `search_flights_ex` loga hit/miss apos cada retorno (best-effort, nunca bloqueia)
- [app/services/admin_stats_service.py](../../../app/services/admin_stats_service.py) novas funcoes:
  - `get_cache_hit_rate_7d(db)` — hit rate dos ultimos 7 dias
  - `get_travelpayouts_quota_info(db)` — uso mensal rastreado internamente
  - `increment_travelpayouts_usage(db)` — chamado por `refresh_top_routes` apos cada call
- Admin panel `/admin/stats` ganhou secao "Cache Travelpayouts (ultimos 7 dias)" exibindo hit rate + uso mensal

## Testes

- Antes: 304 passando
- Depois: **334 passando** (+30), 0 regressao
- Novos testes:
  - 5 RouteCache model + settings
  - 9 Travelpayouts client (happy path + pegadinha IATA + erros)
  - 9 route_cache_service (get/refresh/upsert/skip)
  - 2 integracao flight_search + route_cache
  - 5 admin metrics (CacheLookupLog, hit rate, quota)

## Arquivos

- 3 novos services: `travelpayouts_client.py`, `route_cache_service.py`
- 2 migrations: `g7h8i9j0k1l2_add_route_cache_table`, `h8i9j0k1l2m3_add_cache_lookup_log`
- 2 novos models: `RouteCache`, `CacheLookupLog`
- 5 novos arquivos de teste
- 6 arquivos modificados (config, models, scheduler, flight_search, admin stats service, admin route, admin template, test_scheduler)

## Observacoes pra producao

### Migrations aplicadas automatico
Render roda `alembic upgrade head` no buildCommand. Proximo deploy vai criar as 2 tabelas novas.

### Primeira execucao do cron
Proxima execucao real do `travelpayouts_refresh` sera no proximo slot (00:30, 06:30, 12:30 ou 18:30 UTC). Com 28 rotas × 6 meses = 168 calls por ciclo.

### Ver no admin panel
Apos o primeiro ciclo rodar em producao, acessar `/admin/stats` — secao "Cache Travelpayouts" mostrara hit rate e chamadas feitas. Nas primeiras 24h o hit rate vai estar baixo (cache ainda populando).

### Commits pushados
- `docs(32): plan Cache Layer Travelpayouts (4 plans, 10 tasks)`
- `feat(32): cache layer Travelpayouts (CACHE-03..CACHE-07)`

## Proximo

Phase 33: Public Route Index (SEO) — paginas publicas `/rotas/{ORIG}-{DEST}` servidas do `route_cache`.
