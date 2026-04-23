# Phase 36: Multi-Leg Trip Builder - Research

**Researched:** 2026-04-22
**Domain:** Modelagem de roteiros encadeados + reuso de cache/prediction + UI SSR dinamica
**Confidence:** HIGH (CONTEXT.md ja consolidou decisoes; codigo base inspecionado in-repo; sem incertezas de stack externa)

## Summary

A Phase 36 adiciona roteiros multi-trecho ao modelo de monitoramento da Orbita. As decisoes arquiteturais estao todas travadas no `36-CONTEXT.md` (D-01 a D-20): nova tabela `RouteGroupLeg` 1:N com `RouteGroup`, reuso de `FlightSnapshot` com coluna nova `details: JSON` contendo breakdown do roteiro, ramificacao do `polling_service` por `group.mode`, e reuso integral da engine `price_prediction_service.predict_action` sobre o preco total agregado. A busca faz produto cartesiano de datas candidatas por trecho (cap de 7 por leg, decidido pelo planner) filtrado por validade temporal (`actual_departure[N+1] >= actual_return[N] + min_stay`).

O maior risco operacional e **consumo de quota SerpAPI**: um grupo com 4 trechos em rotas fora das 28 seed do `route_cache` dispara ate 4 chamadas SerpAPI por ciclo de polling, multiplicado por 2 ciclos/dia = 8 chamadas/dia/grupo. Com 250/mes de quota free, 3 grupos multi em rotas nao cacheadas consumiriam a quota em ~10 dias. Mitigacao: D-12 ja define fallback on-demand + populacao do `route_cache` na primeira busca, e o `quota_service` ja existe e bloqueia quando exaurido.

O maior risco de UX e a **validacao temporal do construtor dinamico** em JS vanilla (D-08): auto-calculo de janelas encadeadas (D-09) exige event listeners que recalculam `leg[N+1].window_start` quando o usuario muda `leg[N].window_end` ou `leg[N].min_stay_days`. Sem framework, a solucao e funcao `recalcLegs()` disparada em `input` change, preservando overrides manuais via flag `data-manual-override`.

**Primary recommendation:** Seguir strictly as decisoes ja travadas no CONTEXT.md. A migration Alembic cria `route_group_legs` + adiciona `flight_snapshots.details: JSON`. O `multi_leg_service` e a unica camada nova; tudo mais e extensao minima de servicos existentes. Wave 0 precisa incluir fixtures `multi_leg_group` e `multi_leg_snapshot` em `conftest.py`.

## User Constraints (from CONTEXT.md)

### Locked Decisions

**Modelo de dados:**
- **D-01:** `RouteGroup.mode="multi_leg"` faz `origins/destinations/travel_start/travel_end` serem ignorados; `legs[]` e a verdade.
- **D-02:** Nova tabela `RouteGroupLeg` 1:N: `id, route_group_id FK, order, origin, destination, window_start, window_end, min_stay_days, max_stay_days (null=sem teto), max_stops`. Unique `(route_group_id, order)`.
- **D-03:** Snapshot multi reusa `FlightSnapshot` com `airline="MULTI"` + coluna nova `details: JSON` contendo `{total_price, legs: [{order, origin, destination, date, price, airline}, ...]}`.

**Validacao temporal:**
- **D-04:** Criacao: `leg[N+1].window_start >= leg[N].window_end + leg[N].min_stay_days`. Busca: cada combinacao respeita `actual_departure[N+1] >= actual_return[N] + min_stay` (e <= + max_stay se definido).
- **D-05:** Min 2 trechos, max 5.
- **D-06:** Min 1 dia de stay; max_stay opcional (null = sem teto).

**UI (form):**
- **D-07:** Toggle no topo de `/groups/create`: `Roundtrip simples` (default) / `Multi-trecho`.
- **D-08:** Construtor dinamico em **JS vanilla** (sem framework), botoes `+ Adicionar trecho` / `- Remover`.
- **D-09:** Janela de `leg[N+1]` **auto-calculada** a partir de `leg[N].window_end + leg[N].min_stay_days` ate `+ max_stay_days`. Preenchida mas editavel (override manual).
- **D-10:** Passageiros: valor unico global em `RouteGroup.passengers`. Variacao por trecho fica deferida.

**Busca:**
- **D-11:** `polling_service` ramifica em `if group.mode == "multi_leg"` e chama `multi_leg_service.search_multi_leg_prices(db, group)`.
- **D-12:** Cada trecho consulta `route_cache` primeiro. Miss cai pra SerpAPI on-demand e popula cache. Logar em `cache_lookup_log`.
- **D-13:** Algoritmo: produto cartesiano filtrado por validade temporal, escolhe combinacao de menor preco total. 1 FlightSnapshot com `airline="MULTI"` e `details` JSON.

**Sinal e prediction:**
- **D-14:** `signal_service` aplica logica existente sobre `total_price` (mediana/desvio 90d sobre snapshots multi do mesmo grupo).
- **D-15:** `price_prediction_service.predict_action` recebe `total_price`, mediana dos totais, stddev dos totais, `days_to_departure` do **primeiro trecho**. Reusa engine Phase 34 sem modificacao.

