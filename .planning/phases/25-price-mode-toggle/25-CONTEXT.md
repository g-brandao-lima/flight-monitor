# Phase 25: Price Mode Toggle - Context

**Gathered:** 2026-04-20
**Status:** Implemented

<domain>
Toggle no dashboard para alternar entre "Por pessoa, ida e volta" (default) e "Total da viagem" (preco × passageiros). Persistido em cookie `price_mode`, Max-Age 1 ano, SameSite Lax.
</domain>

<decisions>
- Segmented control no summary-strip substituindo "Buscas restantes" (que foi para admin)
- POST /preferences/price-mode com form (HTML puro, sem JS)
- Cookie lido em cada GET /
- Valor invalido normaliza para per_person
- Quando pax > 1 no modo total, mostra tambem "preco por pessoa" como sublabel
</decisions>

<code_context>
### Arquivos alterados
- app/routes/dashboard.py: leitura de cookie, rota POST /preferences/price-mode
- app/templates/dashboard/index.html: segmented control + renderizacao condicional do preco
- tests/test_price_mode.py: 4 testes
</code_context>

<specifics>
- Substituiu "Buscas restantes: X/250" no summary-strip (agora visivel apenas em /admin/stats)
- Botoes estilizados com active highlight azul
</specifics>

<deferred>
- Modo "por trecho, por pessoa" (preco/2): nao solicitado
- Aplicar toggle no detail.html (grafico): proximo ciclo
</deferred>
