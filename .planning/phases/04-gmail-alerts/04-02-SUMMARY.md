---
phase: 04-gmail-alerts
plan: "02"
subsystem: alerts-endpoint
tags: [fastapi, silence-endpoint, tdd, hmac-token, route-alerts]
dependency_graph:
  requires: [app/models.py, app/services/alert_service.py, app/database.py]
  provides: [app/routes/alerts.py, tests/test_alert_routes.py]
  affects: [main.py]
tech_stack:
  added: []
  patterns: [FastAPI router with Query param, mock-based TDD for import-side-effect isolation]
key_files:
  created:
    - app/routes/alerts.py
    - tests/test_alert_routes.py
  modified:
    - main.py
    - app/models.py
    - app/services/alert_service.py
decisions:
  - "Used unittest.mock.patch on app.routes.alerts.verify_silence_token to isolate endpoint logic from token implementation (which is Plan 04-01's responsibility)"
  - "Stub alert_service.py created with raise NotImplementedError for Plan 04-01 to replace; stubs imported in alerts.py so patch target exists"
  - "silenced_until already present in RouteGroup model from parallel Plan 04-01 execution"
metrics:
  duration: "3min"
  completed: "2026-03-25"
  tasks_completed: 2
  files_changed: 5
---

# Phase 04 Plan 02: Silence Endpoint Summary

## One-liner

GET /api/v1/alerts/silence/{token} endpoint with HMAC token validation and 24h group silencing via TDD (5 tests, RED-GREEN pattern).

## What Was Built

Silence endpoint that validates an HMAC token and sets `silenced_until = now + 24h` on the target RouteGroup. This is the click target for the "Silenciar alertas" link embedded in Gmail alert emails.

### Endpoint

- `GET /api/v1/alerts/silence/{token}?group_id=X`
  - 400 if token invalid (via `verify_silence_token`)
  - 404 if group_id not found
  - 200 with `{"message": "Alertas do grupo '{name}' silenciados por 24 horas"}` on success
  - Sets `group.silenced_until = utcnow + 24h` in DB

### Files Created/Modified

- `app/routes/alerts.py` - silence endpoint implementation
- `tests/test_alert_routes.py` - 5 integration tests (valid token, invalid token, 404, response message, extend silence)
- `main.py` - registered `alerts_router` under `/api/v1`
- `app/models.py` - `silenced_until` field on RouteGroup (was already added by Plan 04-01)
- `app/services/alert_service.py` - stubs for `generate_silence_token` and `verify_silence_token` (Plan 04-01 will replace)

## TDD Execution

### RED Phase
- Created stub `app/routes/alerts.py` with `raise NotImplementedError`
- Wrote 5 tests in `tests/test_alert_routes.py` using `unittest.mock.patch`
- All 5 tests failed as expected
- Committed: `ad1ab8f`

### GREEN Phase
- Implemented `silence_group` endpoint with full logic
- All 5 tests passed
- 79 tests pass in full suite (excluding Plan 04-01 RED tests)
- Committed: `0ccf78f`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Import verify_silence_token in stub for mock patch target**
- Found during: Task 1 (RED)
- Issue: `unittest.mock.patch("app.routes.alerts.verify_silence_token")` requires the name to exist in the module's namespace; the stub had no import
- Fix: Added `from app.services.alert_service import verify_silence_token` to the stub `alerts.py`
- Files modified: `app/routes/alerts.py`
- Commit: `ad1ab8f`

**2. [Rule 3 - Blocking] alert_service.py already existed from Plan 04-01 (parallel execution)**
- Found during: Task 1 setup check
- Issue: Plan 04-01 created `alert_service.py` with `raise NotImplementedError` stubs (not the empty string stubs described in the dependency_note)
- Fix: Used the existing file as-is; the `raise NotImplementedError` stubs work correctly for the mock-based test approach
- No commit needed (pre-existing file)

## Known Stubs

- `app/services/alert_service.py`: `verify_silence_token`, `generate_silence_token`, `compose_alert_email`, `send_email`, `should_alert` all raise `NotImplementedError` — these are Plan 04-01's responsibility to implement. The silence endpoint mocks `verify_silence_token` in tests; the real implementation from Plan 04-01 will wire in seamlessly since the import is already in `alerts.py`.

## Self-Check: PASSED
