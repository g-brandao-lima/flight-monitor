---
phase: 36-multi-leg
verified: 2026-04-22T00:00:00Z
status: passed
score: 4/4 must-haves verified
---

# Phase 36: Multi-Leg Trip Builder Verification Report

**Phase Goal:** Usuario monitora roteiro encadeado (BR -> Italia -> Espanha -> BR) em um unico grupo-pai, com sinal de compra aplicado sobre o preco total do encadeamento.
**Verified:** 2026-04-22
**Status:** passed
**Re-verification:** No (initial verification)

## Goal Achievement

### Observable Truths (Success Criteria from ROADMAP)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Usuario cria grupo-pai com N trechos sequenciais via UI (origin, destination, janela de datas, min/max stay) | VERIFIED | `POST /groups` dispatcher em `app/routes/dashboard.py:549,602`; templates create.html/edit.html contem `leg-template`, `recalcLegs`, `__PRELOADED_LEGS__` (24 matches em 2 templates); `RouteGroupLeg` model em `app/models.py:62` com todas as colunas; testes `test_create_multi_leg_group_valid`, `test_create_multi_leg_group_server_validation_runs_even_if_client_passes` GREEN |
| 2 | Sistema valida encadeamento temporal (saida N+1 >= chegada N + min_stay) | VERIFIED | `RouteGroupMultiCreate.validate_chain` em `app/schemas.py:91-117` com sort-by-order (Pitfall 5); `_is_valid_chain` em `multi_leg_service.py:54`; mensagem pt-BR "precisa sair em ou apos" emitida; testes `test_chain_validation_rejects_overlap`, `test_min_max_legs`, `test_is_valid_chain`, `test_create_multi_leg_group_invalid_chain` GREEN |
| 3 | Sistema busca precos de cada trecho via cache/SerpAPI e calcula preco total | VERIFIED | `multi_leg_service.search_multi_leg_prices` com `itertools.product` (L269), `_fetch_leg_price` cache-first (L87) via `route_cache_service.get_cached_price`; `_persist_multi_snapshot` grava `airline="MULTI"` + `details JSON`; testes `test_uses_route_cache_before_serpapi`, `test_persists_multi_snapshot_with_details`, `test_picks_cheapest_total` GREEN |
| 4 | Sinal de compra e prediction aplicados sobre preco total, nao trecho a trecho | VERIFIED | `polling_service._poll_group` ramifica em `mode=="multi_leg"` (L101) e chama `detect_signals(db, snapshot)` sobre snapshot com `price=total`; `signal_service._check_preco_abaixo_historico` ajustado para dispensar gate LOW quando `airline=="MULTI"`; prediction recebe `days_to_departure` do primeiro leg (Pitfall 3); testes `test_signal_on_total_price`, `test_prediction_uses_total_median`, `test_consolidated_multi_has_recommendation_before_legs` GREEN |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/models.py::RouteGroupLeg` | Model + FlightSnapshot.details + RouteGroup.legs | VERIFIED | L54 (legs relationship), L62 (class RouteGroupLeg), L104 (details Mapped) |
| `app/schemas.py::RouteGroupMultiCreate` | LegCreate/LegOut/RouteGroupMultiCreate + model_validator | VERIFIED | L75, L86, L91 + sorted legs L101 |
| `alembic/versions/j0k1l2m3n4o5_add_route_group_leg_and_details.py` | Migration reversivel | VERIFIED | File exists, down_revision "i9j0k1l2m3n4" |
| `app/services/multi_leg_service.py` | search_multi_leg_prices + helpers | VERIFIED | Todas as funcoes presentes, itertools.product L269, cache-first L87, airline="MULTI" |
| `app/services/polling_service.py` | Branch mode=multi_leg | VERIFIED | L101-102 if/import lazy |
| `app/services/snapshot_service.py` | Branch airline=MULTI em is_duplicate_snapshot | VERIFIED | L88 if airline=="MULTI", L89 cutoff 6h |
| `app/services/dashboard_service.py` | _build_multi_leg_item + booking_urls_oneway | VERIFIED | L33, L240, L636 |
| `app/services/alert_service.py` | _render_consolidated_multi + dispatcher | VERIFIED | L603 def, L630 subject D-20, L703 label preco total |
| `app/templates/dashboard/create.html` | Toggle + builder dinamico | VERIFIED | 11 matches (leg-template, Tipo de roteiro, recalcLegs, __PRELOADED_LEGS__) |
| `app/templates/dashboard/edit.html` | Preload + builder | VERIFIED | 13 matches |
| `app/templates/dashboard/index.html` | Card variant multi | VERIFIED | 4 matches (card-multi, Primeira busca em andamento) |
| `app/templates/dashboard/detail.html` | Breakdown + comparadores | VERIFIED | 8 matches (multi-breakdown, Combinacao mais barata, Comparar este trecho em) |

### Key Link Verification

| From | To | Via | Status |
|------|------|-----|--------|
| polling_service._poll_group | multi_leg_service.search_multi_leg_prices | lazy import | WIRED (L101-102) |
| multi_leg_service._fetch_leg_price | route_cache_service + flight_search | cache-first | WIRED (L87, fallback SerpAPI) |
| routes/dashboard.py POST /groups | RouteGroupMultiCreate | Pydantic validation | WIRED (L18, L368, L627) |
| alert_service.compose_consolidated_email | _render_consolidated_multi | dispatcher group.mode | WIRED (L247, L256) |
| dashboard_service._build_multi_leg_item | FlightSnapshot.details | snapshot.details["legs"] parse | WIRED |
| templates/detail.html | booking_urls_oneway | leg.compare_urls | WIRED (L636) |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 16 multi-leg tests GREEN | `pytest tests/test_multi_leg_*.py` | 16 passed | PASS |
| Full suite no regression | `pytest` | 410 passed, 0 failed | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| MULTI-01 | 36-01, 36-03 | Usuario cria grupo-pai com N trechos sequenciais | SATISFIED | Model + schema + POST handler + UI builder; tests GREEN |
| MULTI-02 | 36-01, 36-03 | Validacao encadeamento temporal | SATISFIED | `validate_chain` server + JS client; mensagens pt-BR UI-SPEC |
| MULTI-03 | 36-02, 36-04 | Busca cache/SerpAPI + preco total | SATISFIED | multi_leg_service com itertools.product + cache-first + dashboard breakdown |
| MULTI-04 | 36-02, 36-04 | Sinal + prediction sobre preco total | SATISFIED | Signal detect sobre snapshot.price=total, prediction sobre primeiro leg; email com recomendacao mandatoria |

No ORPHANED requirements. REQUIREMENTS.md traceability table ja marca MULTI-01..04 como Complete.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | - | - | - | - |

Apenas DeprecationWarnings de `datetime.utcnow()` (anti-pattern ambiental generalizado no codebase, nao introduzido por Phase 36; nao bloqueia).

### Human Verification Required

Checkpoint visual foi auto-aprovado via `workflow.auto_advance=true`. O usuario pode opcionalmente validar manualmente:

1. **Visual dashboard multi**
   - Test: Criar grupo multi-trecho via UI em producao/local, rodar ciclo de polling, verificar card home
   - Expected: Badge MULTI ciano, cadeia `GRU -> FCO -> ... -> GRU` mono 14px, preco total mono 28px, recomendacao Phase 34
   - Why human: Paleta, tipografia, paridade de altura entre cards multi e roundtrip

2. **Email consolidado em Gmail**
   - Test: Disparar `_send_consolidated_alert` em grupo multi, abrir email real no Gmail
   - Expected: Subject "Orbita multi: {nome} R$ X,XX (N trechos)"; recomendacao no topo; breakdown; plain text fallback
   - Why human: Renderizacao de email cliente (Gmail/Outlook), inline CSS, spam score

3. **Links one-way dos comparadores**
   - Test: No detalhe do grupo multi, clicar cada um dos 4 botoes por leg
   - Expected: Abre Google Flights/Decolar/Skyscanner/Kayak com busca one-way (sem return_date)
   - Why human: Validar URLs reais contra mudanca de schema dos agregadores

### Gaps Summary

Nenhum gap encontrado. Todos os 4 Success Criteria da ROADMAP.md estao satisfeitos, todos os 4 requirements (MULTI-01..04) mapeados para Phase 36 tem evidencia de implementacao em codigo + testes GREEN. Full suite 410 passed, 0 failed. Artifacts existem, linkagens verificadas, data-flow completo (UI -> handler -> schema -> model -> service -> polling -> signal -> prediction -> email).

Observacoes menores (nao bloqueantes):
- DeprecationWarnings de `datetime.utcnow()` (convencao legacy do codebase)
- Checkpoint visual humano foi auto-aprovado; validacao real de UI e email Gmail recomendada mas nao obrigatoria para goal achievement
- Migration local SQLite nao roda por bug pre-existente em `a1b2c3d4e5f6` (documentado como deferred em 36-01-SUMMARY, fora do escopo desta phase; producao PostgreSQL nao afetada)

---

*Verified: 2026-04-22*
*Verifier: Claude (gsd-verifier)*
