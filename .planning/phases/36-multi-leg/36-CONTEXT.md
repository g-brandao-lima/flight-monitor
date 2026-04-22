# Phase 36: Multi-Leg Trip Builder - Context

**Gathered:** 2026-04-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Adicionar suporte a roteiros encadeados (N trechos sequenciais, cada trecho com janela de datas e stay min/max) ao modelo de monitoramento da Orbita. Sinal de compra aplicado sobre o preco total do encadeamento, reusando `price_prediction_service` (Phase 34).

Entregaveis em escopo:
- Modelo `RouteGroupLeg` + flag `mode="multi_leg"` em `RouteGroup`
- Migration Alembic
- Validacao temporal do encadeamento
- Busca de precos multi-trecho + snapshot com breakdown em `details JSON`
- UI de criacao/edicao/listagem/detalhe com modo multi
- Email consolidado adaptado
- Dashboard card com layout multi

Fora de escopo:
- Affiliate multi-city (sem monetizacao agora)
- Open-jaw intencional
- Otimizacao automatica de hub
- Multi-city search em tempo real via APIs pagas

</domain>

<decisions>
## Implementation Decisions

### Modelo de dados (locked pelo SPEC)
- **D-01:** `RouteGroup.mode` ganha valor `"multi_leg"`. Quando ativo, `origins/destinations/travel_start/travel_end` sao ignorados e `legs[]` e a verdade.
- **D-02:** Nova tabela `RouteGroupLeg` 1:N: `id, route_group_id FK, order, origin, destination, window_start, window_end, min_stay_days, max_stay_days (null=sem teto), max_stops`. Constraint de unicidade `(route_group_id, order)`.
- **D-03:** Snapshot multi usa `FlightSnapshot` existente com `airline="MULTI"` + coluna nova `details: JSON` contendo `{total_price, legs: [{order, origin, destination, date, price, airline}, ...]}`. Evita tabela separada e simplifica queries.

### Validacao temporal
- **D-04:** Regra: `leg[N+1].window_start >= leg[N].window_end + leg[N].min_stay_days` no momento da criacao do grupo. No momento da busca, cada combinacao de datas respeita `actual_departure[N+1] >= actual_return[N] + min_stay` (e <= + max_stay se definido).
- **D-05:** Minimo 2 trechos (com 1 e modo normal ja cobre). Maximo **5 trechos** por roteiro.
- **D-06:** Minimo 1 dia de stay (conexao com 0 dias fora de escopo). Max_stay opcional (null = sem teto).

### UI - form de criacao
- **D-07:** Toggle no topo de `/groups/create`: `Roundtrip simples` (default) / `Multi-trecho`. Nao muda nada pra modo normal.
- **D-08:** Construtor dinamico (JS vanilla, sem framework) com botoes `+ Adicionar trecho` / `- Remover`.
- **D-09:** **Janela do trecho N+1 e auto-calculada** a partir de `leg[N].window_end + leg[N].min_stay_days` ate `+ max_stay_days`. Campo vem preenchido mas permanece editavel (override manual). Zero friccao por padrao, flexibilidade quando preciso.
- **D-10:** **Passageiros: valor unico global no grupo** (campo `passengers` existente em `RouteGroup`). Todos os trechos herdam o mesmo N. Variacao por trecho ("vou com 2 e volto sozinho") fica pra fase futura se houver demanda real.

### Busca de preco (polling)
- **D-11:** `polling_service` ramifica em `if group.mode == "multi_leg"` e chama `multi_leg_service.search_multi_leg_prices(db, group)`.
- **D-12:** Cada trecho consulta `route_cache` primeiro. **Se leg nao tem cache (rota fora das 28 seed), cai pra SerpAPI on-demand e popula `route_cache`** pra proximos ciclos. Custo: queima quota mensal (250/mes) na criacao de grupo e no primeiro polling. Logar em `cache_lookup_log`.
- **D-13:** Algoritmo de combinacao: produto cartesiano de datas candidatas, filtrado por validade temporal, escolhe a combinacao de menor preco total. Registra 1 FlightSnapshot com `airline="MULTI"` e `details` JSON.

