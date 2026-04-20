# Phase 16: Passengers Fix - Context

**Gathered:** 2026-04-20
**Status:** Implemented
**Mode:** Auto-generated (autonomous night run)

<domain>
## Phase Boundary

Corrigir bug onde `group.passengers` configurado pelo usuario era ignorado nas buscas de voo. fast-flights usava `Passengers(adults=1)` hardcoded e SerpAPI nao recebia o parametro.

</domain>

<decisions>
## Implementation Decisions

- `search_flights()` agora aceita `adults: int = 1` e propaga para ambas fontes
- `SerpApiClient.search_flights_with_insights` aceita `adults` e envia como `adults` na query string
- `polling_service` passa `group.passengers or 1`
- Clamp minimo de 1 (nao permitir 0 ou negativos)

</decisions>

<code_context>
## Existing Code Insights

### Integration Points
- app/services/flight_search.py
- app/services/serpapi_client.py
- app/services/polling_service.py (caller)
- tests/test_serpapi_client.py (2 testes novos: passes_adults_param, clamped_to_one)

</code_context>

<specifics>
## Specific Ideas

- SerpAPI param name: `adults` (documentado no SerpAPI Google Flights API).
- fast-flights: `Passengers(adults=N)` suporta adultos, criancas, bebes. Esta fase cobre apenas adultos.

</specifics>

<deferred>
## Deferred Ideas

- Criancas/bebes no grupo (multi-idade): fora do escopo, nenhum usuario pediu
- Classe de cabine diferente de economy: fora do escopo

</deferred>
