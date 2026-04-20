# Phase 20: Flight Search Cache - Context

**Gathered:** 2026-04-20
**Status:** Implemented

<domain>
Cache in-memory de resultados de search_flights com TTL 30 min. Quando multiplos grupos monitoram a mesma (origin, dest, date, pax), apenas o primeiro faz chamada real a API; os demais recebem do cache. Reduz pressao sobre quota SerpAPI free tier (250/mes) e acelera ciclo de polling.
</domain>

<decisions>
- Cache dict thread-safe em app/services/flight_cache.py
- Key: (origin, destination, departure, return, max_stops, adults)
- TTL default 30 min (cobre 1 ciclo polling inteiro)
- Polling consulta cache antes de chamar search_flights para saber se sera hit; evita incrementar quota em cache hit
- search_flights_ex() retorna 4-tupla (flights, insights, source, was_cache_hit) como API alternativa
- search_flights() mantem contrato 3-tupla (compat com testes existentes)
- conftest.py autouse fixture limpa cache entre testes (evita cross-test contamination)
</decisions>

<code_context>
### Arquivos novos
- app/services/flight_cache.py
- tests/test_flight_cache.py (6 testes)

### Arquivos alterados
- app/services/flight_search.py: search_flights_ex + integracao cache
- app/services/polling_service.py: consulta flight_cache para saber was_cache_hit antes de incrementar quota
- tests/conftest.py: _reset_flight_cache autouse fixture
</code_context>

<specifics>
- Nao persiste entre restarts (aceitavel, cache esquenta em 1 ciclo)
- Para escalar alem de 1 worker, migrar para Redis (compartilhado)
</specifics>

<deferred>
- Redis backend: quando multi-worker
- Metricas de hit rate: quando tiver observability (Phase 21.5 bloqueada)
- Invalidacao por grupo: hoje nao necessario (TTL 30 min resolve)
</deferred>
