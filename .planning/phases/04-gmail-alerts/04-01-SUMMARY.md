---
phase: 04-gmail-alerts
plan: 01
subsystem: alert-service
tags: [email, smtp, hmac, silenciamento, tdd]
dependency_graph:
  requires: [app/models.py, app/config.py]
  provides: [app/services/alert_service.py]
  affects: [app/services/polling_service.py, app/routes/alerts.py]
tech_stack:
  added: []
  patterns: [smtplib.SMTP_SSL, hmac.new + hmac.compare_digest, MIMEMultipart alternative]
key_files:
  created:
    - app/services/alert_service.py
    - tests/test_alert_service.py
  modified:
    - app/models.py
    - app/config.py
decisions:
  - "Reutiliza gmail_app_password como segredo HMAC — aceitavel para single-user sem surface de ataque"
  - "MIMEMultipart alternative com partes plain + html — fallback para leitores sem HTML"
  - "SMTP_SSL porta 465 com timeout=30 — previne travamento do ciclo de polling em falha de rede"
  - "hmac.compare_digest para verify_silence_token — previne timing attacks"
metrics:
  duration: 4min
  completed_date: "2026-03-25"
  tasks_completed: 2
  files_modified: 4
---

# Phase 04 Plan 01: Alert Service Summary

**One-liner:** alert_service.py com compose/send email MIME, HMAC silence token e checagem de silenciamento, implementado via TDD RED-GREEN com 14 testes passando.

## What Was Built

Servico de alertas por email com cinco funcoes exportadas:

- `compose_alert_email(signal, group)` — compoe MIMEMultipart com subject `[URGENCIA] SIGNAL_TYPE - nome`, partes plain/html, silence link HMAC-assinado
- `send_email(msg)` — envia via `smtplib.SMTP_SSL` porta 465, timeout 30s, login com gmail_app_password
- `generate_silence_token(group_id)` — HMAC-SHA256 deterministico, 32 hex chars, secreto = gmail_app_password
- `verify_silence_token(token, group_id)` — compara via `hmac.compare_digest` (timing-safe)
- `should_alert(group)` — retorna True se `silenced_until` e None ou expirou

Tambem adicionados:
- `RouteGroup.silenced_until` — coluna DateTime nullable no modelo
- `Settings.app_base_url` — campo com default `http://localhost:8000`

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | RED — Testes falhando, stubs, model + config | 105564b | app/models.py, app/config.py, app/services/alert_service.py (stub), tests/test_alert_service.py |
| 2 | GREEN — Implementacao completa, 14 testes passando | 1e940bd | app/services/alert_service.py, tests/test_alert_service.py |

## Verification

- `python -m pytest tests/test_alert_service.py -v` — 14 passed, 0 failed
- `python -m pytest tests/ -x -q` — 93 passed, 0 failed, 0 regressions
- `grep "silenced_until" app/models.py` — presente
- `grep "app_base_url" app/config.py` — presente
- `grep -c "def test_" tests/test_alert_service.py` — 14

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Testes usando MagicMock em vez de instancias SQLAlchemy**
- **Found during:** Task 1
- **Issue:** `RouteGroup.__new__()` e `DetectedSignal.__new__()` falham com `AttributeError: 'NoneType' object has no attribute 'set'` porque SQLAlchemy instrumenta os atributos e nao tolera instancias criadas via `__new__` sem a maquinaria ORM inicializada
- **Fix:** Substituiu os helpers `_make_group` e `_make_signal` por `MagicMock(spec=RouteGroup/DetectedSignal)` com atributos definidos manualmente
- **Files modified:** tests/test_alert_service.py
- **Commit:** 105564b

**2. [Rule 1 - Bug] Assertivas sobre corpo do email falhavam por base64**
- **Found during:** Task 2
- **Issue:** `msg.as_string()` retorna o corpo das partes MIME codificado em base64; assertivas de texto como `assert "2026-01-15" in body` nunca encontravam a string
- **Fix:** Criou helper `_decode_msg_body(msg)` que itera pelas partes e decodifica cada payload via `get_payload(decode=True).decode("utf-8")`. Ajustou assertiva de preco para `"3,500.00"` compativel com formato BRL
- **Files modified:** tests/test_alert_service.py
- **Commit:** 1e940bd

## Known Stubs

None — todas as funcoes estao implementadas e retornando dados reais.

## Self-Check: PASSED
