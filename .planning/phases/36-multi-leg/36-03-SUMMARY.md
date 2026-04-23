---
phase: 36-multi-leg
plan: 03
subsystem: routes-and-ui
tags: [route, template, jinja2, js-vanilla, multi-leg, wave-2]
dependency_graph:
  requires: [RouteGroupLeg, RouteGroupMultiCreate, multi_leg_group_factory]
  provides: [POST /groups multi_leg dispatcher, create.html multi builder, edit.html multi preload]
  affects:
    - app/routes/dashboard.py
    - app/templates/dashboard/create.html
    - app/templates/dashboard/edit.html
    - tests/test_multi_leg_routes.py
tech_stack:
  added: []
  patterns: [FastAPI form dispatch, Pydantic ValidationError handling, Jinja2 conditional preload, JS vanilla dynamic builder]
key_files:
  created: []
  modified:
    - app/routes/dashboard.py
    - app/templates/dashboard/create.html
    - app/templates/dashboard/edit.html
    - tests/test_multi_leg_routes.py
decisions:
  - POST /groups adicionado em dashboard.py (nao em route_groups.py) porque route_groups.py e JSON API legada nao usada pelos templates
  - Formularios separados (roundtrip posta em /groups/create, multi posta em /groups) evita conflito de campos entre os dois fluxos
  - Builder duplicado inline em create.html e edit.html (sem partial Jinja) porque reuso e limitado a 2 templates e a duplicacao mecanica e mais simples que extrair partial
  - Auto-calculo de janela preserva data-manual-override para trechos editados manualmente
metrics:
  duration_minutes: 8
  completed_date: 2026-04-23
  tasks_total: 5
  tasks_completed: 5
  tests_green: 3
  commits: 4
  files_changed: 4
---

# Phase 36 Plan 03: Multi-Leg Routes and UI Summary

UI e handler HTTP para criacao e edicao de grupos multi-trecho. Adiciona dispatcher POST `/groups` que parseia `legs[N][field]`, valida via `RouteGroupMultiCreate` e persiste `RouteGroup(mode="multi_leg")` + `RouteGroupLeg[]`. Templates `create.html` e `edit.html` ganham toggle "Tipo de roteiro" (Roundtrip simples / Multi-trecho) e construtor dinamico em JS vanilla com auto-calculo de janelas, validacao inline pt-BR e hook `__PRELOADED_LEGS__` para edicao.

## Handler de rota (app/routes/dashboard.py)

- **Novo endpoint `POST /groups`**: dispatcher por `mode`. Se `mode == "multi_leg"`, parseia `legs[N][field]` via `_parse_legs_from_form`, valida via `RouteGroupMultiCreate`, cria `RouteGroup` + `RouteGroupLeg[]` e redireciona 303 para `/?msg=grupo_multi_criado`. Se `mode != "multi_leg"`, redireciona para `/groups/create` (fluxo roundtrip existente preservado).
- **Handler de edicao `POST /groups/{group_id}/edit`**: reescrito como async para aceitar form dinamico. Se `mode == "multi_leg"`, valida via Pydantic, limpa `group.legs` (cascade delete-orphan) e recria. Fluxo roundtrip preservado com mesmos campos originais (origins, destinations, duration_days, travel_start, travel_end, etc).
- **Parser helper `_parse_legs_from_form`**: usa regex `legs\[(\d+)\]\[(\w+)\]` sobre `form.multi_items()`, normaliza tipos (date, int nullable), ordena por indice do form. Aceita indices 0-based ou 1-based.
- **Erros Pydantic** renderizados em `create.html`/`edit.html` via `templates.TemplateResponse` com `error` pt-BR (mensagem desembrulhada de "Value error, ...").

## Templates

### create.html
- Toggle com dois botoes em `<section class="mode-toggle">` + hidden input `id="mode-input"` para compatibilidade.
- `<section data-mode="roundtrip">` envolve o form existente (submit em `/groups/create`). Campos e autocomplete de aeroporto intocados.
- `<section data-mode="multi">` contem form separado submetendo em `/groups` com `<input type="hidden" name="mode" value="multi_leg">`, `<template id="leg-template">`, `<div id="legs-container">` e botao `+ Adicionar trecho`.
- Toggle `.active` troca `display` das sections via JS.
- CSS 100% via tokens de `base.html` (`--bg-1`, `--brand-500`, `--danger-500`, `--sp-*`). Unico hex hardcoded e `#fff` para texto sobre `--brand-500` (aprovado pelo UI-SPEC como excecao). Flatpickr mantem hex legado herdado (fora do escopo de Phase 36).
- Script vanilla: `addLeg`, `removeLeg`, `renumberAndToggle`, `recalcLegs` (auto-calculo leg[N+1].window_start = leg[N].window_end + leg[N].min_stay_days, respeitando `data-manual-override`), `validateChainLocal` (copy pt-BR exata do UI-SPEC), `setMode`. Hook `window.__PRELOADED_LEGS__` presente para reuso em edit.html.

