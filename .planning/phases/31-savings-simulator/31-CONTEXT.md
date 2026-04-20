# Phase 31: Savings Simulator - Context

**Gathered:** 2026-04-20
**Status:** Implemented

<domain>
No card do grupo, mostra quanto o usuario ja economizou (ou teria economizado comprando ao criar). Aplica loss aversion de forma etica porque usa dados reais: snapshot inicial (primeiras 48h apos criacao do grupo) vs snapshot atual.
</domain>

<decisions>
- Janela inicial: 48h apos group.created_at, pega menor preco
- Direction 'saved' se preco caiu, 'lost' se subiu, 'even' se diferenca < 1%
- Exibicao compacta no card (11px), sub-label apos price-badge
- Cores: verde para saved, vermelho para lost, cinza para even
- Requer pelo menos 1 snapshot nas primeiras 48h
- Conta days_monitoring a partir do created_at para contexto
</decisions>

<code_context>
### Arquivos alterados
- app/services/dashboard_service.py: _compute_savings_since_creation + chave 'savings' no dict
- app/templates/dashboard/index.html: exibicao condicional no card
- tests/test_savings_simulator.py: 4 testes (saved, lost, even, none)
</code_context>

<specifics>
- Loss aversion etico: so mostra "teria economizado" se o preco subiu de verdade (dado real)
- Sem especulacao ou cenarios hipoteticos inventados
</specifics>

<deferred>
- Card de "economia total acumulada" no summary-strip (soma de todos os grupos): considerar apos MVP
- Exportar relatorio com historico de decisoes: futuro
</deferred>
