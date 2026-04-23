---
phase: 36
slug: multi-leg
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-22
---

# Phase 36 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pytest.ini (or pyproject.toml) |
| **Quick run command** | `pytest tests/test_multi_leg*.py -x --tb=short` |
| **Full suite command** | `pytest -x --tb=short` |
| **Estimated runtime** | ~60 seconds (phase slice) |

---

## Sampling Rate

- **After every task commit:** Run quick command for affected test file
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

*Planner fills this table. One row per task with automated verification, mapped to a MULTI-XX requirement.*

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | MULTI-XX | TBD | TBD | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_multi_leg_model.py` — stubs for MULTI-01 (schema + validacao temporal)
- [ ] `tests/test_multi_leg_service.py` — stubs para produto cartesiano e agregacao de precos (MULTI-03)
- [ ] `tests/test_multi_leg_signal.py` — stubs para signal detection sobre total (MULTI-04)
- [ ] `tests/test_multi_leg_routes.py` — stubs para endpoints UI (MULTI-01, MULTI-02)
- [ ] `tests/conftest.py` — fixture `multi_leg_group_factory` se nao existir

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Email consolidado renderiza roteiro multi-leg | MULTI-04 (email) | Render visual de template HTML/texto em cliente real | Criar grupo multi, esperar job consolidated_email, abrir email em Gmail |
| Dashboard card multi-leg visualmente alinhado ao card roundtrip | D-16/18 | Paridade visual | Acessar /dashboard com grupo multi ativo, comparar card vs roundtrip |
| Wizard UI de N trechos | MULTI-01 | Interacao JS dinamica (add/remove leg) | Criar grupo via /grupos/novo?mode=multi |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
