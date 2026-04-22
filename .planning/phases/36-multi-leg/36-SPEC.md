# Phase 36 — Multi-Leg Trip Builder

**Milestone:** v2.3 Growth Features
**Criado:** 2026-04-22
**Status:** Spec completa, pronta pra executar
**Esforço estimado:** ~8h (2-3 sessões)
**Depende de:** Phase 32 (Cache Layer) ✓, Phase 34 (Price Prediction) ⏳ recomendado antes
**Discovery:** o usuário pediu essa feature como "grupo dentro do grupo"

---

## 1. Contexto estratégico

Hoje a Órbita só suporta **roundtrip simples** (origem → destino → origem). O usuário quer planejar:

> "Vou viajar pra Itália em junho, ficar 2 semanas, aí quero ir pra Espanha, ficar 10 dias, e depois voltar pro Brasil."

Isso não cabe no modelo atual. É um **roteiro encadeado** com:
- Múltiplos trechos sequenciais
- Cada trecho tem janela de datas própria dentro do fluxo
- O alerta dispara quando o **encadeamento total** ficar atrativo, não trecho a trecho

Essa feature transforma a Órbita de "monitor de passagem" em "planner de viagem". Diferencial competitivo forte vs Skyscanner/Google Flights que tratam multi-city como busca pontual, não como monitoramento contínuo.

---

## 2. Estado atual do projeto (cold start)

Ver `.planning/phases/34-price-prediction/34-SPEC.md` seção 2 — mesmo contexto.

Adicional pra Phase 36:
- `app/models.py` já tem `RouteGroup` com `origins`, `destinations` (listas de IATA). Phase 36 adiciona relação com trechos.
- `app/routes/route_groups.py` (CRUD atual de grupos) precisa suportar criação multi-trecho via API.
- `app/templates/dashboard/create.html` (form de novo grupo) precisa ganhar modo multi-trecho.

---

## 3. Decisões arquiteturais

### 3.1 Modelagem de dados

**Opção escolhida:** `RouteGroup` ganha flag `mode = "multi_leg"` e relacionamento 1:N com nova tabela `RouteGroupLeg`.

```python
class RouteGroup(Base):
    # existentes
    mode: Mapped[str] = mapped_column(String(20), default="normal")
    # valores possíveis: "normal", "exploracao", "multi_leg"
    # quando multi_leg, os campos origins/destinations/travel_start/end
    # são ignorados e legs são a verdade.

class RouteGroupLeg(Base):
    __tablename__ = "route_group_leg"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    route_group_id: Mapped[int] = mapped_column(ForeignKey("route_groups.id"), index=True)
    order: Mapped[int] = mapped_column(Integer)  # 0, 1, 2...
    origin: Mapped[str] = mapped_column(String(3))
    destination: Mapped[str] = mapped_column(String(3))
    window_start: Mapped[date] = mapped_column(Date)  # data mais cedo que aceita
    window_end: Mapped[date] = mapped_column(Date)    # data mais tarde que aceita
    min_stay_days: Mapped[int] = mapped_column(Integer, default=1)  # dias min no destino antes do proximo trecho
    max_stay_days: Mapped[int] = mapped_column(Integer, nullable=True)  # dias max (opcional)
    max_stops: Mapped[int | None] = mapped_column(Integer, nullable=True)

    route_group: Mapped["RouteGroup"] = relationship(back_populates="legs")
```

**Por que essa opção:**
- Não quebra grupos existentes (que são `mode="normal"`)
- Preserva toda lógica atual pro modo normal
- Cada trecho é independente pra busca de preço — reusa `flight_search.search_flights_ex`
- `order` explícito permite reordenação e garante sequência

**Alternativas descartadas:**
- Tabela única com `parent_id` self-reference: mais genérico mas mais complexo e menos claro
- JSON column com lista de legs: perde integridade referencial + queries ruins

### 3.2 Validação temporal

Pra o encadeamento fazer sentido:

```
leg[N+1].actual_departure >= leg[N].actual_return + leg[N].min_stay_days
leg[N+1].actual_departure <= leg[N].actual_return + leg[N].max_stay_days (se tiver)
```

