# Phase 34 — Price Prediction Engine

**Milestone:** v2.3 Growth Features
**Criado:** 2026-04-22
**Status:** Pronto pra executar na próxima sessão
**Esforço estimado:** ~3h (1 sessão)
**Depende de:** Phase 32 (Cache Layer) — já shipped ✓

---

## 1. Contexto estratégico

A Órbita hoje mostra **o preço atual** e **quanto ele está vs média histórica**. Faltam dar o último passo: **recomendação acionável**. Em vez de o usuário ter que pensar "R$ 3.120 é -23% da média, isso é bom? devo comprar?", a Órbita fala explicitamente:

- **Compre até 15/06** — preço caiu e histórico sugere alta depois dessa data
- **Aguarde ~2 semanas** — janela ótima ainda não chegou (>90 dias antes do voo)
- **Monitorar** — nada de anormal no preço agora

Essa feature fecha o posicionamento de "radar ativo" da landing. Hoje o produto *mostra*, com Phase 34 o produto *recomenda*.

**Regra de negócio-chave:** **sem ML**. Regras determinísticas baseadas em:
1. Janela ótima temporal (50-90 dias antes do voo é historicamente a faixa mais barata em rotas BR)
2. Delta vs mediana 90 dias (-10% ou mais = oportunidade)
3. Volatilidade da rota (desvio padrão dos preços 90d)

ML fica pra quando tivermos 6+ meses de dados reais e validação retrospectiva passar de 60% hit rate.

---

## 2. Estado atual do projeto (cold start para próximo Claude)

- **Nome do produto:** Órbita (rebrand recente de "Flight Monitor")
- **URL produção:** https://orbita-flights.fly.dev
- **Hospedagem:** Fly.io GRU, sempre ligado
- **Banco:** PostgreSQL Neon (prod), SQLite in-memory (testes)
- **Testes:** 364 passando, `.venv/Scripts/python.exe -m pytest -q`
- **Deploy:** `fly deploy` (o usuário executa, não o agent)
- **Fontes de preço:** Travelpayouts Data API (primária, cache 4x/dia) + SerpAPI (fallback on-demand)
- **Monetização:** affiliate Aviasales (marker 714304) via `/comprar/{O}-{D}` tracked redirect
- **Acentuação pt-BR obrigatória** em texto visível (ver CLAUDE.md)
- **Sem ML, sem JS framework** (Jinja2 SSR puro)
- **Convenção commits:** Conventional Commits, sem emoji, atomic
- **Workflow:** SDD + TDD (spec → RED → GREEN → REFACTOR)

### Arquivos importantes pra Phase 34

| Arquivo | Papel |
|---|---|
| `app/models.py` | SQLAlchemy models. FlightSnapshot tem o histórico bruto. |
| `app/services/dashboard_service.py` | Já tem `get_price_history`, `format_price_brl`. |
| `app/services/snapshot_service.py` | `get_historical_price_context` retorna média/min/max 90d. |
| `app/services/signal_service.py` | Detecta sinais de compra atuais. Phase 34 expande. |
| `app/services/alert_service.py` | Emails consolidados. Phase 34 adiciona recomendação no topo. |
| `app/templates/dashboard/index.html` | Cards dos grupos. Phase 34 adiciona banner de recomendação. |
| `app/templates/public/route.html` | Página SEO pública. Phase 34 pode adicionar recomendação opcional. |
| `scripts/` | Onde vai o script de backtest. |

---

## 3. Requirements (do milestone v2.3)

- **PRED-01**: Dashboard exibe recomendação por grupo em uma de três classes: `COMPRE`, `AGUARDE`, `MONITORAR`.
- **PRED-02**: Cada recomendação acompanha justificativa de 1 frase combinando janela ótima, delta vs mediana 90d e volatilidade da rota.
- **PRED-03**: Sistema inclui script `scripts/backtest_predictions.py` que mede hit rate retrospectivo por classe contra o histórico do `route_cache` + `FlightSnapshot`.
- **PRED-04**: Email consolidado exibe recomendação no topo do corpo (acima do preço atual).