**UI dashboard e email:**
- **D-16:** Card multi mostra cadeia `GRU -> FCO -> MAD -> GRU`, badge `MULTI` (mono, cyan), label `Preco total do roteiro`.
- **D-17:** Cada trecho tem seu cluster `Comparar precos em` com os 4 botoes (Google Flights, Decolar, Skyscanner, Kayak) apontando pra busca **individual**. URL multi-city consolidada deferida.
- **D-18:** Detalhe mostra breakdown trecho-a-trecho + total. Apenas **combinacao mais barata** (top 3 deferido).
- **D-19:** Email consolidado multi: cadeia no header, total em destaque, tabela com breakdown, recomendacao no topo (Phase 34), cluster comparadores por trecho.
- **D-20:** Subject: `Orbita multi: [Nome] R$ X,XX (N trechos)`.

### Claude's Discretion
- UI exata do construtor (ordem de campos, cores de separadores, animacao) — seguir tokens `--bg-2`, `--border-2`, `--brand-500`
- Cap de datas candidatas por trecho no produto cartesiano (sugerido: **7**, discutido abaixo)
- Serializacao Pydantic dos schemas `LegCreate`, `LegOut`, `RouteGroupMultiCreate`
- Nome da migration Alembic
- Texto de mensagens de erro de validacao temporal

### Deferred Ideas (OUT OF SCOPE)
- Passageiros variaveis por trecho
- URL multi-city consolidada nos botoes comparadores
- Top 3 combinacoes de datas no detail
- Stopover pago intencional
- Open-jaw com UI destacada
- Otimizacao automatica de hub/rota
- Affiliate multi-city
- Milhas + dinheiro

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MULTI-01 | Usuario cria grupo-pai com N trechos sequenciais (origin, destination, janela, min/max stay) | D-01, D-02, D-07, D-08 no CONTEXT; modelo `RouteGroupLeg` e schemas Pydantic |
| MULTI-02 | Sistema valida encadeamento temporal | D-04, D-05, D-06; validacao server-side (Pydantic + verificacao cruzada) + validacao client-side no builder (D-09) |
| MULTI-03 | Sistema busca precos de cada trecho via cache/SerpAPI e calcula preco total | D-11, D-12, D-13; novo `multi_leg_service` ramificado no `polling_service`; reuso de `flight_search.search_flights_ex` + `route_cache_service` |
| MULTI-04 | Sinal e prediction aplicados sobre preco total, nao trecho a trecho | D-14, D-15; reuso integral da engine `price_prediction_service.predict_action` e logica de sinal existente, operando sobre `FlightSnapshot.price` dos snapshots multi (onde `price = total_price` do roteiro) |

## Project Constraints (from CLAUDE.md)

- **Stack obrigatoria:** Python 3.11, FastAPI, Jinja2 SSR puro (sem framework JS), PostgreSQL Neon, APScheduler, SQLAlchemy 2.0 + Alembic.
- **pt-BR acentuacao obrigatoria** em texto visivel (templates, emails, flashes). Codigo/identificadores/URLs sem acento.
- **Sem emojis** em codigo, commits, docs.
- **Travessao proibido** em copy (usar ponto ou virgula).
- **CSS tokens centralizados** em `base.html` (`--bg-0`, `--brand-500`, `--accent-500`, `--border-2`). Nao hardcodar hex em templates novos.
- **SSR puro** — JS apenas pra interacoes pontuais (builder dinamico se qualifica; manter vanilla).
- **SDD + TDD** — spec aprovada, testes RED antes de implementacao, GREEN minimo, refactor com testes verdes. Cada nova feature tem happy path + edge cases + erro esperado + integracao.
- **Alembic sequencial** — nova revision encadeada, nunca editar migration publicada.
- **Atomic commits** — Conventional Commits (feat/fix/chore/docs/refactor), um escopo por commit.
- **Never scale** Fly.io para multiplas maquinas (duplica cron APScheduler).

## Standard Stack

### Core (ja presente no repo; Phase 36 nao adiciona dependencias novas)

| Library | Version (pyproject/runtime) | Purpose | Why Standard |
|---------|-----------------------------|---------|--------------|
| FastAPI | 0.115 | HTTP routing, form handlers | Ja em uso em `app/routes/route_groups.py` |
| SQLAlchemy | 2.0 | ORM + `Mapped[]` style, `JSON` type | Ja em uso em `app/models.py` |
| Alembic | 1.18 | Schema migrations | Ja em uso; revisions encadeadas em `alembic/versions/` |
| Pydantic | 2.x (vem com FastAPI) | Schemas de request/response + validacao temporal | Ja em uso em `app/schemas.py` |
| Jinja2 | vem com FastAPI | SSR templates | `app/templates/dashboard/` |
| pytest | (conftest.py ativo) | Testes com SQLite in-memory | `tests/conftest.py` fixtures ja estabelecidas |

### Supporting (existentes, reusados)