Ou seja: o trecho seguinte tem que sair **depois** de o anterior chegar (+ mínimo de permanência).

Validação acontece em 2 momentos:
1. **Criação do grupo:** janelas de datas têm que se encadear logicamente (window_start do leg N+1 > window_end do leg N antes do min_stay).
2. **Busca de preços:** combinações inviáveis temporalmente são filtradas.

### 3.3 Busca e sinal

**Preço total = soma dos trechos.**

Cada trecho busca no `route_cache`/SerpAPI o menor preço dentro da sua janela, **respeitando a data do trecho anterior** (data de saída do leg N+1 nunca antes de `leg[N].actual_return + min_stay`).

Algoritmo:
```
pra cada combinação (data_leg_0, data_leg_1, data_leg_2, ...):
    se combinação temporalmente válida:
        preço_total = sum(preço_de_cada_trecho)
        registrar como candidato

top_cheapest = min(candidatos, key=preço_total)
gravar FlightSnapshot com preço total e airline="MULTI" (flag)
```

**Sinal (Phase 34):** aplicado sobre o **preço total do encadeamento**, não trecho a trecho. Se o total está historicamente baixo, `COMPRE` dispara.

**Comissão afiliada:** redirect manda pro Aviasales com **multi-city flag** (formato `AR?from=GRU&to=FCO&...&legs=FCO:MAD:...`). Documentar no `affiliate_links.py`.

### 3.4 UI

#### Form de criação (3 modos)

Hoje `/groups/create` tem form simples. Ganha toggle no topo:
- `●` Roundtrip simples (default, não muda nada)
- `○` Multi-trecho

No modo multi-trecho, aparece construtor dinâmico:

```
┌─────────────────────────────────────────┐
│ Nome do roteiro: [Europa 2026]          │
│                                          │
│ ── Trecho 01 ──────────────────────────  │
│ De: [GRU] Para: [FCO]                   │
│ Janela: [01/06/2026] a [15/06/2026]     │
│ Ficar no destino: [10] a [__] dias      │
│                                          │
│ ── Trecho 02 ──────────────────────────  │
│ De: [FCO] Para: [MAD]                   │
│ Janela: (calculado automatico)           │
│ Ficar no destino: [7] a [__] dias       │
│                                          │
│ ── Trecho 03 ──────────────────────────  │
│ De: [MAD] Para: [GRU]                   │
│ Janela: (calculado automatico)           │
│                                          │
│ [+ Adicionar trecho]                    │
│                                          │
│ [Criar roteiro]                          │
└─────────────────────────────────────────┘
```

Mínimo 2 trechos (ida e volta de rota simples = modo normal). Máximo sugerido 5 trechos.

#### Card do dashboard

Dashboard card de grupo multi-trecho mostra diferente:
```
┌─────────────────────────────────────────┐
│ Europa 2026    MULTI                    │
│ GRU → FCO → MAD → GRU                   │
│ 3 trechos · jun-jul 2026                │
│                                          │
│ R$ 9.250,00 total                       │
│ -12% vs média 90d do encadeamento       │
│                                          │
│ ● AGUARDE                               │
│ Janela ótima começa em 12 dias          │
└─────────────────────────────────────────┘
```

#### Página de detalhe

Quando usuário clica, ver cada trecho com preço individual + total na hora.

---

## 4. Requirements (do milestone v2.3)

- **MULTI-01**: Usuário pode criar grupo-pai com N trechos sequenciais, cada trecho com origin, destination, janela de datas e stay min/max.
- **MULTI-02**: Sistema valida encadeamento temporal (saída N+1 >= chegada N + min_stay; e ≤ chegada N + max_stay se definido).
- **MULTI-03**: Sistema busca preços de cada trecho no cache/SerpAPI e calcula preço total do roteiro.
- **MULTI-04**: Sinal de compra aplicado sobre o preço total do encadeamento, não trecho a trecho.

---

## 5. Success criteria

