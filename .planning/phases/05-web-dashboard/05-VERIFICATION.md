---
phase: 05-web-dashboard
verified: 2026-03-25T20:00:00Z
status: human_needed
score: 7/7 must-haves verified
re_verification: false
human_verification:
  - test: "Abrir http://localhost:8000/ no navegador e verificar que a lista de grupos exibe preco formatado, badges coloridos e layout responsivo em ~375px de largura"
    expected: "Cards de grupos com preco em BRL (R$ X.XXX,XX), badge de sinal com cor correta (cinza/amarelo/laranja/vermelho), layout single-column em tela estreita"
    why_human: "Rendering visual, responsividade e CSS inline nao sao verificaveis por testes automatizados"
  - test: "Clicar em um grupo e verificar grafico Chart.js com historico de precos"
    expected: "Grafico de linha carregado via CDN cdn.jsdelivr.net/npm/chart.js@4.5.1, eixos visiveis, dados de preco plotados"
    why_human: "Renderizacao do canvas e execucao de JavaScript nao sao verificaveis em testes de integracao com TestClient"
  - test: "Criar novo grupo via formulario (/groups/create), submeter, confirmar redirecionamento para /"
    expected: "Grupo aparece na lista principal apos criacao; codigos IATA em minuscula sao convertidos para maiusculo automaticamente"
    why_human: "Comportamento de redirect e atualizacao da pagina requer browser real"
  - test: "Editar grupo existente, verificar campos pre-preenchidos, salvar e confirmar atualizacao"
    expected: "Inputs do formulario de edicao mostram valores atuais do grupo; apos salvar, grupo aparece atualizado na lista"
    why_human: "Verificacao visual de valores pre-preenchidos requer browser"
  - test: "Clicar em Desativar em um grupo e verificar indicador visual de inativo"
    expected: "Card do grupo aparece com opacidade reduzida e badge 'Inativo'; botao muda para 'Ativar'"
    why_human: "Mudanca visual de estado requer browser"
---

# Phase 05: Web Dashboard Verification Report

**Phase Goal:** Usuario pode visualizar o estado atual de todos os grupos, historico de precos e gerenciar grupos pelo navegador
**Verified:** 2026-03-25T20:00:00Z
**Status:** human_needed
**Re-verification:** No - initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | get_groups_with_summary retorna todos os grupos com melhor preco atual e sinal mais urgente nas ultimas 12h | VERIFIED | Implementacao em `app/services/dashboard_service.py` linhas 10-58; 6 testes cobrindo happy path, edge cases, sinal antigo e sem snapshots; 11/11 testes passando |
| 2 | get_price_history retorna labels e prices para a rota mais barata de um grupo nos ultimos 14 dias | VERIFIED | Implementacao em `app/services/dashboard_service.py` linhas 62-102; 4 testes cobrindo happy path, filtragem de rota, grupo vazio e cutoff de 14 dias |
| 3 | Grupo sem snapshots retorna cheapest_snapshot=None e chart_data vazio | VERIFIED | `test_get_groups_with_summary_no_snapshots` e `test_get_price_history_empty_group` passando; template mostra "Aguardando coleta" e "Nenhum dado coletado ainda" |
| 4 | GET / retorna HTML com lista de todos os grupos, melhor preco atual formatado em BRL e badge de sinal ativo | VERIFIED | `app/routes/dashboard.py` GET "/" chama `get_groups_with_summary` e passa `format_price_brl` como funcao no context; `index.html` renderiza preco e badges; `test_index_shows_cheapest_price` e `test_index_shows_signal_badge_alta` passando |
| 5 | GET /groups/{id} retorna HTML com dados JSON para Chart.js mostrando historico de precos da rota mais barata | VERIFIED | `dashboard_detail` chama `get_price_history`; `detail.html` usa `{{ chart_data \| tojson }}` com CDN Chart.js; `test_detail_shows_chart_data` passando |
| 6 | Usuario pode criar e editar Grupo de Rota pelo formulario no dashboard sem usar a API diretamente | VERIFIED | Rotas POST `/groups/create` e POST `/groups/{id}/edit` em `dashboard.py`; validacao IATA server-side; PRG pattern com 303 redirect; 7 testes cobrindo criacao, edicao, uppercase IATA, erros de validacao |
| 7 | Todas as paginas tem meta viewport e CSS responsivo (media query max-width 768px) | VERIFIED | `base.html` linha 5: `<meta name="viewport" content="width=device-width, initial-scale=1.0">`; linha 14: `@media (max-width: 768px)`; `test_index_has_viewport_meta` e `test_index_has_responsive_css` passando |

