---
phase: 02-data-collection
plan: 01
subsystem: database
tags: [sqlalchemy, sqlite, orm, snapshots, booking-classes, gmail]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: "RouteGroup model, Base declarative, database.py, conftest.py fixtures"
provides:
  - "FlightSnapshot model (flight_snapshots table)"
  - "BookingClassSnapshot model (booking_class_snapshots table)"
  - "save_flight_snapshot service function"
  - "Gmail config fields (gmail_sender, gmail_app_password, gmail_recipient)"
affects: [02-data-collection, 03-signal-detection, 04-alerts]

# Tech tracking
tech-stack:
  added: [amadeus==12.0.0, apscheduler==3.11.2]
  patterns: [snapshot-persistence, parent-child-orm-relationship, cascade-delete-orphan]

key-files:
  created:
    - app/services/snapshot_service.py
    - tests/test_snapshot_service.py
  modified:
    - app/models.py
    - app/config.py
    - tests/test_config.py
    - requirements.txt

key-decisions:
  - "Used model_fields for Pydantic Settings field detection instead of hasattr (Pydantic v2 compatibility)"
  - "Cascade all,delete-orphan on booking_classes relationship for data integrity"

patterns-established:
  - "Snapshot pattern: FlightSnapshot as parent, BookingClassSnapshot as child with FK"
  - "Service function receives dict and creates ORM objects internally"

requirements-completed: [COLL-05]

# Metrics
duration: 3min
completed: 2026-03-25
---

# Phase 2 Plan 1: Snapshot Models and Persistence Summary

**FlightSnapshot + BookingClassSnapshot SQLAlchemy models with save_flight_snapshot service and Gmail config replacing Telegram**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-25T03:12:42Z
- **Completed:** 2026-03-25T03:15:40Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- FlightSnapshot model with price metrics (min, quartiles, max, classification) as nullable fields
- BookingClassSnapshot model with class_code, seats_available, segment_direction linked via FK
- save_flight_snapshot service function that persists snapshot + booking classes in one transaction
- Config updated: telegram fields removed, gmail_sender/gmail_app_password/gmail_recipient added
- 6 new tests all passing, full suite of 34 tests green

## Task Commits

Each task was committed atomically:

1. **Task 1: RED - Testes de modelos snapshot e servico de persistencia** - `32d5035` (test)
2. **Task 2: GREEN - Implementar modelos snapshot, snapshot_service e atualizar config** - `e58d08d` (feat)

_TDD flow: Task 1 = RED (6 tests failing), Task 2 = GREEN (6 tests passing)_

## Files Created/Modified
- `app/models.py` - Added FlightSnapshot and BookingClassSnapshot models
- `app/config.py` - Replaced telegram_* with gmail_* fields
- `app/services/snapshot_service.py` - save_flight_snapshot function
- `tests/test_snapshot_service.py` - 6 tests for persistence and config
- `tests/test_config.py` - Updated to check gmail fields instead of telegram
- `requirements.txt` - Added amadeus==12.0.0 and apscheduler==3.11.2

## Decisions Made
- Used model_fields dict for Pydantic Settings field detection (hasattr on class does not work with Pydantic v2 BaseSettings)
- Cascade "all, delete-orphan" on booking_classes relationship ensures child records are cleaned when parent is deleted

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated test_config.py to match new gmail fields**
- **Found during:** Task 2 (GREEN phase)
- **Issue:** Existing test_settings_has_all_fields checked for telegram_bot_token and telegram_chat_id which were removed
- **Fix:** Changed assertions to check for gmail_sender, gmail_app_password, gmail_recipient
- **Files modified:** tests/test_config.py
- **Verification:** All 34 tests passing
- **Committed in:** e58d08d (Task 2 commit)

**2. [Rule 1 - Bug] Fixed test_config_has_gmail_fields to use model_fields**
- **Found during:** Task 2 (GREEN phase)
- **Issue:** hasattr(Settings, "gmail_sender") returns False on Pydantic v2 BaseSettings class
- **Fix:** Changed to check Settings.model_fields dict instead of hasattr
- **Files modified:** tests/test_snapshot_service.py
- **Verification:** All 6 snapshot tests passing
- **Committed in:** e58d08d (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both necessary for correctness. No scope creep.

## Issues Encountered
None beyond the auto-fixed deviations.

## Known Stubs
None. All models have real fields, service function is fully implemented, config fields have empty string defaults (expected, user sets via .env).

## User Setup Required
None - no external service configuration required for this plan.

## Next Phase Readiness
- FlightSnapshot and BookingClassSnapshot models ready for Phase 2 Plan 2 (Amadeus client) to populate
- save_flight_snapshot ready to be called by the polling scheduler
- Gmail config fields ready for Phase 4 (alerts)

---
*Phase: 02-data-collection*
*Completed: 2026-03-25*
