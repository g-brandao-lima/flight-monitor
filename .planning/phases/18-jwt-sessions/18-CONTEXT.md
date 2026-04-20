# Phase 18: JWT Sessions - Context

**Gathered:** 2026-04-20
**Status:** DEFERRED - decisao da noite autonoma

<domain>
Migrar sessoes stateful (SessionMiddleware com user_id) para JWT stateless em cookie httponly. Goal declarado: "escalabilidade horizontal sem perder fluxo OAuth".
</domain>

<decisions>
## Decisao: DEFERRED

Refatoracao adiada apos analise custo-beneficio no contexto real.

**Por que NAO fazer agora:**
- 200 usuarios alvo em 6 meses (cenario real, nao teorico)
- Render free tier roda 1 worker gunicorn: nao tem multiplos processos compartilhando sessao
- SessionMiddleware cabe em 1 worker sem problema
- Refatorar auth toca em middleware + 218+ testes existentes + conftest fixture de cookie
- Alto risco de quebra sem possibilidade de teste manual durante execucao autonoma
- Beneficio real de JWT so aparece em horizontal scaling (multiplos workers ou multiplos containers)

**Quando retomar:**
- Quando passar de ~500 usuarios ativos E for necessario aumentar para 2+ workers
- Ou quando deploy for migrado para arquitetura com multiplos containers

**Alternativa para agora:** continuar com session cookie stateful ja implementado e testado.
</decisions>

<code_context>
Nenhum codigo alterado.
</code_context>

<specifics>
Se o usuario validar que quer JWT mesmo assim, retomar esta fase em sessao interativa (nao autonoma) para poder testar OAuth flow manualmente no browser.
</specifics>

<deferred>
Ver decisao acima.
</deferred>