| Service | Purpose | When to Use |
|---------|---------|-------------|
| `app/services/flight_search.py::search_flights_ex` | Cache in-memory 30min + SerpAPI | Chamado 1x por leg no `multi_leg_service` |
| `app/services/route_cache_service.py::get_cached_price` | Cache persistente 6h Travelpayouts | Primeiro lookup por leg antes de SerpAPI |
| `app/services/price_prediction_service.py::predict_action` | Engine deterministica COMPRE/AGUARDE/MONITORAR (Phase 34) | Chamar sobre `total_price` + agregado 90d |
| `app/services/signal_service.py::detect_signals` | Deteccao de 4 tipos de sinal + dedup 12h | Operar sobre snapshot multi como se fosse roundtrip (price = total_price) |
| `app/services/quota_service.py` | Budget SerpAPI compartilhado | Verificar antes de cada miss de leg |
| `app/services/snapshot_service.py::save_flight_snapshot, is_duplicate_snapshot` | Persistencia + dedup | Reuso direto, com `details=JSON` nos kwargs |
| `app/services/alert_service.py::compose_consolidated_email` | Email consolidado | Ramificar por `group.mode` para render multi |
| `app/services/dashboard_service.py::get_groups_with_summary` | Agregacao para cards | Adicionar legs + total_price quando `mode="multi_leg"` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Tabela separada `MultiLegSnapshot` (D-03 rejeitou) | Modelo novo dedicado | Duplica queries; quebra reuso de signal_service que ja filtra por `route_group_id`. D-03 vence: coluna `details: JSON` em `FlightSnapshot` e suficiente |
| Form JSON + SPA (rejeitado por convencao SSR) | Alpine.js ou HTMX | CLAUDE.md proibe JS framework; builder vanilla cumpre D-08 |
| Scipy/itertools.product com cap dinamico | Implementacao manual | `itertools.product` + filtro temporal lazy e suficiente e estatisticamente seguro ate 5 legs × 7 datas = 16807 combinacoes (aceitavel em memoria) |

**Instalacao:** Nenhuma dep nova.

**Version verification:** N/A — stack ja fixada pelos phases 10, 11, 14, 32, 34.

## Architecture Patterns

### Recommended Structure (deltas only)

```
app/
├── models.py                              # + RouteGroupLeg, + FlightSnapshot.details
├── schemas.py                             # + LegCreate, LegOut, RouteGroupMultiCreate
├── services/
│   ├── multi_leg_service.py               # NOVO — search_multi_leg_prices()
│   ├── polling_service.py                 # branch if group.mode == "multi_leg"
│   ├── signal_service.py                  # inalterado (opera sobre price via FlightSnapshot)
│   ├── dashboard_service.py               # + leg breakdown no dict de retorno quando multi
│   └── alert_service.py                   # + _render_consolidated_html_multi(...)
├── routes/
│   └── route_groups.py                    # POST aceita legs[] via form
├── templates/dashboard/
│   ├── create.html                        # + toggle + builder dinamico (JS vanilla inline ou em <script>)
│   ├── edit.html                          # + carrega legs existentes
│   ├── index.html                         # + card variant multi
│   └── detail.html                        # + layout breakdown multi
alembic/versions/
└── jXXXX_add_route_group_leg_and_details.py  # NOVO — 1 migration
tests/
├── conftest.py                            # + fixture multi_leg_group, multi_leg_snapshot
├── test_multi_leg_service.py              # NOVO — produto cartesiano, validacao temporal, agregacao
├── test_multi_leg_model.py                # NOVO — constraints, relationship
├── test_multi_leg_routes.py               # NOVO — POST /groups com legs[]
├── test_multi_leg_polling.py              # NOVO — branch integration
└── test_multi_leg_email.py                # NOVO — render consolidated multi
```

### Pattern 1: Produto Cartesiano de Datas com Filtro Temporal

**What:** Gerar todas as combinacoes validas `(leg1_dates, leg2_dates, ..., legN_dates)` respeitando stay constraints e escolher a de menor preco total.

**When to use:** `multi_leg_service.search_multi_leg_prices()`.

**Algoritmo:**

```python
# app/services/multi_leg_service.py
import itertools
from datetime import date, timedelta

DATE_CANDIDATES_PER_LEG = 7  # Claude's discretion; cap decidido pelo planner

def _candidate_dates(leg) -> list[date]:
    """Amostra ate 7 datas dentro da janela do trecho."""
    total_days = (leg.window_end - leg.window_start).days
    if total_days <= DATE_CANDIDATES_PER_LEG:
        return [leg.window_start + timedelta(days=i) for i in range(total_days + 1)]
    step = total_days // (DATE_CANDIDATES_PER_LEG - 1)
    return [leg.window_start + timedelta(days=i * step) for i in range(DATE_CANDIDATES_PER_LEG)]


def _is_valid_chain(dates: tuple[date, ...], legs: list) -> bool:
    """Cada data respeita min/max_stay do trecho anterior."""
    for i in range(1, len(dates)):
        gap = (dates[i] - dates[i - 1]).days
        if gap < legs[i - 1].min_stay_days:
            return False
        if legs[i - 1].max_stay_days is not None and gap > legs[i - 1].max_stay_days:
            return False
    return True


def search_multi_leg_prices(db, group) -> FlightSnapshot | None:
    legs = sorted(group.legs, key=lambda l: l.order)
    candidate_sets = [_candidate_dates(leg) for leg in legs]

    best_total = None
    best_combo = None
    for combo in itertools.product(*candidate_sets):
        if not _is_valid_chain(combo, legs):
            continue
        prices = []
        for leg, dep_date in zip(legs, combo):
            # one-way lookup: return_date nao se aplica ate o proximo leg
            price_data = _fetch_leg_price(db, leg, dep_date)  # route_cache -> SerpAPI fallback
            if price_data is None:
                break
            prices.append(price_data)
        else:
            total = sum(p["price"] for p in prices)
            if best_total is None or total < best_total:
                best_total = total
                best_combo = (combo, prices)
    if best_combo is None:
        return None
    return _persist_multi_snapshot(db, group, best_combo)
```

