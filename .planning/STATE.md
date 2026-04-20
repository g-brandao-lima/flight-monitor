---
gsd_state_version: 1.0
milestone: v2.2
milestone_name: UX Polish e Quick Wins
status: roadmap created
stopped_at: null
last_updated: "2026-04-20T18:00:00.000Z"
progress:
  total_phases: 8
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-03)

**Core value:** Detectar o momento certo de comprar uma passagem antes que o preco suba, apresentando o preco de forma clara e imediata para o usuario tomar decisao rapida.
**Current focus:** v2.2 roadmap created, executing 8 UX polish + engagement quick-win phases

## Current Position

Phase: 24 (Admin Stats Panel) - first of 8 v2.2 phases (24-31)
Plan: Implementing inline
Status: In progress
Last activity: 2026-04-20 — v2.1 shipped, v2.2 roadmap created with 8 phases from research docs

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**

- Total plans completed: 32
- Average duration: ~3min
- Total execution time: ~100min

**Recent Trend:**

- Last 5 plans: 4min, 6min, 4min, 2min, 3min
- Trend: Stable

## Accumulated Context

### Roadmap Evolution

- Phase 15.1 inserted after Phase 15: Security Emergency Fix (URGENT - vazamento de dados em /api/v1/route-groups/ + rate limit login) - 2026-04-20
- Phase 17.1 inserted after Phase 17: Price Source Indicator (coluna source em FlightSnapshot + badge visual) - 2026-04-20
- Phase 22 added: Historical Context in Alerts (email e UI mostram "X% abaixo da média dos últimos 90 dias") - 2026-04-20
- Phase 23 added: Inventory Signal Empirical Validation (análise SQL dos snapshots para medir acerto do sinal K/Q/V) - 2026-04-20

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [v2.1]: CI Pipeline first — safety net before JWT refactoring (research recommendation)
- [v2.1]: Passengers fix before cache — cache key needs correct passengers count
- [v2.1]: JWT before rate limiting — request.state.user_id improves slowapi key_func
- [v2.1]: Legacy removal last — blocks nothing, not blocked by anything
- [v2.1, 2026-04-20]: Pesquisa de mercado validou gaps: contexto histórico e WhatsApp ausentes no BR
- [v2.1, 2026-04-20]: Kiwi Tequila como fonte complementar (markup no checkout), SerpAPI mantém como primária
- [v2.1, 2026-04-20]: fast-flights marcado para remoção (scraping frágil, retorna vazio silenciosamente)

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 18]: JWT migration touches conftest.py (base of 218+ tests) — CI must be active before this phase
- [Phase 18]: OAuth flow needs manual testing after JWT change (Google callback)
- [Phase 21]: Verify no tests or services reference booking_classes before removing

## Session Continuity

Last session: 2026-04-03
Stopped at: Roadmap v2.1 created
Resume file: None
