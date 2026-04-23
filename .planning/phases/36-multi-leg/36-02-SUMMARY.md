---
phase: 36-multi-leg
plan: 02
subsystem: multi-leg-search
tags: [service, polling, signal, tdd, wave-2]
dependency_graph:
  requires: [36-01, RouteGroupLeg, FlightSnapshot.details]
  provides:
    - multi_leg_service.search_multi_leg_prices
    - multi_leg_service._is_valid_chain
    - multi_leg_service._candidate_dates
    - multi_leg_service._fetch_leg_price
    - multi_leg_service._persist_multi_snapshot
    - polling_service._poll_group branch mode=multi_leg
    - snapshot_service.is_duplicate_snapshot branch airline=MULTI
  affects:
    - app/services/multi_leg_service.py
    - app/services/polling_service.py
    - app/services/snapshot_service.py
    - app/services/signal_service.py
tech_stack:
  added: []
  patterns:
    - itertools.product para cartesiano de datas
    - cache-first com fallback SerpAPI (D-12)
    - Lazy import para evitar ciclo polling <-> multi_leg
key_files:
  created:
    - app/services/multi_leg_service.py
  modified:
    - app/services/polling_service.py
    - app/services/snapshot_service.py
    - app/services/signal_service.py
decisions:
  - Cap DATE_CANDIDATES_PER_LEG=7 com ancoragem em window_start e window_end (round-based sampling, dedup ordem-preservada)
  - One-way workaround: search_flights_ex(return_date == departure_date) per RESEARCH.md Open Q1
  - signal_service dispensa gate price_classification=LOW quando airline=MULTI (Rule 2)
  - Dedup multi em janela de 6h (vs 1h roundtrip), chave (group, total, dep, ret)
metrics:
  duration_minutes: 8
  completed_date: 2026-04-22
  tasks_total: 3
  tasks_completed: 3
  tests_green_new: 6
  commits: 3
  files_changed: 4
---

# Phase 36 Plan 02: Multi-Leg Service e Polling Branch Summary

Implementacao do coracao funcional da Phase 36: servico `multi_leg_service` com produto cartesiano cache-first, ramificacao do `polling_service._poll_group` para `mode=multi_leg`, dedup especifico de snapshots MULTI e ajuste de `signal_service` para disparar `PRECO_ABAIXO_HISTORICO` sobre totais multi sem depender de `typical_price_range` do SerpAPI.

## Servico criado

**app/services/multi_leg_service.py** (~230 linhas)

Exporta:
- `search_multi_leg_prices(db, group) -> FlightSnapshot | None` — busca e persiste
- `_candidate_dates(leg) -> list[date]` — amostragem ate 7 datas (ancorada em window_start/window_end via `round(i*total_days/n)`)
- `_is_valid_chain(dates, legs) -> bool` — valida min/max_stay entre legs consecutivas
- `_fetch_leg_price(db, leg, dep_date, passengers) -> dict | None` — cache-first (aceita `{"price":...}` ou `{"min_price":...}` do route_cache), fallback `flight_search.search_flights_ex`
- `_persist_multi_snapshot(db, group, legs, best_combo, prices) -> FlightSnapshot | None` — cria snapshot com airline=MULTI e details JSON; usa `is_duplicate_snapshot` com branch MULTI
- `_totals_stats(db, group)` + `_maybe_predict` — calcula mediana/stddev dos totais 90d e chama `price_prediction_service.predict_action` com `days_to_departure` do PRIMEIRO leg (Pitfall 3)

Constantes: `DATE_CANDIDATES_PER_LEG=7`, `HISTORICAL_WINDOW_DAYS=90`.

## Branch polling

**app/services/polling_service.py::_poll_group** recebe early-return para `mode=multi_leg`:
1. Chama `search_multi_leg_prices`; se retornar None, loga e retorna
2. `detect_signals(db, snapshot)` sobre o snapshot multi (price = total)
3. `should_alert(group)` gate + `compose_consolidated_email` + `send_email` (reusa helpers de `alert_service`, mantem check de recipient allowlist igual ao fluxo roundtrip)
4. Import lazy de `multi_leg_service` dentro da branch (evita ciclo)

**Pre-task discovery (grep):** `should_alert`, `_send_consolidated_alert` etc. NAO existem em `polling_service.py`. O fluxo roundtrip atual importa `should_alert` e `compose_consolidated_email` de `alert_service` e chama inline. Apliquei o mesmo padrao — nao criei helpers novos. Registrado como Deviation (Rule 3: blocking — plan assumia helpers locais que nao existem).

## Modificacao em snapshot_service

**is_duplicate_snapshot** ganha branch `airline == "MULTI"`: janela 6h, chave `(route_group_id, price, departure_date, return_date)` sem match de `origin`/`destination` (cadeia pode variar). Logica roundtrip intacta (janela 1h, match completo).

## Modificacao em signal_service (Rule 2)