### Pattern 2: Snapshot com `details` JSON

```python
snapshot = FlightSnapshot(
    route_group_id=group.id,
    origin=legs[0].origin,
    destination=legs[-1].destination,
    departure_date=combo[0],
    return_date=combo[-1],  # ultimo leg funciona como "return" pra queries de ordenacao
    price=best_total,
    currency="BRL",
    airline="MULTI",
    source="multi_leg",
    details={
        "total_price": best_total,
        "legs": [
            {"order": leg.order, "origin": leg.origin, "destination": leg.destination,
             "date": combo[i].isoformat(), "price": prices[i]["price"], "airline": prices[i]["airline"]}
            for i, leg in enumerate(legs)
        ],
    },
)
```

### Pattern 3: Validacao Pydantic Cruzada entre Legs

```python
# app/schemas.py
from pydantic import BaseModel, model_validator
from datetime import date

class LegCreate(BaseModel):
    order: int
    origin: str
    destination: str
    window_start: date
    window_end: date
    min_stay_days: int
    max_stay_days: int | None = None
    max_stops: int | None = None

class RouteGroupMultiCreate(BaseModel):
    name: str
    passengers: int = 1
    target_price: float | None = None
    legs: list[LegCreate]

    @model_validator(mode="after")
    def validate_chain(self):
        if not (2 <= len(self.legs) <= 5):
            raise ValueError("Roteiro multi exige entre 2 e 5 trechos.")
        sorted_legs = sorted(self.legs, key=lambda l: l.order)
        for i in range(1, len(sorted_legs)):
            prev = sorted_legs[i - 1]
            cur = sorted_legs[i]
            min_start = prev.window_end + timedelta(days=prev.min_stay_days)
            if cur.window_start < min_start:
                raise ValueError(
                    f"Trecho {cur.order} precisa sair em ou apos {min_start.isoformat()} "
                    f"(janela do trecho anterior + estadia minima)."
                )
        return self
```

### Pattern 4: Builder Dinamico em JS Vanilla (D-08)

```html
<!-- app/templates/dashboard/create.html (fragment) -->
<template id="leg-template">
  <fieldset class="leg" data-order="__N__">
    <legend>Trecho <span class="leg-num">__N__</span></legend>
    <input name="legs[__N__][origin]" data-field="origin" ...>
    ... (outros campos) ...
    <button type="button" class="remove-leg">Remover</button>
  </fieldset>
</template>

<script>
  const MAX_LEGS = 5;
  function addLeg() { /* clona template, anexa, chama recalc */ }
  function removeLeg(i) { /* remove, renumera, chama recalc */ }
  function recalcLegs() {
    // Para cada leg N > 0: se nao tem data-manual-override,
    // window_start = legs[N-1].window_end + min_stay
    // window_end = window_start + max_stay (se definido) ou +30 default
  }
  document.addEventListener("input", (e) => {
    if (e.target.closest(".leg")) {
      if (e.target.matches("[data-field=window_end], [data-field=min_stay_days]")) {
        recalcLegs();
      } else if (e.target.matches("[data-field=window_start], [data-field=window_end]")) {
        e.target.closest(".leg").dataset.manualOverride = "true";
      }
    }
  });
</script>
```

### Anti-Patterns to Avoid

- **Criar tabela dedicada `MultiLegSnapshot`** — D-03 ja rejeitou; duplica queries de signal/dashboard.
- **Validar encadeamento apenas no client** — sempre re-validar server-side (Pydantic `model_validator`). Client-side e UX, nao seguranca.
- **Chamar SerpAPI em paralelo (asyncio.gather)** — FastAPI sync routes + APScheduler sync jobs. Manter serial; 4 chamadas × 2s = 8s por grupo, aceitavel.
- **Armazenar total_price em coluna propria duplicada** — `FlightSnapshot.price` ja serve. Simplicidade > normalizacao extra.
- **Usar `JSON` em PostgreSQL sem `nullable=True` + migration data-safe** — snapshots antigos nao tem `details`; coluna precisa ser nullable para nao quebrar backfill.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Produto cartesiano de datas | Nested loops manuais | `itertools.product` | Stdlib, legivel, lazy; 5 niveis aninhados nao escalam |
| Validacao de schema | `if/raise` manual no route handler | Pydantic `@model_validator(mode="after")` | Validacao declarativa, erro HTTP 422 automatico, mensagens estruturadas |
| Cache de leg individual | Logica nova | `flight_search.search_flights_ex(one_way=True?)` — verificar se ja suporta ida simples, senao usar `(origin, dest, dep_date, dep_date)` como workaround | Ja tem in-memory + SerpAPI + log |
| Engine de prediction | Nova implementacao | `price_prediction_service.predict_action(total_price, median_of_totals_90d, stddev_of_totals_90d, days_to_first_departure, snapshot_count, first_departure_date)` | Phase 34 ja testada e com backtest |
| Persistencia de snapshot | Novo INSERT | `snapshot_service.save_flight_snapshot(..., details={...})` + garantir que `is_duplicate_snapshot` considera `airline="MULTI"` | Dedup ja pronto |
| Dedup 12h de sinal | Nova logica | `signal_service.detect_signals()` ja faz dedup por `(route_group_id, signal_type, 12h)` | Funciona igual pra snapshots multi |
| Render email consolidado | Novo template | Ramo em `_render_consolidated_html` com helper `_render_multi_leg_section(snapshot.details)` | Ja tem infra de MIME, styling inline, subject builder |
| Form handling | Novo endpoint | Adicionar form POST em `/groups` existente com deteccao de `mode=multi_leg` | FastAPI form handlers + Pydantic ja fazem |

