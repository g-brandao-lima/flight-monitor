# Phase 24: Admin Stats Panel - Context

**Gathered:** 2026-04-20
**Status:** Implemented

<domain>
Painel administrativo em /admin/stats visivel apenas para o email configurado em ADMIN_EMAIL. Mostra quota SerpAPI com data exata de reset, distribuicao de fontes nos ultimos 7 dias, estado do cache in-memory, e link para o dashboard Sentry.
</domain>

<decisions>
- 404 para nao-admin (nao 403) conforme recomendacao do agente UX para evitar enumeracao
- ADMIN_EMAIL como env var (case insensitive, trim)
- Helper is_admin(user) disponivel em todos os templates via app/templates_config.py
- Icone engrenagem no header aparece apenas quando is_admin(user) e True
- 4 blocos no painel: Quota, Fontes, Cache, Observabilidade (link Sentry)
- Reset date calculado como primeiro dia do mes UTC seguinte (matching do quota_service atual)
</decisions>

<code_context>
### Arquivos novos
- app/services/admin_stats_service.py
- app/routes/admin.py
- app/templates/admin/stats.html
- app/templates_config.py (centralizador Jinja2 com globals)
- tests/test_admin_stats.py (6 testes)

### Arquivos alterados
- app/config.py: campo admin_email
- app/auth/dependencies.py: get_admin_user + is_admin
- app/templates/base.html: icone condicional engrenagem
- app/routes/dashboard.py, main.py: usam get_templates()
- .env, .env.example, render.yaml: var ADMIN_EMAIL
</code_context>

<specifics>
- Proximo reset SerpAPI e sempre primeiro dia do mes seguinte (calendario UTC)
- Cache in-memory reseta em cada restart (aceitavel)
</specifics>

<deferred>
- Last errors: adiar porque Sentry ja cobre. Link direto para dashboard Sentry basta.
- Paginacao de logs: desnecessaria para 200 users
</deferred>