**_check_preco_abaixo_historico** dispensa gate `price_classification == "LOW"` quando `snapshot.airline == "MULTI"`. Motivo: snapshots multi nao recebem `typical_price_range` do SerpAPI (cada leg e buscado isoladamente), portanto nunca teriam `price_classification` setado. O teste RED `test_signal_on_total_price` exigia a detecao funcionando sobre 10 snapshots historicos + 1 novo abaixo, sem classificar. Ajuste minimo e localizado.

## Testes — RED virou GREEN

| Arquivo | Teste | Estado pre-plan | Estado pos-plan |
|---------|-------|-----------------|-----------------|
| test_multi_leg_service.py | test_is_valid_chain | RED | GREEN |
| test_multi_leg_service.py | test_uses_route_cache_before_serpapi | RED | GREEN |
| test_multi_leg_service.py | test_persists_multi_snapshot_with_details | RED | GREEN |
| test_multi_leg_service.py | test_picks_cheapest_total | RED | GREEN |
| test_multi_leg_service.py | test_prediction_uses_total_median | RED | GREEN |
| test_multi_leg_polling.py | test_signal_on_total_price | RED | GREEN |

Full suite: `404 passed, 1 failed`. O unico fail restante e `test_multi_leg_email.py::test_consolidated_multi_has_chain_and_total` (RED marcado para Plan 04 no 36-01-SUMMARY, fora de escopo desta onda).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Helpers de alerta `should_alert`/`_send_consolidated_alert` nao existem em polling_service**
- **Found during:** Task 2 pre-task grep discovery
- **Issue:** Plano referenciava `should_alert(group)` e `_send_consolidated_alert(db, group, [snapshot], signals)` como se estivessem em `polling_service.py`. Grep retornou zero matches.
- **Fix:** Usei o padrao ja estabelecido no fluxo roundtrip de `_poll_group`: `should_alert` importado de `alert_service`, envio via `compose_consolidated_email` + `send_email` com allowlist de recipient.
- **Files modified:** app/services/polling_service.py
- **Commit:** 4a21c65

**2. [Rule 2 - Missing functionality] signal_service nao disparava PRECO_ABAIXO_HISTORICO em snapshots multi**
- **Found during:** Task 2 verificacao (test_signal_on_total_price falhou com "got {'JANELA_OTIMA'}")
- **Issue:** `_check_preco_abaixo_historico` exige `price_classification == "LOW"`, mas snapshots multi nunca recebem classification (cada leg e buscado isoladamente via cache/SerpAPI, sem `typical_price_range`).
- **Fix:** Branch minimo `if snapshot.airline != "MULTI" and snapshot.price_classification != "LOW": return None`. Para MULTI, comparacao contra media historica prossegue direto. Escopo formal do plan era services/*; signal_service e dependencia logica transparente — pequena mudanca documentada.
- **Files modified:** app/services/signal_service.py
- **Commit:** 4a21c65

**3. [Rule 1 - Algorithm] Amostragem de _candidate_dates perdia window_end quando total_days > cap-1**
- **Found during:** Task 1 teste test_picks_cheapest_total (reportou 5500 <= 4500 False)
- **Issue:** `step = total_days // (cap-1)` com total_days=7 e cap=7 dava step=1 e amostrava apenas [0..6], perdendo dia 7 (window_end). Resultava em apenas 1 combo valido dado o fixture com gap 20 dias e max_stay=14, impedindo o teste de escolher entre combos.
- **Fix:** Trocado para amostragem com `round(i * total_days / (cap-1))` que ancora em window_start e window_end; dedup preservando ordem. 3 combos validos passam o filtro temporal, teste escolhe o menor (4500).
- **Files modified:** app/services/multi_leg_service.py
- **Commit:** ae937db

## Must-Haves Verification

- [x] `search_multi_leg_prices` retorna FlightSnapshot com airline=MULTI e details JSON
- [x] Cada leg consulta route_cache primeiro; apenas em miss chama SerpAPI
- [x] Produto cartesiano respeita cap 7 e filtra por `_is_valid_chain`
- [x] Snapshot persiste com price=total_price, departure_date=primeiro leg, return_date=ultimo leg
- [x] `_poll_group` ramifica por `group.mode == "multi_leg"` e chama multi_leg_service
- [x] `signal_service.detect_signals` opera sobre snapshot.price (total)
- [x] `is_duplicate_snapshot` reconhece airline=MULTI com janela 6h
- [x] `price_prediction_service.predict_action` recebe `days_to_departure` do primeiro leg

## Self-Check: PASSED

Files created:
- FOUND: app/services/multi_leg_service.py

Files modified:
- FOUND: app/services/polling_service.py (branch mode=multi_leg em _poll_group)
- FOUND: app/services/snapshot_service.py (branch airline=MULTI em is_duplicate_snapshot)
- FOUND: app/services/signal_service.py (dispensa gate LOW para MULTI)

Commits:
- FOUND: ae937db feat(36-02): add multi_leg_service with cartesian product and cache-first fetch
- FOUND: 4a21c65 feat(36-02): branch polling_service for mode=multi_leg and enable signal on MULTI
- FOUND: c312b4b feat(36-02): branch is_duplicate_snapshot for airline=MULTI (Pitfall 2)