### edit.html
- Mesma estrutura de toggle + sections + template + script, duplicada inline.
- Estado inicial do toggle baseado em `group.mode`: se `multi_leg`, a section multi aparece ativa e o preload roda via `window.__PRELOADED_LEGS__`.
- Bloco Jinja `{% if group.mode == "multi_leg" %}` injeta `window.__PRELOADED_LEGS__` com JSON dos legs ordenados antes do script do builder.
- Script detecta preload, forca `setMode('multi_leg')`, limpa container e popula fieldsets com valores de cada leg, marcando `data-manual-override=true` para preservar edicoes.
- Form multi submete em `/groups/{id}/edit` (mesmo endpoint, handler ramifica por `mode`).
- Fallback `<input type="hidden" name="mode" id="mode-input" value="{{ group.mode }}">` garante mode correto mesmo se JS falhar.

## Testes

| Arquivo | Teste | Estado |
|---------|-------|--------|
| test_multi_leg_routes.py | test_create_multi_leg_group_valid | GREEN |
| test_multi_leg_routes.py | test_create_multi_leg_group_invalid_chain | GREEN |
| test_multi_leg_routes.py | test_create_multi_leg_group_server_validation_runs_even_if_client_passes | GREEN |

- Full suite: 405 passed, 1 failed (test_consolidated_multi_has_chain_and_total — RED esperado para Plan 04)
- Zero regressao introduzida por Phase 36-03.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Plan frontmatter aponta app/routes/route_groups.py mas route real e /groups no dashboard.py**
- **Found during:** Task 1 leitura do codigo
- **Issue:** `app/routes/route_groups.py` existe como JSON API legada prefixada em `/route-groups`, nao usada pelos templates. Os endpoints `/groups/create`, `/groups/{id}/edit` reais vivem em `app/routes/dashboard.py`. Os testes em `test_multi_leg_routes.py` postam em `/groups` (sem `-`).
- **Fix:** Adicionei `POST /groups` e modifiquei `POST /groups/{id}/edit` em `dashboard.py`. Import `RouteGroupLeg` e `RouteGroupMultiCreate` adicionados.
- **Files modified:** app/routes/dashboard.py
- **Commit:** 7ff38a7

**2. [Rule 3 - Blocking] Modos existentes (normal/exploracao) conflitam com modes do UI-SPEC (roundtrip/multi_leg)**
- **Found during:** Task 2a
- **Issue:** `RouteGroup.mode` ja tinha valores `normal`/`exploracao`. O UI-SPEC de Phase 36 introduz `roundtrip`/`multi_leg`. Unificar em um unico campo/form quebraria fluxos existentes.
- **Fix:** Forms separados: o form roundtrip mantem seu select `mode=normal|exploracao` e posta em `/groups/create` (intocado). O form multi posta em `/groups` com `mode=multi_leg` hardcoded. Toggle apenas troca qual form esta visivel. Isso preserva 100% do comportamento legado.
- **Files modified:** app/templates/dashboard/create.html, app/templates/dashboard/edit.html
- **Commits:** 83f9788, d713258

### Intentional simplifications

- **Sem partial Jinja para o builder:** criacao de `_multi_leg_builder.html` adiaria apenas ~200 linhas duplicadas entre 2 templates. Duplicacao inline e mais simples de ler e manter neste escopo; decisao documentada.
- **Auto-approve do checkpoint human-verify:** workflow.auto_advance esta `true` na config; checkpoint aprovado automaticamente com log.

## Deferred Issues

**1. Checkpoint humano nao executado interativamente**
- Auto-aprovado conforme config `workflow.auto_advance=true`.
- Verificacao visual real (server rodando, login Google, clicar toggles) fica para validacao manual posterior pelo usuario.

## Self-Check: PASSED

Files modified:
- FOUND: app/routes/dashboard.py
- FOUND: app/templates/dashboard/create.html
- FOUND: app/templates/dashboard/edit.html
- FOUND: tests/test_multi_leg_routes.py

Commits:
- FOUND: 7ff38a7 feat(36-03): add POST /groups dispatcher for multi_leg + edit handler
- FOUND: 83f9788 feat(36-03): add mode toggle and multi-leg builder to create.html
- FOUND: d713258 feat(36-03): add multi-leg builder and preload to edit.html
- FOUND: 47db4c6 test(36-03): add server-side validation regression test
