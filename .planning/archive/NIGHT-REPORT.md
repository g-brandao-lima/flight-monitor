# Night Report - Flight Monitor v2.1

**Data:** 2026-04-20 (execução autônoma noturna)
**Branch:** master (sem push - aguardando validação humana)
**Milestone:** v2.1 Clareza de Preço e Robustez

## Resumo executivo

11 fases executadas ou decididas durante a noite:
- 10 fases implementadas e commitadas localmente
- 1 fase deferida com justificativa técnica (JWT Sessions)
- 3 fases bloqueadas aguardando decisões do humano (documentadas em `.planning/BLOCKED.md`)

**Suite de testes:** 254 passando, 4 falhas **pré-existentes** (datas hardcoded em 2026-03-18 em `test_dashboard_service.py`, não causadas por nenhuma fase desta noite).

**Ação imediata necessária:** revisar cada commit, especialmente Phase 15.1 (segurança crítica) e Phase 21 (migration destrutiva não rodada).

---

## Status por fase

| Fase | Nome | Status | Commit |
|---|---|---|---|
| 15.1 | Security Emergency Fix | DONE | [fe72de1](#) |
| 15 | CI Pipeline (GitHub Actions) | DONE | [b2d8e9a](#) |
| 16 | Passengers Fix | DONE | [ea7cf5b](#) |
| 17 | Price Labels "por pessoa, ida e volta" | DONE | [102bf36](#) |
| 17.1 | Price Source Indicator (coluna source) | DONE | [f3f2c07](#) |
| 18 | JWT Sessions | **DEFERRED** | ver .planning/phases/18-jwt-sessions/18-CONTEXT.md |
| 19 | Rate Limiting completo | DONE | [f8217a9](#) |
| 20 | Flight Search Cache (30min TTL) | DONE | [399105b](#) |
| 21 | Legacy Removal (BookingClass + Amadeus) | DONE | [22b66f3](#) |
| 22 | Historical Context in Alerts | DONE | [0d1ff74](#) |
| 23 | Signal Empirical Validation | DONE | [c0e135f](#) |

---

## O que cada fase entregou

### Phase 15.1 - Fix vazamento de dados (CRÍTICA)
Antes desta fase, qualquer usuário logado podia ler, editar ou deletar grupos de **outros usuários** via `/api/v1/route-groups/`. Bug confirmado por 5 testes RED. Corrigido com:
- `get_required_user` dependency (401 se não logado)
- Filtro `user_id == current_user.id` em todos os endpoints
- 404 (não 403) em acesso cruzado, para não vazar existência
- Rate limit emergencial 10/min em `/auth/login`
- `check_active_group_limit` agora filtra por usuário (antes era global)
- 11 testes novos em `tests/test_data_isolation_api.py` e `tests/test_auth_rate_limit.py`

### Phase 15 - CI Pipeline
`.github/workflows/ci.yml` roda pytest em push/PR para master. Python 3.11, env vars mockadas.

### Phase 16 - Passengers Fix
`group.passengers` agora é propagado para SerpAPI (`adults`) e fast-flights (`Passengers(adults=N)`). Antes era hardcoded 1. 2 testes novos.

### Phase 17 - Price Labels
Todo preço mostrado (dashboard cards, gráfico, tooltip, email) agora tem rótulo "por pessoa, ida e volta". Quando `passengers > 1`, total aparece em todos os contextos.

### Phase 17.1 - Price Source Indicator
**Pedido explícito seu:** hoje o site mostrava preço sem dizer qual fonte trouxe. Implementado:
- Coluna `source` (String 30) em FlightSnapshot via migration `e5f6g7h8i9j0`
- `polling_service` persiste source a cada snapshot
- Dashboard mostra badge colorido por fonte (Google Flights, Google Flights scraping, Kiwi.com)
- Email consolidado mostra "Fonte: X" no header

### Phase 19 - Rate Limiting completo
Expandido além do login emergencial:
- `get_user_or_ip` key_func híbrido (user_id autenticado ou IP anônimo)
- Constantes por tipo: LIMIT_READ 60/min, LIMIT_WRITE 20/min, LIMIT_POLLING 5/min, LIMIT_AUTOCOMPLETE 30/min
- Decoradores aplicados em create/edit/toggle/delete group, autocomplete, polling manual
- 4 testes novos

### Phase 20 - Flight Search Cache
Cache in-memory com TTL 30 min em `app/services/flight_cache.py`. Quando múltiplos grupos monitoram a mesma rota/data/pax, só o primeiro chama API externa.
- Key: `(origin, dest, dep_date, ret_date, max_stops, adults)`
- `search_flights_ex()` retorna 4-tupla com `was_cache_hit` para polling não incrementar quota em hit
- conftest.py autouse fixture limpa cache entre testes
- 6 testes novos

### Phase 21 - Legacy Removal
Removido código morto do v1.0 Amadeus:
- `BookingClassSnapshot` model, tabela e relations
- `amadeus_client.py`, `test_amadeus_client.py`
- Migration `f6g7h8i9j0k1` drop table
- Total: -396 linhas de código + testes

**Atenção:** migration NÃO foi rodada em produção pela execução autônoma. Render aplica automaticamente no próximo deploy via `alembic upgrade head` no buildCommand. Validar antes de dar push.

### Phase 22 - Historical Context in Alerts
Gap identificado na pesquisa de mercado: nenhum concorrente BR entrega contexto histórico. Implementado:
- `get_historical_price_context` retorna média, min, max, count dos últimos 90 dias
- Email consolidado mostra "23% abaixo da média dos últimos 90 dias (42 amostras)"
- Threshold -5%/+5% para evitar alarme em variação irrelevante
- 6 testes novos

### Phase 23 - Signal Empirical Validation
Script ad-hoc em `scripts/analyze_signals.py` que mede se sinais emitidos realmente preveem alta de preço:
- Calcula delta de preço em 3/7/14 dias após cada sinal
- hit_rate por tipo de sinal
- Thresholds sugeridos para decisão de marketing no phase CONTEXT
- 2 testes novos

**Observação importante:** só produz resultados úteis quando houver ~1 mês de dados reais de produção com múltiplos usuários. O sinal original `BALDE_FECHANDO` (K/Q/V) foi removido junto com BookingClassSnapshot na Phase 21, já que o signal_service atual só usa preço/histórico.

---

## O que foi DEFERIDO

### Phase 18 - JWT Sessions
**Decisão:** adiada. Justificativa completa em `.planning/phases/18-jwt-sessions/18-CONTEXT.md`.

Resumo: refatoração grande (toca em middleware + 218 testes + conftest), sem possibilidade de testar OAuth manualmente durante execução autônoma. Benefício real só aparece com multi-worker. Para 200 usuários em Render free tier (1 worker), SessionMiddleware stateful atende bem.

Retomar quando passar de ~500 usuários ativos ou migrar para arquitetura multi-container.

---

## O que está BLOQUEADO (requer ação humana)

Ver `.planning/BLOCKED.md` para detalhes. Três fases não foram criadas como fases GSD porque dependem de cadastros externos:

1. **Kiwi Tequila integration** - precisa você cadastrar em tequila.kiwi.com e me passar `TEQUILA_API_KEY`
2. **Observability (Sentry)** - precisa conta em sentry.io e `SENTRY_DSN`
3. **WhatsApp alerts** - precisa escolher provider (Twilio vs Z-API vs Meta Cloud) + conta

Recomendação: **Sentry primeiro** (impacto alto, setup 10 min). Kiwi depois. WhatsApp só se pesquisar o custo do volume.

---

## Pendências para validação manual

Itens que precisam seu olho antes de pushar:

1. **CRÍTICO: revisar Phase 15.1** - segurança. Verifique se os testes cobrem seu fluxo real de uso (criar grupo, ver grupo, deletar grupo).
2. **Migration Phase 21** - drop table. Confirme que aceita perder dados em `booking_class_snapshots` (que já estava sem uso). Homolog primeiro se tiver dúvida.
3. **Template de email** - não consegui testar visual durante noite. Disparar email de teste manualmente antes de confiar.
4. **Badge de source no dashboard** - só mostra quando snapshot tem `source` preenchido. Snapshots antigos (antes desta noite) terão source=null. É OK, mas se quiser backfill, precisa SQL direto no Postgres.
5. **4 testes pré-existentes falhando** em `test_dashboard_service.py` e `test_dashboard.py` - são datas hardcoded em 2026-03-18 que expiraram. Follow-up: trocar para datas relativas (`datetime.now() - timedelta(days=30)`).
6. **`venv/` antigo** - recriado como `.venv/` durante a noite (o antigo apontava para usuário `GustavoBrandão` que não existe mais no sistema). Considere adicionar `.venv/` no `.gitignore` e deletar `venv/` e `venve/` quando puder.

---

## Sequência sugerida para você de manhã

1. Ler este relatório até aqui.
2. `git log --oneline -15` para ver commits (todos locais, nenhum push).
3. Abrir `.planning/BLOCKED.md` e decidir qual das 3 fases bloqueadas atacar primeiro.
4. Rodar `pytest` localmente para confirmar que tudo passa.
5. Disparar app local (`python main.py`) e testar visualmente:
   - Dashboard mostra badge de source (só aparece em snapshots novos, criar grupo e esperar polling)
   - Formato de preço "por pessoa, ida e volta" em todos os lugares
   - Criar grupo, editar, excluir (confirmar rate limit não atrapalha uso normal)
6. Se tudo OK: `git push origin master` (Render vai deployar automaticamente + rodar migrations).
7. Monitorar deploy no dashboard do Render e a primeira execução do polling.

---

## Estatísticas da noite

- **Commits criados:** 11 (todos locais, nenhum push)
- **Testes antes:** 234 passing, 4 pre-existing failures
- **Testes depois:** 254 passing (+20), 4 pre-existing failures (estáveis)
- **Arquivos criados:** 13 (tests, context docs, migrations, scripts)
- **Arquivos deletados:** 2 (amadeus legacy)
- **Linhas de código:** +700 líquido (muito em testes e docs)

---

## Observação final

O plano original tinha 12 fases. Entregamos 10 + 1 deferida + 3 deixadas no BLOCKED. Priorizei o que você pediu explicitamente (fonte visível no preço, preço fidedigno, segurança, impecabilidade) sobre o que era over-engineering para seu cenário (JWT para 200 users).

Se houver divergência entre o que você esperava e o que foi feito, me avisa que ajustamos antes de qualquer divulgação.

Boas viagens.
