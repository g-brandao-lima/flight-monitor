---
phase: 05-web-dashboard
plan: 02
subsystem: ui
tags: [fastapi, jinja2, chartjs, html, css, responsive]

requires:
  - phase: 05-web-dashboard plan 01
    provides: dashboard_service.py with get_groups_with_summary, get_price_history, format_price_brl
provides:
  - Dashboard HTML index listing groups with price and signal badges
  - Dashboard HTML detail with Chart.js price history graph
  - Base template with responsive CSS and navigation
  - Dashboard router registered in main.py
affects: [05-web-dashboard plan 03]

tech-stack:
  added: [Jinja2Templates, Chart.js 4.5.1 CDN]
  patterns: [template inheritance via extends/block, inline CSS per D-11, format function in template context]

key-files:
  created:
    - app/routes/dashboard.py
    - app/templates/base.html
    - app/templates/dashboard/index.html
    - app/templates/dashboard/detail.html
    - tests/test_dashboard.py
  modified:
    - main.py
    - tests/test_app_startup.py

key-decisions:
  - "Inline CSS in base.html instead of external stylesheet (per D-11 constraint, no JS framework)"
  - "format_price_brl passed as template context function for Jinja2 usage"
  - "HTMLResponse with status_code=404 for nonexistent groups instead of HTTPException"

patterns-established:
  - "Template inheritance: dashboard pages extend base.html via block content/head/title"
  - "Signal badge color mapping: #94a3b8 (none), #eab308 (MEDIA), #f97316 (ALTA), #ef4444 (MAXIMA)"
  - "Chart.js integration: CDN in head block, tojson filter for data"

requirements-completed: [ALRT-03, DASH-01, DASH-02, DASH-05]

duration: 3min
completed: 2026-03-25
---

# Phase 05 Plan 02: Dashboard HTML Routes Summary

**Dashboard index with group cards showing BRL prices and urgency badges, detail page with Chart.js price history graph, responsive layout with Jinja2 template inheritance**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-25T19:35:40Z
- **Completed:** 2026-03-25T19:38:40Z
- **Tasks:** 1
- **Files modified:** 7

## Accomplishments
- Dashboard index lists all route groups with cheapest price formatted in BRL and colored signal badges
- Dashboard detail shows Chart.js line chart for cheapest route price history or "Nenhum dado coletado ainda" empty state
- Responsive base template with viewport meta, nav links, media queries for mobile
- 12 integration tests covering all routes, badges, chart data, empty states, and 404

## Task Commits

Each task was committed atomically:

1. **Task 1: Dashboard routes + templates + tests** - `61e2d9a` (feat)

## Files Created/Modified
- `app/routes/dashboard.py` - FastAPI router with GET / (index) and GET /groups/{id} (detail)
- `app/templates/base.html` - Base template with nav, viewport, responsive CSS
- `app/templates/dashboard/index.html` - Group cards with price and signal badges
- `app/templates/dashboard/detail.html` - Chart.js price history or empty state
- `tests/test_dashboard.py` - 12 integration tests for dashboard routes
- `main.py` - Registered dashboard_router, removed old JSON root endpoint
- `tests/test_app_startup.py` - Updated to expect HTML response at GET /

## Decisions Made
- Inline CSS in base.html (no external stylesheet, per D-11 no JS framework constraint)
- format_price_brl passed as template context function rather than pre-formatting in route
- HTMLResponse with 404 status for nonexistent groups (simple, no exception overhead)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated test_app_startup to expect HTML instead of JSON**
- **Found during:** Task 1 (full suite verification)
- **Issue:** test_app_starts_and_responds expected JSON {"status": "ok"} from GET / but dashboard now returns HTML
- **Fix:** Updated assertion to check for text/html content-type and "Flight Monitor" in HTML
- **Files modified:** tests/test_app_startup.py
- **Verification:** Full test suite (130 tests) passes
- **Committed in:** 61e2d9a (part of task commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Necessary fix for existing test that conflicted with new dashboard route. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all data flows are wired to dashboard_service.py which queries real database.

## Next Phase Readiness
- Dashboard index and detail fully functional
- Ready for Plan 03 (group create/edit forms)
- Navigation links to /groups/create already in place (target for Plan 03)

---
*Phase: 05-web-dashboard*
*Completed: 2026-03-25*