### Sinal e recomendacao
- **D-14:** `signal_service` aplica logica existente sobre `total_price` do encadeamento (mediana/desvio 90d sobre snapshots multi do mesmo grupo).
- **D-15:** `price_prediction_service.predict_action` recebe `total_price`, mediana dos totais, stddev dos totais, `days_to_departure` do primeiro trecho. Reusa engine da Phase 34 sem modificacao.

### UI - card dashboard e detalhe
- **D-16:** Card multi mostra cadeia `GRU -> FCO -> MAD -> GRU`, badge `MULTI` (mono, cyan), label `Preco total do roteiro`, recomendacao igual grupos normais.
- **D-17:** **Comparadores externos**: no modo multi, cada trecho tem seu proprio cluster `Comparar precos em` com os 4 botoes (Google Flights, Decolar, Skyscanner, Kayak) apontando pra busca individual daquele trecho. URL multi-city consolidada fica pra fase futura (formato varia demais entre providers). Mais simples e previsivel pro usuario.
- **D-18:** Pagina de detalhe mostra breakdown: cada trecho com seu preco atual, data escolhida pela busca, e total embaixo. **Mostra apenas a combinacao mais barata** (top 3 combinacoes fica pra fase futura se houver demanda — nao foi pedido agora).

### Email
- **D-19:** Email consolidado multi mostra cadeia `GRU -> FCO -> MAD -> GRU` no header, total em destaque, tabela com breakdown por trecho (origem, destino, data, preco). Recomendacao no topo (Phase 34), cluster `Comparar precos em` por trecho.
- **D-20:** Subject: `Orbita multi: [Nome] R$ X,XX (N trechos)`.

### Claude's Discretion
- UI exata do construtor de trechos (ordem de campos, cores de separadores, animacao ao adicionar trecho) — seguir tokens existentes (`--bg-2`, `--border-2`, `--brand-500`)
- Algoritmo exato de produto cartesiano (limites de datas amostradas por trecho) — planner decide baseado em performance; cap sugerido: 7 candidatos de data por trecho
- Serializacao Pydantic dos schemas `LegCreate`, `LegOut`, `RouteGroupMultiCreate`
- Nome da migration Alembic
- Texto exato de mensagens de erro de validacao temporal

### Folded Todos
Nenhum todo pendente foi identificado como relevante pra Phase 36 (skip silencioso).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase spec
- `.planning/phases/36-multi-leg/36-SPEC.md` — Spec completa original com modelagem, algoritmo, UI mockup, copy pt-BR
- `.planning/ROADMAP.md` — Phase 36 entry + MULTI-01..04 requirements
- `.planning/REQUIREMENTS.md` — MULTI-01..04 (grupo multi-trecho, validacao temporal, busca + sinal sobre total)

### Fase dependencia direta
- `.planning/phases/34-price-prediction/34-SPEC.md` — Phase 34 (recomendacao COMPRE/AGUARDE/MONITORAR). Engine `predict_action` sera reusada sobre preco total.
- `app/services/price_prediction_service.py` — Engine que Phase 36 reusa

### Fases relacionadas (patterns)
- `.planning/phases/32-cache-layer/` — Travelpayouts cache + `route_cache` tabela (dependencia infra)
- `.planning/phases/20-serpapi-cache/20-CONTEXT.md` — SerpAPI fallback + quota

### Codigo base afetado
- `app/models.py` — `RouteGroup`, `FlightSnapshot` (recebem campos novos)
- `app/services/polling_service.py` — branch multi
- `app/services/flight_search.py` — reutilizado por trecho
- `app/services/route_cache_service.py` — cache hit/miss por trecho
- `app/services/signal_service.py` — sinal sobre total
- `app/services/dashboard_service.py` — `get_groups_with_summary` retorna legs+total
- `app/services/alert_service.py` — email multi
- `app/routes/route_groups.py` — POST aceita `legs[]`
- `app/templates/dashboard/create.html`, `edit.html`, `index.html`, `detail.html` — UI
- `alembic/versions/` — 1 migration nova

