# Phase 9: Visual Polish - Context

**Gathered:** 2026-03-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Aplicar o UI-SPEC aprovado (08-UI-SPEC.md) nos templates existentes do dashboard. Puramente visual: nao altera funcionalidade, rotas, services ou models. Apenas CSS e HTML nos templates Jinja2.

Requisitos: VIS-01, VIS-02, VIS-03, VIS-04, VIS-05, VIS-06.

</domain>

<decisions>
## Implementation Decisions

### Todas as decisoes visuais estao no UI-SPEC

O UI-SPEC em `.planning/phases/08-dashboard-redesign/08-UI-SPEC.md` e a fonte de verdade para TODAS as decisoes visuais desta phase. Ele define:

- **D-01:** Paleta completa com hex codes e 60/30/10 split
- **D-02:** Tipografia: 4 tamanhos (13/14/20/28px), 2 pesos (400/700), system-ui + monospace pra precos
- **D-03:** Spacing: escala 8-point (4/8/16/24/32/48/64px)
- **D-04:** Cards: borda esquerda 4px colorida, preco monospace 28px bold, hover sombra 0.2s, footer separador #e2e8f0
- **D-05:** Summary bar: fundo #1e293b, metricas 20px bold, labels 13px
- **D-06:** Estado vazio: SVG aviao inline, texto 14px, botao CTA verde #22c55e com min-height 40px
- **D-07:** Inativos: opacidade 0.6, badge "Inativo"
- **D-08:** Cores semanticas: #22c55e LOW, #f59e0b MEDIUM, #ef4444 HIGH, #94a3b8 sem dados

### Abordagem de implementacao
- **D-09:** Reescrever CSS inline nos templates existentes (index.html, detail.html, base.html). Nao criar arquivo CSS externo.
- **D-10:** Nao alterar nenhum arquivo Python (routes, services, models). Apenas templates HTML.
- **D-11:** Manter todos os testes existentes passando (zero regressao funcional).

### Claude's Discretion
- Ordem exata de aplicacao das mudancas
- Detalhes de implementacao CSS (gradientes sutis, border-radius exatos)
- SVG do aviao (design simples, inline)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### UI-SPEC (FONTE DE VERDADE)
- `.planning/phases/08-dashboard-redesign/08-UI-SPEC.md` - Contrato visual completo: cores, tipografia, spacing, cards, summary bar, estado vazio, copywriting

### Templates atuais (a ser atualizados)
- `app/templates/base.html` - template base com nav e flash messages
- `app/templates/dashboard/index.html` - pagina principal com cards e summary bar
- `app/templates/dashboard/detail.html` - pagina de detalhe com grafico Chart.js
- `app/templates/dashboard/create.html` - formulario criar grupo
- `app/templates/dashboard/edit.html` - formulario editar grupo
- `app/templates/error.html` - pagina de erro

### Requirements
- `.planning/REQUIREMENTS.md` - VIS-01 a VIS-06

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Todos os templates ja existem e funcionam. A mudanca e puramente CSS.
- Flash messages ja implementadas no base.html (Phase 6)
- Chart.js ja carregado no detail.html
- format_price_brl e format_date_br ja passados como contexto

### Established Patterns
- CSS inline em tags style nos templates
- Jinja2 template inheritance (base.html -> pages)
- Classes CSS ja existentes nos cards (card-border-low, etc)

### Integration Points
- Nenhum. Apenas templates HTML/CSS. Zero mudancas em Python.

</code_context>

<specifics>
## Specific Ideas

- Inspiracao: Hopper (cores e badges), Linear (minimalismo e whitespace), Going.com (precos grandes)
- Preco e o rei: maior elemento no card, fonte monospace pra alinhar digitos
- Menos e mais: remover sombras pesadas, usar bordas sutis e whitespace generoso

</specifics>

<deferred>
## Deferred Ideas

None - discussion stayed within phase scope.

</deferred>

---

*Phase: 09-visual-polish*
*Context gathered: 2026-03-26 (auto mode)*