**Score:** 7/7 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/services/dashboard_service.py` | Queries de aggregation para dashboard | VERIFIED | 109 linhas; exporta `get_groups_with_summary`, `get_price_history`, `format_price_brl`; queries reais contra SQLAlchemy |
| `tests/test_dashboard_service.py` | Testes RED->GREEN para dashboard service | VERIFIED | 206 linhas; 11 funcoes test_*; cobre happy path, edge cases, cutoff de 14 dias |
| `app/routes/dashboard.py` | Rotas HTML para dashboard | VERIFIED | 241 linhas; exporta `router`; 7 rotas (GET /, GET /groups/create, POST /groups/create, GET /groups/{id}, GET /groups/{id}/edit, POST /groups/{id}/edit, POST /groups/{id}/toggle) |
| `app/templates/base.html` | Template base com nav, viewport, CSS inline | VERIFIED | 30 linhas; contem `meta name="viewport"`, nav com links Grupos e Novo Grupo, `@media (max-width: 768px)` |
| `app/templates/dashboard/index.html` | Lista de grupos com preco e badge | VERIFIED | 55 linhas; `{% extends "base.html" %}`; badges com cores #94a3b8, #eab308, #f97316, #ef4444; formato BRL via `format_price_brl`; links Editar e botao toggle |
| `app/templates/dashboard/detail.html` | Detalhe do grupo com Chart.js | VERIFIED | 59 linhas; contem `chart.js` CDN; canvas com `{{ chart_data \| tojson }}`; mensagem "Nenhum dado coletado ainda" para grupo vazio |
| `app/templates/dashboard/create.html` | Formulario HTML para criar grupo | VERIFIED | 74 linhas; `method="POST"` action="/groups/create"; todos os campos obrigatorios; `text-transform: uppercase` nos inputs IATA |
| `app/templates/dashboard/edit.html` | Formulario HTML pre-preenchido para editar grupo | VERIFIED | 75 linhas; `method="POST"` action="/groups/{{ group.id }}/edit"; values pre-preenchidos com dados do grupo |
| `tests/test_dashboard.py` | Testes de integracao para rotas do dashboard | VERIFIED | 315 linhas; 21 funcoes test_* (12 do Plan 02 + 9 do Plan 03) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app/routes/dashboard.py` | `app/services/dashboard_service.py` | `from app.services.dashboard_service import get_groups_with_summary, get_price_history, format_price_brl` | WIRED | Linha 12-16; todas as 3 funcoes importadas e usadas nas rotas |
| `app/routes/dashboard.py` | `app/templates/` | `Jinja2Templates(directory="app/templates")` | WIRED | Linha 19; templates usados em todas as 7 rotas |
| `main.py` | `app/routes/dashboard.py` | `app.include_router(dashboard_router)` | WIRED | Linha 24-28; router importado e registrado sem prefix; endpoint raiz "/" servido pelo dashboard |
| `app/routes/dashboard.py` | `app/models.py` | `RouteGroup(...)` para criar e editar grupos | WIRED | Linha 135-146 (create), linhas 216-223 (edit); `db.add(group)` e `db.commit()` presentes |
| `app/templates/dashboard/create.html` | `app/routes/dashboard.py` | `form action="/groups/create" method="POST"` | WIRED | Linha 15 do template; corresponde exatamente ao `@router.post("/groups/create")` |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `app/templates/dashboard/index.html` | `groups` | `get_groups_with_summary(db)` -> `db.query(RouteGroup).all()` + subconsultas SQLAlchemy | Sim - queries reais contra banco SQLite | FLOWING |
| `app/templates/dashboard/detail.html` | `chart_data` | `get_price_history(db, group_id)` -> `db.query(FlightSnapshot)` com filtros reais | Sim - queries com GROUP BY e ORDER BY contra banco | FLOWING |
| `app/templates/dashboard/index.html` | `format_price_brl` | Funcao passada no context, nao dado renderizado diretamente | N/A - funcao utilitaria | N/A |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Modulo dashboard_service exporta funcoes esperadas | `python -c "from app.services.dashboard_service import get_groups_with_summary, get_price_history, format_price_brl; print('ok')"` | ok | PASS |
| format_price_brl formata corretamente | `python -c "from app.services.dashboard_service import format_price_brl; print(format_price_brl(3500.0))"` | R$ 3.500,00 | PASS |
| Testes dashboard_service (11 testes) | `python -m pytest tests/test_dashboard_service.py -q` | 11 passed | PASS |
| Testes dashboard routes (21 testes) | `python -m pytest tests/test_dashboard.py -q` | 21 passed | PASS |
| Suite completa | `python -m pytest tests/ -q` | 139 passed, 0 failures | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| ALRT-03 | 05-01, 05-02 | Dashboard web exibe status de todos os grupos ativos e melhor preco atual | SATISFIED | `get_groups_with_summary` retorna cheapest_snapshot; index.html renderiza preco formatado; testes `test_index_shows_cheapest_price` e `test_index_shows_group_names` passando |
| DASH-01 | 05-01, 05-02 | Dashboard lista todos os Grupos de Rota com: melhor preco atual, rota mais barata e indicador visual de sinal ativo | SATISFIED | `index.html` mostra origin -> destination, preco BRL formatado, badges com 4 niveis de urgencia; testes de integracao cobrem todos os casos |
| DASH-02 | 05-01, 05-02 | Clicando em um Grupo de Rota abre historico de precos das ultimas 2 semanas em grafico de linha | SATISFIED | `get_price_history` filtra 14 dias; `detail.html` usa Chart.js com dados via tojson; `test_detail_shows_chart_data` passando |
| DASH-03 | 05-03 | Dashboard tem formulario para criar novo Grupo de Rota | SATISFIED | GET/POST `/groups/create`; `create.html` com todos os campos; validacao IATA; `test_create_group_via_form` e `test_create_group_uppercase_iata` passando |
| DASH-04 | 05-03 | Dashboard permite editar e desativar Grupo de Rota existente | SATISFIED | GET/POST `/groups/{id}/edit` e POST `/groups/{id}/toggle`; edit.html pre-preenchido; `test_edit_group_via_form` e `test_toggle_group_active` passando |
| DASH-05 | 05-02 | Interface funciona em navegador mobile (layout responsivo simples) | SATISFIED (automated) / NEEDS HUMAN (visual) | `base.html` contem meta viewport e `@media (max-width: 768px)`; `test_index_has_viewport_meta` e `test_index_has_responsive_css` passando; rendering visual requer browser |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `app/services/dashboard_service.py` | 36, 64 | `datetime.datetime.utcnow()` deprecated em Python 3.12+ | Info | Deprecation warning nos testes; funcional no Python atual; migracao para `datetime.now(datetime.UTC)` recomendada em versao futura |
| `tests/test_dashboard_service.py` | 109, 139, 190, 191 | `datetime.datetime.utcnow()` nos testes | Info | Mesma deprecation warning; nao afeta corretude dos testes |

