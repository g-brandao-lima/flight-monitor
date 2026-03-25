---
phase: 03-signal-detection
plan: 01
subsystem: signal-detection
tags: [tdd, sqlalchemy, pytest, booking-class, signal]

requires:
  - phase: 02-data-collection
    provides: FlightSnapshot and BookingClassSnapshot models with polling data
provides:
  - DetectedSignal model with ix_signal_dedup composite index
  - 19 RED tests covering all 4 signal types plus deduplication
  - signal_service.py stub with detect_signals entry point
affects: [03-signal-detection plan 02 GREEN implementation, 03-signal-detection plan 03 integration]

tech-stack:
  added: []
  patterns: [TDD RED phase with stub services raising NotImplementedError, composite index for deduplication queries]

key-files:
  created:
    - app/services/signal_service.py
    - tests/test_signal_service.py
  modified:
    - app/models.py

key-decisions:
  - "19 tests (not 18) to cover all signal types, dedup, and edge cases thoroughly"
  - "DetectedSignal relationships to RouteGroup and FlightSnapshot for referential integrity"
  - "Index ix_signal_dedup on composite key for 12h deduplication window queries"

patterns-established:
  - "Test helpers _make_route_group and _make_snapshot for signal test data creation"
  - "Test classes organized by signal type (SIGN-01 through SIGN-05) plus edge cases"
  - "unittest.mock.patch on date for deterministic JANELA_OTIMA tests"

requirements-completed: [SIGN-01, SIGN-02, SIGN-03, SIGN-04, SIGN-05]

duration: 3min
completed: 2026-03-25
---

# Phase 3 Plan 1: Signal Detection TDD RED Summary

**DetectedSignal model with 12 fields, ix_signal_dedup index, and 19 failing RED tests covering BALDE_FECHANDO, BALDE_REABERTO, PRECO_ABAIXO_HISTORICO, JANELA_OTIMA, and deduplication**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-25T04:04:28Z
- **Completed:** 2026-03-25T04:08:00Z
- **Tasks:** 3 (1 checkpoint auto-approved, 2 auto)
- **Files modified:** 3

## Accomplishments
- DetectedSignal model added to app/models.py with all 12 fields and composite dedup index
- signal_service.py created with detect_signals stub raising NotImplementedError
- 19 RED tests written covering all 4 signal types, deduplication, and edge cases
- All 19 tests fail as expected (TDD RED phase confirmed)
- All 55 existing tests continue to pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Spec approval** - auto-approved (checkpoint:human-verify, auto mode)
2. **Task 2: DetectedSignal model + signal_service stubs** - `fba04b0` (feat)
3. **Task 3: RED tests for SIGN-01 through SIGN-05** - `551b0b3` (test)

## Files Created/Modified
- `app/models.py` - Added DetectedSignal class with 12 fields, relationships, and ix_signal_dedup index
- `app/services/signal_service.py` - Created with detect_signals stub (NotImplementedError)
- `tests/test_signal_service.py` - 19 failing tests organized in 6 test classes

## Decisions Made
- 19 tests instead of minimum 18 to provide better coverage of edge cases
- DetectedSignal has explicit relationships to RouteGroup and FlightSnapshot
- Composite index ix_signal_dedup covers route_group_id, origin, destination, departure_date, return_date, signal_type

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Plan 02 (GREEN) can implement detect_signals against these 19 tests
- All test infrastructure ready: helpers, fixtures, mock patterns established
- DetectedSignal model schema is stable for implementation

---
*Phase: 03-signal-detection*
*Completed: 2026-03-25*
