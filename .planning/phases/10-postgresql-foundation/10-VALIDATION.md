---
phase: 10
slug: postgresql-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-28
---

# Phase 10 — Validation Strategy

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
| 10-01-01 | 01 | 1 | DB-01 | unit | `python -m pytest tests/ -x -q` | ✅ | ⬜ pending |
| 10-01-02 | 01 | 1 | DB-02 | unit | `alembic upgrade head` | ❌ W0 | ⬜ pending |
| 10-02-01 | 02 | 1 | DB-03 | unit | `python -m pytest tests/ -v` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `alembic/` directory initialized with `alembic init`
- [ ] `alembic.ini` configured with sqlalchemy.url placeholder
- [ ] `alembic/env.py` importing Base from app.models

*Existing test infrastructure (conftest.py with SQLite in-memory + StaticPool) covers DB-03.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Dados sobrevivem redeploy no Render | DB-01 | Requer deploy real no Render + Neon.tech | 1. Deploy no Render 2. Criar grupo 3. Redeploy 4. Verificar grupo persiste |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
