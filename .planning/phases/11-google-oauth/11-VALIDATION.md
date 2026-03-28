---
phase: 11
slug: google-oauth
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-28
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3.5 |
| **Config file** | pyproject.toml |
| **Quick run command** | `python -m pytest tests/ -x -q` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 11-01-01 | 01 | 1 | AUTH-01 | unit | `python -m pytest tests/ -x -q` | ❌ W0 | ⬜ pending |
| 11-01-02 | 01 | 1 | AUTH-02 | unit | `python -m pytest tests/ -x -q` | ❌ W0 | ⬜ pending |
| 11-02-01 | 02 | 1 | AUTH-03 | unit | `python -m pytest tests/ -x -q` | ❌ W0 | ⬜ pending |
| 11-02-02 | 02 | 1 | AUTH-04 | unit | `python -m pytest tests/ -x -q` | ❌ W0 | ⬜ pending |
| 11-03-01 | 03 | 2 | AUTH-05 | unit | `python -m pytest tests/ -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_auth.py` — test stubs for Google OAuth flow (login, callback, logout, session)
- [ ] `tests/conftest.py` — auth fixtures (test_user, authenticated_client) added before middleware
- [ ] Auth fixtures must work with existing SQLite in-memory test setup

*Critical: 188 existing tests will break when auth middleware is added. Fixtures must exist first.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Google OAuth redirect flow | AUTH-01 | Requires real Google OAuth consent screen | 1. Configure Google Cloud Console 2. Click "Entrar com Google" 3. Authorize 4. Verify redirect to /dashboard |
| Session persists across tabs | AUTH-02 | Browser behavior cannot be tested in pytest | 1. Login 2. Open new tab 3. Navigate to /dashboard 4. Verify still logged in |
| Google profile photo in header | AUTH-04 | Requires real Google profile data | 1. Login with Google account that has photo 2. Verify photo appears in header |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