---

## 4. Success criteria (o que precisa estar true pra fase fechar)

1. Função `predict_action(snapshot, history, days_to_departure) -> Recommendation` determinística, pura, testável (sem I/O).
2. Dashboard (logado) mostra badge colorido por grupo: verde `COMPRE`, amarelo `AGUARDE`, cinza `MONITORAR`, com tooltip/subtítulo explicando a razão.
3. Email consolidado tem card destacado no topo com a recomendação + frase de justificativa.
4. Script `python scripts/backtest_predictions.py` roda, imprime hit rate por classe em formato tabelado.
5. Testes: ≥15 testes cobrindo as 3 classes + edge cases (sem histórico, 1 snapshot, rota volátil, rota estável).
6. Suite completa (364+) continua verde.

---

## 5. Regras determinísticas (heurísticas canônicas)

### Inputs
- `current_price: float`
- `median_90d: float`
- `stddev_90d: float` (desvio padrão dos preços dos últimos 90d)
- `days_to_departure: int` (quantos dias até a partida)
- `snapshot_count: int` (quantos snapshots a gente tem)

### Thresholds

```python
OPTIMAL_WINDOW_MIN = 35   # dias antes do voo onde histórico indica "comprar"
OPTIMAL_WINDOW_MAX = 95
LOW_PRICE_PCT = -10.0     # preço ≤ -10% da mediana → sinal de queda
HIGH_PRICE_PCT = 10.0     # preço ≥ +10% da mediana → caro
MIN_SNAPSHOTS = 15        # abaixo disso, dados insuficientes → MONITORAR
```

### Decisão (em ordem)

```
1. Se snapshot_count < MIN_SNAPSHOTS:
   -> MONITORAR, motivo="dados insuficientes (precisa de >=15 leituras)"

2. Se current_price <= median_90d * (1 + LOW_PRICE_PCT/100)
   E OPTIMAL_WINDOW_MIN <= days_to_departure <= OPTIMAL_WINDOW_MAX:
   -> COMPRE, motivo="preço X% abaixo da mediana E janela ótima"

3. Se days_to_departure > OPTIMAL_WINDOW_MAX:
   -> AGUARDE ate (departure_date - OPTIMAL_WINDOW_MAX) dias,
      motivo="janela ótima começa em X dias"

4. Se days_to_departure < OPTIMAL_WINDOW_MIN:
   E current_price <= median_90d:
   -> COMPRE, motivo="última chance, preço ainda não está caro"

5. Se current_price >= median_90d * (1 + HIGH_PRICE_PCT/100):
   -> MONITORAR, motivo="preço X% acima da média, aguardando queda"

6. Else:
   -> MONITORAR, motivo="preço em linha com histórico (±10%)"
```

### Retorno

```python
@dataclass(frozen=True)
class Recommendation:
    action: Literal["COMPRE", "AGUARDE", "MONITORAR"]
    reason: str           # frase curta em pt-BR
    confidence: float     # 0-1, baseada em snapshot_count / stddev
    deadline: date | None # pra COMPRE: até quando o sinal vale
                          # pra AGUARDE: até quando esperar
```

---

## 6. Plano de implementação (sessão próxima)

### 6.1 Plan 1 — Service `price_prediction_service.py` (RED + GREEN)

Arquivo novo: `app/services/price_prediction_service.py`

Testes novos: `tests/test_price_prediction_service.py`

Cobertura esperada:
- `test_compre_preco_baixo_janela_otima`
- `test_compre_ultima_chance_perto_do_voo`
- `test_aguarde_janela_ainda_nao_chegou`
- `test_monitorar_preco_caro`
- `test_monitorar_preco_normal`
- `test_monitorar_dados_insuficientes`
- `test_confidence_baixa_com_pouco_historico`
- `test_confidence_alta_com_historico_robusto`
- `test_deadline_compre_calculado_corretamente`
- `test_deadline_aguarde_calculado_corretamente`
- `test_volatilidade_alta_reduz_confidence`

