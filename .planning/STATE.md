---
gsd_state_version: 1.0
milestone: v2.1
milestone_name: Clareza de Preco e Robustez
status: roadmap created
stopped_at: null
last_updated: "2026-04-03T00:00:00.000Z"
progress:
  total_phases: 7
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-03)

**Core value:** Detectar o momento certo de comprar uma passagem antes que o preco suba, apresentando o preco de forma clara e imediata para o usuario tomar decisao rapida.
**Current focus:** v2.1 roadmap created, ready to plan Phase 15

## Current Position

Phase: 15 (CI Pipeline) - first of 7 v2.1 phases (15-21)
Plan: Not yet planned
Status: Ready to plan
Last activity: 2026-04-03 — Roadmap v2.1 created with 7 phases, 14 requirements mapped

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

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [v2.1]: CI Pipeline first — safety net before JWT refactoring (research recommendation)
- [v2.1]: Passengers fix before cache — cache key needs correct passengers count
- [v2.1]: JWT before rate limiting — request.state.user_id improves slowapi key_func
- [v2.1]: Legacy removal last — blocks nothing, not blocked by anything

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