**Key insight:** A Phase 36 e **integracao, nao reinvencao**. Todo servico novo e 1 arquivo (`multi_leg_service.py`); todo o resto e extensao minima. Se um plan de task parecer grande, provavelmente esta duplicando algo existente — reverificar antes de implementar.

## Runtime State Inventory

Nao aplicavel. Phase 36 e feature greenfield puramente aditiva:
- Nenhum rename — todos os nomes novos (`RouteGroupLeg`, `multi_leg_service`, `mode="multi_leg"`) nunca existiram.
- Stored data: **None** — criando estrutura nova.
- Live service config: **None** — APScheduler jobs existentes continuam chamando `run_polling_cycle()` que internamente ramifica; nao ha novo cron.
- OS-registered state: **None** — Fly.io deploy nao requer re-registro.
- Secrets/env vars: **None** — reusa SerpAPI + Travelpayouts existentes.
- Build artifacts: **None** — sem package rename.

## Common Pitfalls

### Pitfall 1: `FlightSnapshot.details` como NOT NULL quebra backfill

**What goes wrong:** Alembic migration adiciona coluna com default ou NOT NULL; snapshots existentes (todos roundtrip) falham.

**Why it happens:** Migration autogenerate do Alembic deduz NOT NULL por padrao se o model define `JSON` sem `nullable=True`.

**How to avoid:** Declarar `Mapped[dict | None] = mapped_column(JSON, nullable=True, default=None)` no model. Explicitar `nullable=True` no `op.add_column` da migration manualmente.

**Warning signs:** Teste `test_historical_context.py` ou `test_dashboard.py` falhando apos migration.

### Pitfall 2: `is_duplicate_snapshot` ignora `details`, dedupa snapshots multi diferentes como iguais

**What goes wrong:** Dois ciclos de polling geram combinacoes diferentes (datas diferentes por produto cartesiano), mas o dedup compara so `(origin, destination, departure_date, return_date, price)` e pode colidir.

**Why it happens:** `snapshot_service.is_duplicate_snapshot` foi escrito para roundtrip; nao conhece multi.

**How to avoid:** Adicionar branch: se `airline == "MULTI"`, dedup considera `(route_group_id, total_price, first_leg_date, last_leg_date)` — precisao suficiente, evita falso positivo.

**Warning signs:** Dashboard mostra mesmo snapshot multi persistido 2x no mesmo dia.

### Pitfall 3: `price_prediction_service` com `days_to_departure` errado

**What goes wrong:** Recomendacao usa data do ultimo trecho em vez do primeiro; sistema diz "compre agora" quando ja passou da janela otima do leg inicial.

**Why it happens:** D-15 especifica `first_departure`, mas e facil confundir com `snapshot.departure_date` vs `snapshot.return_date`.

**How to avoid:** `days_to_departure = (snapshot.departure_date - date.today()).days` — `departure_date` do snapshot multi ja e o **primeiro** leg (convencao D-03 + Pattern 2).

**Warning signs:** Recomendacao AGUARDE quando voo ja e em 20 dias; ou COMPRE quando voo e em 200 dias.

### Pitfall 4: Quota SerpAPI exaurida pela criacao de grupos multi

**What goes wrong:** Usuario cria grupo 4-trecho em rotas fora das 28 seed; primeira busca consome 4 chamadas SerpAPI; 3 usuarios fazem o mesmo e o mes acabou.

**Why it happens:** D-12 aceita o custo, mas sem mitigacao visivel ao usuario a UX degrada silenciosamente.

**How to avoid:** (a) Antes de aceitar criacao, checar `quota_service.get_remaining_quota(db)` e se < `num_legs * 2`, mostrar aviso no form "Quota SerpAPI do mes baixa — primeira busca pode ficar pendente ate proximo mes". (b) Logar cada hit/miss em `cache_lookup_log` pra analise posterior. (c) Nao bloquear criacao — preco vira quando houver quota (cache_miss, rota nao seed, sem quota = snapshot nulo no ciclo, retry ciclo seguinte).

**Warning signs:** Muitos grupos ativos sem nenhum snapshot recente; `/admin/stats` mostra quota zerada em < 20 dias do mes.

### Pitfall 5: Validacao Pydantic `model_validator` executa antes de `order` estar ordenado

**What goes wrong:** Frontend envia legs na ordem que o usuario digitou (nao ordenado por `order`), validacao compara `leg[i]` vs `leg[i+1]` do array e falha falsamente.

**Why it happens:** Pydantic preserva ordem do JSON de entrada.

**How to avoid:** Sempre `sorted(self.legs, key=lambda l: l.order)` dentro do validator antes de iterar.

**Warning signs:** Erro 422 em legs que o humano ve como validos.