Estrutura do service:

```python
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal

@dataclass(frozen=True)
class Recommendation:
    action: Literal["COMPRE", "AGUARDE", "MONITORAR"]
    reason: str
    confidence: float
    deadline: date | None


OPTIMAL_WINDOW_MIN = 35
OPTIMAL_WINDOW_MAX = 95
LOW_PRICE_PCT = -10.0
HIGH_PRICE_PCT = 10.0
MIN_SNAPSHOTS = 15


def predict_action(
    current_price: float,
    median_90d: float | None,
    stddev_90d: float | None,
    days_to_departure: int,
    snapshot_count: int,
    departure_date: date,
) -> Recommendation:
    ...
```

### 6.2 Plan 2 — Integração no dashboard (GREEN)

Em `app/services/dashboard_service.py` (`get_groups_with_summary`):
- Depois de pegar o cheapest snapshot, chamar `predict_action`
- Adicionar `recommendation: Recommendation` em cada item do retorno

Em `app/templates/dashboard/index.html`:
- Dentro do card, abaixo do preço, renderizar badge:
  ```html
  {% if item.recommendation %}
  <div class="recommendation recommendation-{{ item.recommendation.action|lower }}">
      <div class="rec-action">{{ item.recommendation.action }}</div>
      <div class="rec-reason">{{ item.recommendation.reason }}</div>
      {% if item.recommendation.deadline %}
      <div class="rec-deadline">Até {{ format_date_br(item.recommendation.deadline) }}</div>
      {% endif %}
  </div>
  {% endif %}
  ```
- CSS com tokens Órbita existentes (`--success-*`, `--warning-*`, `--text-*`)
- COMPRE = background success-bg + border success-500
- AGUARDE = background warning-bg + border warning-500
- MONITORAR = background bg-2 + border border-2

Testes novos em `tests/test_dashboard.py`:
- `test_dashboard_mostra_recommendation_compre`
- `test_dashboard_mostra_recommendation_aguarde`
- `test_dashboard_mostra_recommendation_monitorar`

### 6.3 Plan 3 — Integração no email (GREEN)

Em `app/services/alert_service.py` (`_render_consolidated_html` e `_render_consolidated_plain`):