1. Migration Alembic cria `route_group_leg` com FK pra `route_groups.id` + constraint de unicidade (route_group_id, order).
2. API `POST /api/v1/route-groups/` aceita payload com `mode="multi_leg"` + array `legs[]`.
3. Form web em `/groups/create` tem toggle e suporta criação com até 5 trechos.
4. `polling_service` respeita `mode="multi_leg"` e busca preços com encadeamento temporal.
5. Snapshot de grupo multi-trecho armazena preço total + breakdown (JSON de trechos individuais, por ex em coluna `details: JSON`).
6. Dashboard card mostra layout multi com rotas encadeadas e preço total.
7. Email consolidado funciona pra multi (rotas encadeadas + preço total + justificativa).
8. Testes: 20+ testes cobrindo modelo, validação temporal, busca, sinal, UI renderização.
9. Suite inteira continua verde.

---

## 6. Plano de implementação (3 plans)

### 6.1 Plan 1 — Modelo + migration + validação (RED + GREEN, ~2h)

Arquivos:
- `app/models.py` — adicionar `RouteGroupLeg` + relationship em `RouteGroup`
- `alembic/versions/j0k1l2m3n4o5_add_route_group_leg.py` (new)
- `app/services/multi_leg_service.py` (new) — validação temporal pura
- `tests/test_multi_leg_model.py` (new)
- `tests/test_multi_leg_validation.py` (new)

Testes:
- `test_route_group_leg_persist`
- `test_route_group_has_legs_relationship`
- `test_validation_leg_order_unique`
- `test_validation_temporal_chain_valid`
- `test_validation_temporal_chain_invalid_overlap`
- `test_validation_min_stay_respected`
- `test_validation_max_stay_exceeded`
- `test_validation_at_least_2_legs_required`
- `test_validation_iata_codes_uppercased`

### 6.2 Plan 2 — Busca + polling + sinal (RED + GREEN, ~3h)

Arquivos:
- `app/services/multi_leg_service.py` — adicionar `search_multi_leg_prices(db, group)`
- `app/services/polling_service.py` — branch `if group.mode == "multi_leg": multi_leg_service.search(...)`
- `app/services/signal_service.py` — sinal sobre total, não trecho
- `app/services/price_prediction_service.py` (criado na Phase 34) — aceita preço total como input
- `app/models.py` — `FlightSnapshot` ganha `details: JSON` opcional com breakdown (ou criar `MultiLegSnapshot` separado)
- `alembic/versions/k1l2m3n4o5p6_add_multi_leg_snapshot.py` ou migration adicionando coluna details
- `tests/test_multi_leg_search.py`
- `tests/test_multi_leg_polling.py`

Decisão: **usar `FlightSnapshot` com `airline="MULTI"` e adicionar coluna `details: JSON`** em vez de tabela separada. Reduz complexidade de query. O JSON contém:
```json
{
    "total_price": 9250.00,
    "legs": [
        {"order": 0, "origin": "GRU", "destination": "FCO", "date": "2026-06-01", "price": 3200.00, "airline": "LA"},
        {"order": 1, "origin": "FCO", "destination": "MAD", "date": "2026-06-15", "price": 180.00, "airline": "IB"},
        {"order": 2, "origin": "MAD", "destination": "GRU", "date": "2026-07-05", "price": 2900.00, "airline": "TP"}
    ]
}
```

### 6.3 Plan 3 — UI + API + email (GREEN, ~2-3h)

Arquivos:
- `app/routes/route_groups.py` — POST aceita `legs: list[dict]` payload
- `app/schemas.py` — schemas pydantic pra validar payload
- `app/templates/dashboard/create.html` — toggle + construtor dinâmico (JS mínimo puro pra adicionar/remover linhas)
- `app/templates/dashboard/edit.html` — suporte a editar legs
- `app/templates/dashboard/index.html` — card renderiza multi diferente
- `app/templates/dashboard/detail.html` — mostra breakdown de trechos
- `app/services/dashboard_service.py` — `get_groups_with_summary` retorna `legs` e `total_price` pra multi
- `app/services/alert_service.py` — `_render_consolidated_html/plain` branch pra multi
- `tests/test_multi_leg_api.py`
- `tests/test_multi_leg_ui.py`

### 6.4 Plan 4 (opcional) — Affiliate multi-city link (~30min)

