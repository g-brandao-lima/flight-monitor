# Phase 26: Factual Email Subject - Context

**Gathered:** 2026-04-20
**Status:** Implemented

<domain>
Subject line do email consolidado passa a ter dados factuais (delta vs media, preco absoluto, rota) em vez de "Flight Monitor: Nome - preco (melhor preco)". Aumenta taxa de abertura segundo pesquisa de growth.
</domain>

<decisions>
- Thresholds de linguagem:
  - <= -10%: "ROUTE caiu X% hoje: PRECO (media 90d AVG)"
  - <= -5%: "ROUTE X% abaixo da media: PRECO (media 90d AVG)"
  - >= +10%: "ROUTE subiu X%: PRECO (media 90d AVG)"
  - caso contrario: "ROUTE em PRECO (media 90d AVG)"
- Sem contexto historico (amostras < 10): fallback "Flight Monitor: NOME em PRECO"
- Guard contra avg <= 0: fallback neutro
- Codigo IATA da rota no inicio (GRU-LIS, GIG-CDG): preview mobile mostra o essencial
</decisions>

<code_context>
### Arquivos alterados
- app/services/alert_service.py: funcao _build_subject, chamada no compose_consolidated_email
- tests/test_subject_factual.py: 6 testes cobrindo todos os thresholds
- tests/test_alert_service.py: teste antigo ajustado para novo formato
</code_context>

<specifics>
- format_price_brl reutilizado para consistencia
- Rota e avg sempre no formato BRL
</specifics>

<deferred>
- A/B test de subject: requer base de usuarios maior
- Subject em ingles para usuarios nao-BR: fora de escopo
</deferred>
