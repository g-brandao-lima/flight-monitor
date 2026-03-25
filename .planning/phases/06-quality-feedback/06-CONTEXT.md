# Phase 6: Quality & Feedback - Context

**Gathered:** 2026-03-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Corrigir bug de snapshots duplicados no polling, adicionar mensagens de feedback apos acoes do usuario (criar/editar/desativar grupo), e criar pagina de erro amigavel. Nao envolve mudancas visuais no layout (Phase 8).

Requisitos: FIX-01, UX-01, UX-02.

</domain>

<decisions>
## Implementation Decisions

### Deduplicacao de snapshots (FIX-01)
- **D-01:** Deduplicar no polling_service antes de chamar save_flight_snapshot. Verificar se ja existe snapshot com mesma rota+data+preco+airline no ciclo atual antes de salvar.
- **D-02:** Usar collected_at do ciclo como referencia para agrupar snapshots do mesmo ciclo (janela de 1 hora).

### Mensagens de feedback (UX-01)
- **D-03:** Flash messages via query parameter na URL de redirect (ex: `/?msg=grupo_criado`). O template index.html renderiza a mensagem baseado no parametro.
- **D-04:** Mensagens: "Grupo criado com sucesso!", "Grupo atualizado com sucesso!", "Grupo ativado/desativado com sucesso!"
- **D-05:** Mensagem aparece no topo da pagina com fundo verde, desaparece apos 5 segundos (CSS animation, sem JS complexo).

### Pagina de erro (UX-02)
- **D-06:** Pagina HTML com template error.html que mostra mensagem amigavel, botao "Voltar ao inicio" e nao expoe detalhes tecnicos.
- **D-07:** Registrar exception handler global no FastAPI para capturar erros 500.
- **D-08:** Manter pagina 404 simples para grupos nao encontrados (ja existe inline no dashboard.py).

### Claude's Discretion
- Texto exato das mensagens de feedback
- Estilo visual da pagina de erro
- Estrategia exata de dedup (hash vs comparacao de campos)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Polling (bug fix)
- `app/services/polling_service.py` - _process_flight e _poll_group (onde snapshots duplicados sao criados)
- `app/services/snapshot_service.py` - save_flight_snapshot (persiste snapshot)

### Dashboard (feedback messages)
- `app/routes/dashboard.py` - create_group_form, edit_group_form, toggle_group (redirects que precisam de msg)
- `app/templates/base.html` - template base onde a mensagem de feedback sera renderizada
- `app/templates/dashboard/index.html` - pagina que recebe o redirect

### Error handling
- `main.py` - FastAPI app onde o exception handler global sera registrado

### Requirements
- `.planning/REQUIREMENTS.md` - FIX-01, UX-01, UX-02

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/templates/base.html`: template base com nav e estilos inline - mensagem de feedback pode ser adicionada no bloco content
- PRG pattern ja implementado: create/edit/toggle fazem redirect 303 para "/" - basta adicionar query param

### Established Patterns
- RedirectResponse(url="/", status_code=303) nos forms
- HTMLResponse para erros inline (404 em dashboard.py)
- CSS inline em tags style nos templates

### Integration Points
- `main.py`: registrar exception_handler para HTTPException e Exception generica
- `app/templates/base.html`: bloco para mensagem de feedback antes do content
- `app/routes/dashboard.py`: adicionar ?msg= nos redirects

</code_context>

<specifics>
## Specific Ideas

- Mensagem de feedback verde com animacao fade-out via CSS (sem JS)
- Pagina de erro clean, sem stack trace, com tom amigavel em portugues
- Dedup deve comparar rota+data+preco+airline para nao salvar o mesmo voo 2x

</specifics>

<deferred>
## Deferred Ideas

None - discussion stayed within phase scope.

</deferred>

---

*Phase: 06-quality-feedback*
*Context gathered: 2026-03-25 (auto mode)*