### Pitfall 6: Produto cartesiano explode em grupos sem max_stay

**What goes wrong:** Grupo com 5 legs, cada leg com janela de 60 dias e sem max_stay, gera `60^5 = 778M` combinacoes se amostradas 1-dia.

**Why it happens:** Produto cartesiano sem cap.

**How to avoid:** Respeitar `DATE_CANDIDATES_PER_LEG = 7` (cap fixo). Mesmo sem max_stay, amostramos 7 datas por leg → `7^5 = 16807` combinacoes, maioria filtrada pelo `_is_valid_chain`. Caso real de execucao < 1000 combinacoes.

**Warning signs:** `_poll_group` demora > 30s; log de timeout no APScheduler.

### Pitfall 7: Card dashboard tenta renderizar legs mas snapshot ainda e None (grupo recem-criado)

**What goes wrong:** `get_groups_with_summary` retorna dict sem `legs_breakdown` quando snapshot e None, mas template assume presenca → `UndefinedError`.

**Why it happens:** Template Jinja sem `{% if %}` guard.

**How to avoid:** `dashboard_service.get_groups_with_summary` sempre retorna `legs_breakdown: list[dict] | None`. Template usa `{% if group.legs_breakdown %}` antes de iterar.

**Warning signs:** Dashboard 500 apos criar grupo multi pela primeira vez.

### Pitfall 8: Copy do email com travessao (proibido por convencao)

**What goes wrong:** Copywriter escreve "Trecho 1 - GRU - FCO" usando hifen-cercado-de-espaco (travessao). CLAUDE.md proibe.

**How to avoid:** Use seta ASCII `->` ou flecha unicode pra chain visual; hifens so em palavras compostas (IATA = 3 letras, sem hifens aqui).

**Warning signs:** Code review humano sinaliza; nao ha linter automatico pra isso.

## Code Examples

Verificados contra codigo existente no repo. Paths relativos a `flight-monitor/`.

### Exemplo 1: Registro e relationship em `app/models.py`

```python
# Source: padrao existente em app/models.py (RouteGroup, FlightSnapshot)
class RouteGroupLeg(Base):
    __tablename__ = "route_group_legs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    route_group_id: Mapped[int] = mapped_column(
        ForeignKey("route_groups.id", ondelete="CASCADE"), index=True
    )
    order: Mapped[int] = mapped_column(Integer)
    origin: Mapped[str] = mapped_column(String(3))
    destination: Mapped[str] = mapped_column(String(3))
    window_start: Mapped[datetime.date] = mapped_column(Date)
    window_end: Mapped[datetime.date] = mapped_column(Date)
    min_stay_days: Mapped[int] = mapped_column(Integer, default=1)
    max_stay_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_stops: Mapped[int | None] = mapped_column(Integer, nullable=True)

    route_group: Mapped["RouteGroup"] = relationship("RouteGroup", back_populates="legs")

    __table_args__ = (
        Index("ix_route_group_legs_group_order", "route_group_id", "order", unique=True),
    )


# Em RouteGroup, adicionar:
# legs: Mapped[list["RouteGroupLeg"]] = relationship(
#     "RouteGroupLeg", back_populates="route_group",
#     cascade="all, delete-orphan", order_by="RouteGroupLeg.order"
# )

# Em FlightSnapshot, adicionar:
# details: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=None)
```

### Exemplo 2: Migration Alembic

```python
# Source: padrao em alembic/versions/g7h8i9j0k1l2_add_route_cache_table.py
"""add route_group_legs and flight_snapshots.details

Revision ID: jXXXXXXXXXXXX
Revises: i9j0k1l2m3n4
Create Date: 2026-04-22 ...
"""
from alembic import op
import sqlalchemy as sa

revision = "jXXXXXXXXXXXX"
down_revision = "i9j0k1l2m3n4"

def upgrade() -> None:
    op.create_table(
        "route_group_legs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("route_group_id", sa.Integer,
                  sa.ForeignKey("route_groups.id", ondelete="CASCADE"), nullable=False),
        sa.Column("order", sa.Integer, nullable=False),
        sa.Column("origin", sa.String(3), nullable=False),
        sa.Column("destination", sa.String(3), nullable=False),
        sa.Column("window_start", sa.Date, nullable=False),
        sa.Column("window_end", sa.Date, nullable=False),
        sa.Column("min_stay_days", sa.Integer, nullable=False, server_default="1"),
        sa.Column("max_stay_days", sa.Integer, nullable=True),
        sa.Column("max_stops", sa.Integer, nullable=True),
    )
    op.create_index("ix_route_group_legs_group_order",
                    "route_group_legs", ["route_group_id", "order"], unique=True)
    op.add_column("flight_snapshots",
                  sa.Column("details", sa.JSON(), nullable=True))

def downgrade() -> None:
    op.drop_column("flight_snapshots", "details")
    op.drop_index("ix_route_group_legs_group_order", table_name="route_group_legs")
    op.drop_table("route_group_legs")
```

### Exemplo 3: Integracao polling