Nenhum blocker ou warning encontrado. Os dois items sao meramente informativos (deprecation do Python 3.12+).

### Human Verification Required

#### 1. Layout responsivo em dispositivo mobile

**Test:** Iniciar o servidor com `python main.py`, abrir http://localhost:8000/ no navegador e redimensionar a janela para ~375px de largura.
**Expected:** Cards de grupos se reorganizam em coluna unica; texto e botoes ficam legiveis; navegacao no topo permanece acessivel.
**Why human:** O CSS inline com `@media (max-width: 768px)` e `grid-template-columns: 1fr !important` esta presente no HTML, mas a renderizacao visual do layout responsivo requer um browser real.

#### 2. Grafico Chart.js na pagina de detalhe

**Test:** Clicar em um grupo que tenha snapshots coletados para abrir `/groups/{id}`. Verificar que o grafico de linha e renderizado com eixos e dados visiveis.
**Expected:** Canvas com grafico de linha azul mostrando historico de precos, eixo X com labels no formato "DD/MM HHh", eixo Y com valores de preco.
**Why human:** O CDN do Chart.js e carregado pelo browser; o canvas precisa de JavaScript para ser renderizado; testes de integracao com TestClient nao executam JavaScript.

#### 3. Fluxo completo de criacao de grupo

**Test:** Clicar em "Novo Grupo" no topo, preencher o formulario com origens em minuscula (ex: "gru"), submeter e verificar redirecionamento.
**Expected:** Grupo aparece na lista principal com IATA em maiuscula (GRU); preco mostra "Aguardando coleta" enquanto nenhum snapshot existe.
**Why human:** O redirect 303 e o estado subsequente da pagina requerem browser para verificar experiencia completa do usuario.

#### 4. Botao toggle ativo/inativo

**Test:** Clicar em "Desativar" em um grupo ativo. Verificar indicador visual de grupo inativo.
**Expected:** Card do grupo aparece com `opacity: 0.6` e badge "Inativo" visiveis; botao muda para "Ativar".
**Why human:** A mudanca de estado visual (opacidade, badge Inativo) requer browser para confirmar que o CSS e aplicado corretamente apos o redirect.

### Gaps Summary

Nenhuma gap encontrada. Todos os 7 truths verificados, todos os 9 artifacts presentes e substantivos, todos os 5 key links confirmados como wired, data flow tracado ate queries SQLAlchemy reais, 139 testes passando.

Os itens de verificacao humana sao relacionados exclusivamente a comportamento visual e rendering no browser, que por natureza nao podem ser verificados automaticamente. A implementacao tecnica que sustenta esses comportamentos esta completamente verificada.

---

_Verified: 2026-03-25T20:00:00Z_
_Verifier: Claude (gsd-verifier)_