Em `app/services/affiliate_links.py`, adicionar `build_aviasales_multi_city_url(legs, marker)` que gera URL compatível com multi-city do Aviasales.

Formato investigado (documentar se mudou):
```
https://www.aviasales.com/search/GRU0106FCO15MAD0507GRU1?marker=714304
```
Cada par `{IATA}{DDMM}` é um trecho. O último tem o PAX no final.

---

## 7. Questões em aberto (decidir na execução)

1. **Máximo de trechos.** Sugerido 5. Acima disso, UX fica complexa e busca fica lenta.
2. **Passageiros por trecho.** Hoje é 1 valor no grupo. Pra multi, manter 1 passageiro pra todos os trechos (decisão simples). Em v futuro, permitir variar (ex: "vou com 2 até Roma, volto sozinho").
3. **Companhia diferente por trecho?** Natural (Gol BR→Europa + RyanAir Europa-Europa + TAP Europa→BR). Sistema suporta porque cada trecho busca independente. Bagagem despachada vira problema do usuário resolver.
4. **Fallback se um trecho não tem cache.** Se MAD→GRU não está no cache Travelpayouts, pula pra SerpAPI on-demand (consome quota). Logar em `cache_lookup_log`.
5. **Exibir múltiplos "top 3 roteiros"?** No email, mostrar só o mais barato. Em detalhe de grupo, pode listar top 3 combinações de datas.
6. **Janela auto-calculada na UI.** Quando usuário preenche trecho 2, sua janela é derivada automático de `trecho_1.window_end + trecho_1.min_stay_days` até `+ max_stay_days`. Permitir override manual.

---

## 8. Copy pt-BR

- Toggle do form: `Roundtrip simples` / `Multi-trecho`
- Legenda do modo: "Encadeie vários voos numa viagem só (ex: BR → Itália → Espanha → BR)."
- Badge do card: `MULTI` (mono, cyan)
- Dashboard breakdown: `GRU → FCO → MAD → GRU`
- Label do preço: "Preço total do roteiro"
- Email subject: "Órbita multi: [Nome] R$ X,XX (3 trechos)"

---

## 9. Não fazer (out of scope)

- ❌ Multi-city search em tempo real (Aviasales Flight Search API gated) — só cache
- ❌ Stopover pago intencional (comprar leg 1 + leg 2 separadas com overnight em hub) — assume usuário resolve
- ❌ Open-jaw (chegar em uma cidade, voltar de outra) — modelo já suporta se usuário desenhar corretamente. Só não destaca.
- ❌ Combinar milhas + dinheiro — fora do radar
- ❌ Otimização automática de "melhor rota" (ex: sugerir hub ideal) — feature v3+
- ❌ Permitir 0 dias de stay (conexão) — força mín 1

---

## 10. Ordem de execução recomendada

1. `/gsd:discuss-phase 36` — 15-30min conversando com usuário pra confirmar decisões abertas da seção 7
2. `/gsd:plan-phase 36` — planner detalha os 3-4 plans
3. Executar Plan 1 (modelo + validação) — testar bem, é fundação
4. Executar Plan 2 (busca + sinal) — parte mais cara tecnicamente
5. Executar Plan 3 (UI + API) — parte mais trabalhosa em volume
6. Plan 4 (affiliate) se sobrar tempo
7. Commit atomic por plan
8. Deploy final quando tudo verde

---

## 11. Como começar a próxima sessão (se for pular direto pra essa fase)

Pré-requisito recomendado: executar Phase 34 antes. Mas Phase 36 pode rodar sem Phase 34 (recomendação fica desativada pra grupos multi até 34 shipar).

```
/gsd:discuss-phase 36
```

Se quiser pular o discuss e já saber as respostas da seção 7:
```
/gsd:plan-phase 36
```

Contexto pra dar pro planner no prompt:
- Modelo com `RouteGroupLeg` separado, FK pra `route_groups`
- Busca via `FlightSnapshot` com `airline="MULTI"` + coluna `details: JSON`
- Sinal no total, não no trecho
- Toggle na UI de create, max 5 trechos
- Reusa `price_prediction_service.predict_action` da Phase 34

Rodar suite antes de cada commit: `.venv/Scripts/python.exe -m pytest -q`