- Logo após o header (antes do `parts.append('<div style="border:1px solid #e5e7eb...')`, inserir card de recomendação em destaque
- Plain text: primeira linha após "MELHOR PREÇO" vira "RECOMENDAÇÃO: [ACTION] — [reason]"

Testes em `tests/test_alert_service.py`:
- `test_consolidated_email_exibe_recomendacao_compre_no_topo`
- `test_consolidated_email_plain_tem_recomendacao_primeira_linha`

### 6.4 Plan 4 — Script de backtest (GREEN)

Arquivo novo: `scripts/backtest_predictions.py`

Lógica:
1. Pra cada FlightSnapshot com `collected_at` entre 30 e 180 dias atrás:
   - Pega a "história disponível naquele momento" (snapshots da mesma rota anteriores a ele)
   - Calcula `predict_action(...)` com esses dados de passado
   - Compara com o preço real 7, 14, 30 dias depois do snapshot
2. Classifica acerto:
   - `COMPRE` = acerto se preço subiu ≥5% nos 30 dias seguintes
   - `AGUARDE` = acerto se preço caiu ≥5% dentro do prazo do deadline
   - `MONITORAR` = neutro

Output:
```
Phase 34 Backtest — 2026-04-22
Período analisado: 180 dias
Total snapshots avaliados: 1247

COMPRE:     412 casos  | 287 acertos (69.7%) ✓ acima meta 60%
AGUARDE:    198 casos  | 132 acertos (66.7%) ✓
MONITORAR:  637 casos  | neutro (n/a)

Recomenda promoção das regras atuais pra UI.
```

Teste: `tests/test_backtest_predictions.py` com fixture de dados controlados.

---

## 7. UI spec do badge de recomendação

Desenho conceitual (ASCII):

```
┌─────────────────────────────────────┐
│ GRU → LIS            REC              │
│ R$ 3.120                              │
│ -18% vs média                         │
│                                       │
│ ┌───────────────────────────────────┐ │
│ │ ● COMPRE                          │ │
│ │ Preço 18% abaixo da média E       │ │
│ │ janela ótima                      │ │
│ │ Até 15/06/2026                    │ │
│ └───────────────────────────────────┘ │
└─────────────────────────────────────┘
```

Estilo (CSS):
```css
.recommendation {
    margin-top: var(--sp-3);
    padding: var(--sp-3) var(--sp-4);
    border-radius: var(--r-md);
    border: 1px solid;
}
.recommendation-compre {
    background: var(--success-bg);
    border-color: rgba(16,185,129,0.3);
    color: var(--success-400);
}
.recommendation-aguarde {
    background: var(--warning-bg);
    border-color: rgba(245,158,11,0.3);
    color: var(--warning-400);
}
.recommendation-monitorar {
    background: var(--bg-2);
    border-color: var(--border-2);
    color: var(--text-2);
}
.rec-action {
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-bottom: 4px;
}
.rec-reason {
    font-size: 13px;
    color: var(--text-1);
    line-height: 1.4;
}
.rec-deadline {
    font-size: 11px;
    font-family: var(--font-mono);
    margin-top: 4px;
    opacity: 0.8;
}
```

---

## 8. Copy pt-BR

Frases-template pros `reason`:

- **COMPRE (preço baixo + janela ótima):** "Preço {pct}% abaixo da média e dentro da janela ótima."
- **COMPRE (última chance):** "Última janela antes da partida. Preço ainda razoável."
- **AGUARDE:** "Janela ótima começa em {days} dias. Sem urgência ainda."
- **MONITORAR (caro):** "Preço {pct}% acima da média. Aguardando queda."
- **MONITORAR (normal):** "Preço em linha com o histórico. Sem mudança significativa."
- **MONITORAR (sem dados):** "Ainda reunindo histórico (menos de 15 leituras)."

---

## 9. Não fazer (out of scope)

- ❌ Machine Learning (ARIMA, Prophet, LSTM) — vira Phase 50+
- ❌ Previsão de preço futuro (ex: "vai custar X em 10 dias") — risco de errar feio
- ❌ Integração com calendário do usuário (Google Calendar) — futuro
- ❌ Push notification — futuro
- ❌ Alertas diferentes de `COMPRE/AGUARDE/MONITORAR` (ex: "urgente", "flash") — começa simples
- ❌ Customização de thresholds por usuário — futuro

---

## 10. Como começar a próxima sessão

```
/gsd:plan-phase 34
```

Ou, se quiser pular o planner e ir direto:
1. Ler esse SPEC inteiro
2. Criar `app/services/price_prediction_service.py` com a função `predict_action`
3. Criar `tests/test_price_prediction_service.py` com os 11 casos listados em 6.1
4. Integrar no dashboard (6.2)
5. Integrar no email (6.3)
6. Escrever backtest (6.4)
7. Commit + push + pedir pro usuário rodar `fly deploy`

Rodar suite antes de cada commit: `.venv/Scripts/python.exe -m pytest -q`

---

## 11. Perguntas que precisam de confirmação (se surgir dúvida)

- **Thresholds são chutes iniciais.** Ajustar depois que backtest rodar em dados reais. Não tentar acertar de primeira.
- **Cor do badge MONITORAR:** cinza (neutro) ou azul (info)? Escolhi cinza porque é o default de "nada acontecendo".
- **Recommendation aparece na página pública `/rotas/{O}-{D}`?** Não nesta fase. É valor agregado exclusivo de usuário logado.
