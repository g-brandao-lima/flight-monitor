# Phase 27: Sparkline + Price Badge - Context

**Gathered:** 2026-04-20
**Status:** Implemented

<domain>
Melhorar feedback visual do card: sparkline de 30 dias (antes 7) + badge contextual ("Menor preço em 30 dias", "X% abaixo da média 30d", "X% acima da média 30d") baseado em analise do historico.
</domain>

<decisions>
- Janela sparkline: 30 dias (antes 7). Mais dados = mais signal.
- Agrupamento por DIA (minimo do dia) em vez de hora. Mais estavel para sparkline.
- Badge 'good' quando: preco <= min_30d × 1.01 OU preco <= avg_30d × 0.95
- Badge 'bad' quando: preco >= avg_30d × 1.10
- Minimo de 3 dias de dados para gerar badge (evita ruido)
- Estilo pill com fundo verde/vermelho translucido
</decisions>

<code_context>
### Arquivos alterados
- app/services/dashboard_service.py: extende sparkline para 30d + price_badge
- app/templates/dashboard/index.html: renderiza price_badge acima da source_badge
- tests/test_price_badge.py: 4 testes cobrindo os 3 cenarios + ausencia
</code_context>

<specifics>
- price_badge e dict {label, tone} ou None
- Badges factuais, nunca inventados (sempre baseados em dados)
</specifics>

<deferred>
- Migrar sparkline para SVG elegante: custo alto, sparkline por divs ja funciona
- Badge comparando cost vs melhor preco historico absoluto: duplicacao com best_ever
</deferred>