```python
# Source: padrao em app/services/polling_service.py::_poll_group
def _poll_group(db, group):
    if group.mode == "multi_leg":
        from app.services.multi_leg_service import search_multi_leg_prices
        snapshot = search_multi_leg_prices(db, group)
        if snapshot is None:
            logger.warning("multi_leg: sem precos para group %s", group.id)
            return
        signals = signal_service.detect_signals(db, snapshot)
        if signals and should_alert(group):
            # alert_service ramifica por group.mode internamente
            _send_consolidated_alert(db, group, [snapshot], signals)
        return
    # fluxo normal roundtrip existente abaixo...
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Varios grupos relacionados para simular multi | `RouteGroup.mode="multi_leg"` + `legs[]` 1:N | Phase 36 (nova) | Usuario tem mental model unico; sinal/prediction sobre total |
| fast-flights para busca | SerpAPI + route_cache only | Phase 31.9 | Phase 36 herda; nao precisa lidar com fast-flights |
| Snapshot roundtrip fixed schema | `details: JSON` opcional | Phase 36 | Extensibilidade sem tabela nova |
| Prediction roundtrip-only | Mesma engine sobre total agregado | Phase 36 (reuso) | D-15 confirma engine Phase 34 e agnostica de estrutura |

**Deprecated/outdated:** Nenhum componente legado em Phase 36 (tudo e adicao; nada e removido).

## Open Questions

1. **`search_flights_ex` suporta busca one-way puro?**
   - What we know: A assinatura atual exige `departure_date` + `return_date`. O `flight_cache.make_key` inclui ambos.
   - What's unclear: Se passar `return_date == departure_date` retorna resultado sane da SerpAPI para voo de ida apenas.
   - Recommendation: Planner investiga em Wave 0 (task 1). Se nao suportar, adicionar parametro `one_way: bool = False` ao `search_flights_ex` OU criar `search_flights_one_way` helper em `multi_leg_service`. Custo: 1 task extra.

2. **Como o dashboard card mostra `legs_breakdown` sem poluir o home quando usuario tem muitos grupos?**
   - What we know: D-16 define cadeia `GRU -> FCO -> MAD -> GRU` + badge + label, mas nao especifica se mostra breakdown total no card ou apenas no detalhe.
   - What's unclear: Altura do card multi vs roundtrip — manter paridade visual.
   - Recommendation: Card multi mostra **apenas** cadeia + total + recomendacao + badge MULTI. Breakdown trecho-a-trecho fica na pagina de detalhe (D-18). Mantem card com mesma altura.

3. **Cap de 7 candidatos de data por trecho e suficiente?**
   - What we know: 7^5 = 16807 combos, maioria filtradas por `_is_valid_chain`. Exec em memoria trivial.
   - What's unclear: Em janelas longas (60 dias), 7 samples = 1 a cada 10 dias — pode perder preco bom entre amostras.
   - Recommendation: Comecar com 7 (Claude's discretion). Se backtest mostrar viés sistematico de "melhor data esta a 5 dias do amostrado", subir para 10. Planner inclui configuracao via constante em `multi_leg_service.py`.

4. **Signal detection sobre snapshots multi precisa de BALDE FECHANDO/REABERTO?**
   - What we know: `signal_service` detecta 4 sinais. Balde fechando/reaberto dependem de `booking_class_snapshots` que foi removido (Phase 21 planned). Atualmente o servico detecta PRECO ABAIXO DO HISTORICO + JANELA OTIMA que operam sobre `FlightSnapshot.price`.
   - What's unclear: Quais sinais efetivamente disparam em snapshots multi.
   - Recommendation: Confirmar com codigo de `signal_service.detect_signals()` no Wave 0 task de investigacao. Provavel que PRECO ABAIXO DO HISTORICO + JANELA OTIMA + prediction (Phase 34) cubram o caso. BALDE sinais ja nao disparam em producao por falta de dado de inventario.

## Environment Availability

Nao aplicavel — Phase 36 nao introduz dependencias externas novas. Reusa SerpAPI + Travelpayouts + PostgreSQL Neon ja em producao desde Phases 20/32.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (inferido de `tests/conftest.py`, `pyproject.toml [tool.pytest.ini_options]`) |
| Config file | `pyproject.toml` (`testpaths=["tests"]`, `python_files=["test_*.py"]`) |
| Quick run command | `.venv/Scripts/python.exe -m pytest tests/test_multi_leg_*.py -x -q` |
| Full suite command | `.venv/Scripts/python.exe -m pytest -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MULTI-01 | Criar grupo com 2-5 legs via POST /groups | integration | `pytest tests/test_multi_leg_routes.py::test_create_multi_leg_group_valid -x` | Wave 0 |
| MULTI-01 | Model RouteGroupLeg persiste e cascade delete | unit | `pytest tests/test_multi_leg_model.py::test_leg_cascade_delete -x` | Wave 0 |
| MULTI-01 | Toggle form muda campos visiveis (UI manual) | manual | checkpoint visual em `/groups/create` | Wave 0 |
| MULTI-02 | Pydantic rejeita `leg[1].window_start < leg[0].window_end + min_stay` | unit | `pytest tests/test_multi_leg_model.py::test_chain_validation_rejects_overlap -x` | Wave 0 |
| MULTI-02 | Aceita 2 trechos, rejeita 1 ou 6 | unit | `pytest tests/test_multi_leg_model.py::test_min_max_legs -x` | Wave 0 |
| MULTI-02 | Produto cartesiano filtra combos invalidos temporalmente | unit | `pytest tests/test_multi_leg_service.py::test_is_valid_chain -x` | Wave 0 |
| MULTI-03 | `search_multi_leg_prices` consulta route_cache primeiro por leg | integration | `pytest tests/test_multi_leg_service.py::test_uses_route_cache_before_serpapi -x` | Wave 0 |
| MULTI-03 | Persiste 1 FlightSnapshot com airline=MULTI e details JSON | integration | `pytest tests/test_multi_leg_service.py::test_persists_multi_snapshot_with_details -x` | Wave 0 |
| MULTI-03 | Retorna combinacao de menor preco total | unit | `pytest tests/test_multi_leg_service.py::test_picks_cheapest_total -x` | Wave 0 |
| MULTI-04 | `signal_service` opera sobre total_price via FlightSnapshot.price | integration | `pytest tests/test_multi_leg_polling.py::test_signal_on_total_price -x` | Wave 0 |
| MULTI-04 | `price_prediction_service.predict_action` usa median/stddev dos totais 90d | integration | `pytest tests/test_multi_leg_service.py::test_prediction_uses_total_median -x` | Wave 0 |
| D-16/D-18 | Dashboard renderiza card multi com cadeia e detalhe com breakdown | smoke | `pytest tests/test_dashboard.py::test_renders_multi_leg_card -x` | Wave 0 (extensao) |
| D-19 | Email consolidado multi tem cadeia + total + breakdown por trecho | integration | `pytest tests/test_multi_leg_email.py::test_consolidated_multi_has_chain_and_total -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `.venv/Scripts/python.exe -m pytest tests/test_multi_leg_*.py -x -q` (suite focada, < 5s)
- **Per wave merge:** `.venv/Scripts/python.exe -m pytest -q` (full suite; estimado ~30s baseado em ~40 arquivos de teste)
- **Phase gate:** Full suite green antes de `/gsd:verify-work`; verificar `alembic upgrade head` + `alembic downgrade -1 && alembic upgrade head` (migration reversivel).

### Wave 0 Gaps

- [ ] `tests/test_multi_leg_model.py` — cobre MULTI-01 model, MULTI-02 validators Pydantic
- [ ] `tests/test_multi_leg_service.py` — cobre MULTI-02 chain validation, MULTI-03 produto cartesiano + cache + persistencia, MULTI-04 prediction input
- [ ] `tests/test_multi_leg_routes.py` — cobre MULTI-01 POST form
- [ ] `tests/test_multi_leg_polling.py` — cobre MULTI-04 signal integration
- [ ] `tests/test_multi_leg_email.py` — cobre D-19 render email multi
- [ ] `tests/conftest.py` — adicionar fixtures `multi_leg_group(db, test_user)` e `multi_leg_snapshot(db, multi_leg_group)`
- [ ] Framework install: **N/A** (pytest ja configurado)

## Sources

### Primary (HIGH confidence)

- `.planning/phases/36-multi-leg/36-CONTEXT.md` — Decisoes travadas D-01 a D-20
- `.planning/REQUIREMENTS.md` linhas 326-330 — MULTI-01 a MULTI-04 oficiais
- `.planning/ROADMAP.md` linhas 481-491 — Phase 36 entry + Success Criteria
- `CLAUDE.md` (raiz) — Constraints de stack, conventions, SSR puro, SDD+TDD
- `app/models.py` — Shape atual de `RouteGroup`, `FlightSnapshot` (linhas 1-100)
- `app/services/price_prediction_service.py` — Signature de `predict_action` (Phase 34)
- `app/services/polling_service.py` — Ponto de ramificacao `_poll_group` (linhas 26-80)
- `app/services/flight_search.py` — `search_flights_ex` signature (linhas 49-79)
- `app/services/signal_service.py` — constantes de janela (linhas 44-48)
- `alembic/versions/i9j0k1l2m3n4_add_affiliate_click.py` — ultima revision como `down_revision`
- `tests/conftest.py` — fixtures `db`, `test_user`, `client` ja estabelecidas
- `.planning/config.json` — `workflow.nyquist_validation: true`

### Secondary (MEDIUM confidence)

- Inferencia de `pyproject.toml` para comando pytest (arquivo truncado no read; reconferir caminho `.venv/Scripts/python.exe` em produção — pode ser `python -m pytest` direto)

### Tertiary (LOW confidence)

- Nenhum finding externo usado (domain 100% interno ao projeto)

## Metadata

**Confidence breakdown:**

- **User Constraints / Requirements:** HIGH — CONTEXT.md explicitamente travou todas as decisoes arquiteturais; nada deixado ao planner alem do elencado em "Claude's Discretion".
- **Standard Stack:** HIGH — stack ja em producao desde Phase 14; nenhuma lib nova.
- **Architecture Patterns:** HIGH — padroes inspecionados diretamente em `app/services/` e `app/models.py`.
- **Pitfalls:** MEDIUM-HIGH — Pitfall 2 (dedup) e Pitfall 4 (quota) sao riscos reais que exigem verificacao em Wave 0; os demais sao preventivos com base em leitura de codigo.
- **Code Examples:** HIGH — construidos a partir de padroes ja existentes no repo.

**Research date:** 2026-04-22
**Valid until:** ~2026-05-22 (30 dias — stack estavel, sem dependencia de terceiros volateis). Revisitar se entre pesquisa e execucao houver mudanca em `price_prediction_service`, `signal_service` ou migracao de SerpAPI para outro provider.