### Convencoes
- `CLAUDE.md` (raiz) — SDD+TDD, pt-BR acentuado, sem emoji, commits atomicos, SSR puro sem JS framework, travessao proibido

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`price_prediction_service.predict_action`** (Phase 34): aceita `current_price, median, stddev, days_to_departure, snapshot_count, departure_date` — funciona identicamente sobre preco total multi
- **`booking_urls`** (`dashboard_service.py`): gera Google Flights (#flt=), Decolar, Skyscanner, Kayak por trecho. Reusar direto por leg no template.
- **`FlightSnapshot`**: modelo existente. Ganha so coluna `details: JSON` (nullable). Campos `departure_date`/`return_date` do snapshot representam o primeiro e ultimo voo do encadeamento (pra ordenacao e queries basicas).
- **`route_cache`**: cache Travelpayouts funciona por `(origin, destination, month)`. Cada leg consulta independente.
- **`quota_service`**: registra uso SerpAPI, ja pronto pra fallback on-demand.
- **Templates Jinja2 + tokens CSS**: paleta Orbita definida em `base.html` (`--brand-500`, `--accent-500`, `--success-bg`, `--warning-bg`, `--bg-2`, etc).
- **Form de grupo existente** (`create.html`): serve como base. Gate no comeco por radio toggle ativa divs escondidas.

### Established Patterns
- **CRUD de grupos**: `app/routes/route_groups.py` com FastAPI form handlers (nao JSON API puro — e form POST server-side). Phase 36 segue mesmo padrao.
- **Validacao**: Pydantic schemas em `app/schemas.py`. Phase 36 adiciona `LegCreate`, `LegOut`, `RouteGroupMultiCreate`.
- **Testes**: SQLite in-memory, fixtures em `tests/conftest.py`, padrao AAA, `.venv/Scripts/python.exe -m pytest -q`.
- **Migrations**: Alembic sequencial, revisions encadeadas. Nome sugerido `jXXXX_add_route_group_leg_and_details.py`.
- **Polling**: `polling_service.run_polling_cycle` itera grupos ativos. Phase 36 adiciona ramificacao por `mode`.

### Integration Points
- `/groups/create` (GET + POST) — adiciona toggle + builder dinamico
- `/groups/{id}/edit` — carregar legs existentes
- `/groups/{id}` detail — render multi vs roundtrip
- `/` dashboard home — loop de cards ramifica layout
- Cron de polling in-process (APScheduler) — continua dispararando pra todos os grupos ativos
- Email consolidado — `_render_consolidated_html/plain` ramifica por `group.mode`

</code_context>

<specifics>
## Specific Ideas

- Usuario pediu essa feature como "grupo dentro do grupo" — o mental model e **roteiro com blocos sequenciais**, nao "varios grupos relacionados".
- Caso de uso motivador: "Vou pra Italia em junho, fico 2 semanas, ai pra Espanha, fico 10 dias, e depois volto pro Brasil."
- Decisao de UX: auto-calcular janela do trecho N+1 quando N eh preenchido, com override manual. Reduz friccao sem perder flexibilidade.
- Decisao de negocio: sem afiliado. CTAs sao cluster "Comparar precos em" por trecho (4 providers brasileiros conhecidos).
- Copy decidido: badge `MULTI`, label `Preco total do roteiro`, subject `Orbita multi: ...`.

</specifics>

<deferred>
## Deferred Ideas

Ideias surgidas que nao entram nessa fase:

- **Passageiros variaveis por trecho** ("vou com 2 ate Roma, volto sozinho") — capturar se houver pedido real de usuario em v3+
- **URL multi-city consolidada** nos botoes de comparador — Google Flights suporta mas Decolar/Skyscanner/Kayak divergem; adiar ate ter volume que justifique research
- **Top 3 combinacoes de datas** no detail do grupo multi — hoje mostra so a combinacao mais barata, que ja cobre o caso principal
- **Stopover pago intencional** (overnight em hub como leg separado) — user decide manualmente se quiser
- **Open-jaw** (chegar em uma cidade, voltar de outra) — modelo ja suporta se usuario desenhar, mas nao destaca na UI
- **Otimizacao automatica de hub/rota** — "sugerir ir pra Madrid antes de Roma" — feature v3+
- **Affiliate multi-city (Plan 4 do SPEC original)** — removido agora que monetizacao nao eh prioridade; endpoint `/comprar/` continua existindo e pode ser reativado depois
- **Milhas + dinheiro combinado** — fora do radar

### Reviewed Todos (not folded)
Nenhum todo revisado foi deferido (nenhum match encontrado).

</deferred>

---

*Phase: 36-multi-leg*
*Context gathered: 2026-04-22*
