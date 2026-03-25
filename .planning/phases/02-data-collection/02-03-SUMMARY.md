---
phase: 02-data-collection
plan: 03
subsystem: data-collection
tags: [apscheduler, polling, amadeus, booking-classes, background-scheduler]

requires:
  - phase: 02-data-collection/02-01
    provides: "save_flight_snapshot persistence layer"
  - phase: 02-data-collection/02-02
    provides: "AmadeusClient with search, availability, price metrics"
provides:
  - "run_polling_cycle orchestrating data collection for all active groups"
  - "BackgroundScheduler with 6-hour polling interval"
  - "Per-group error isolation in polling cycle"
  - "Date pair generation (every 3 days within travel period)"
  - "Booking class extraction from availability response"
affects: [03-signal-detection, 04-alerts]

tech-stack:
  added: []
  patterns: [per-group-error-isolation, date-pair-generation, lifespan-scheduler-integration]

key-files:
  created:
    - app/services/polling_service.py
    - app/scheduler.py
  modified:
    - main.py
    - tests/test_polling_service.py
    - tests/test_scheduler.py

key-decisions:
  - "Date pairs generated every 3 days within travel period for balanced API budget usage"
  - "Per-group try/except ensures one failing group does not block others"
  - "Scheduler uses module-level BackgroundScheduler instance for clean init/shutdown lifecycle"

patterns-established:
  - "Per-group error isolation: each group wrapped in try/except within polling loop"
  - "Lifespan scheduler pattern: init_scheduler in startup, shutdown_scheduler in teardown"
  - "Date combination generation: 3-day step within travel_start to travel_end window"

requirements-completed: [COLL-01, COLL-06]

duration: 3min
completed: 2026-03-25
---

# Phase 2 Plan 3: Polling Service + Scheduler Summary

**APScheduler-driven 6-hour polling cycle that orchestrates Amadeus data collection across all active route groups with per-group error isolation**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-25T03:20:45Z
- **Completed:** 2026-03-25T03:23:18Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Polling service that iterates active groups, generates origin x destination x date combinations, fetches top 5 offers, captures availability (booking classes) and price metrics, and persists complete snapshots
- BackgroundScheduler with IntervalTrigger(hours=6) integrated into FastAPI lifespan
- Per-group error handling ensuring one group's failure does not crash the entire polling cycle
- 10 new tests covering all behavior (55 total tests passing)

## Task Commits

Each task was committed atomically:

1. **Task 1: RED - Testes do polling_service e scheduler** - `a3e3f11` (test)
2. **Task 2: GREEN - Implementar polling_service, scheduler e main.py** - `97fe0dd` (feat)

## Files Created/Modified
- `app/services/polling_service.py` - Orchestrates polling cycle: group iteration, date/route combos, offer processing, booking class extraction
- `app/scheduler.py` - BackgroundScheduler with 6-hour interval job calling run_polling_cycle
- `main.py` - Lifespan updated with init_scheduler/shutdown_scheduler
- `tests/test_polling_service.py` - 8 tests: skip unconfigured, active/inactive groups, error isolation, date/route combos, snapshot data, missing metrics
- `tests/test_scheduler.py` - 2 tests: job registration with 6h interval, clean shutdown

## Decisions Made
- Date pairs generated every 3 days within travel period for balanced API budget usage
- Per-group try/except ensures one failing group does not block others
- Scheduler uses module-level BackgroundScheduler instance for clean init/shutdown lifecycle

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Known Stubs

None - all data flows are fully wired.

## Next Phase Readiness
- Phase 2 (data-collection) is complete: all 3 plans executed
- Signal detection (Phase 3) can now query FlightSnapshot history to detect booking class changes and price signals
- Polling cycle produces the snapshots that signal detection will analyze

## Self-Check: PASSED

- All 5 files FOUND
- Commit a3e3f11 FOUND
- Commit 97fe0dd FOUND
- 55 tests passing

---
*Phase: 02-data-collection*
*Completed: 2026-03-25*
