# Requirements: Flight Monitor

**Defined:** 2026-03-24
**Core Value:** Detectar o momento certo de comprar uma passagem antes que o preço suba, usando dados de inventário reais (booking classes via Amadeus API) que nenhum sistema consumer expõe.

## v1 Requirements

### Route Groups (Grupos de Rota)

- [x] **ROUTE-01**: Usuário pode criar um Grupo de Rota com: nome, lista de aeroportos de origem (múltiplos códigos IATA), lista de aeroportos de destino (múltiplos códigos IATA), duração da viagem em dias, e período de viagem (mês específico ou intervalo de datas)
- [x] **ROUTE-02**: Usuário pode definir preço-alvo opcional por Grupo de Rota
- [x] **ROUTE-03**: Usuário pode ativar e desativar um Grupo de Rota sem deletar
- [x] **ROUTE-04**: Usuário pode editar um Grupo de Rota existente
- [x] **ROUTE-05**: Usuário pode deletar um Grupo de Rota
- [x] **ROUTE-06**: Sistema limita a 10 grupos ativos simultaneamente (constraint do free tier Amadeus)

### Data Collection (Coleta de Dados)

- [x] **COLL-01**: Sistema faz polling da Amadeus API a cada 6 horas para cada Grupo de Rota ativo
- [x] **COLL-02**: Por ciclo de polling, sistema encontra as 5 combinações mais baratas de (origem × destino × data_ida × data_volta) dentro do período configurado via Amadeus Flight Cheapest Date Search e Flight Offers Search
- [x] **COLL-03**: Para cada combinação encontrada, sistema captura inventário de booking classes (Y, B, M, H, Q, K, L com contagem de assentos) via Amadeus Flight Availabilities Search
- [x] **COLL-04**: Sistema captura classificação histórica do preço (LOW / MEDIUM / HIGH) via Amadeus Flight Price Analysis para cada combinação
- [x] **COLL-05**: Sistema persiste todos os dados como snapshots com timestamp no banco SQLite
- [x] **COLL-06**: Sistema trata graciosamente falhas de API (timeout, rate limit) sem crashar o scheduler

### Signal Detection (Detecção de Sinais)

- [x] **SIGN-01**: Sistema detecta sinal BALDE FECHANDO quando classe K ou Q passou de >=3 para <=1 comparado ao snapshot anterior — urgência ALTA
- [x] **SIGN-02**: Sistema detecta sinal BALDE REABERTO quando classe estava em 0 e voltou a ter assentos no snapshot atual — urgência MÁXIMA
- [x] **SIGN-03**: Sistema detecta sinal PREÇO ABAIXO DO HISTÓRICO quando Amadeus retorna LOW e preço atual está abaixo da média dos últimos 14 snapshots — urgência MÉDIA
- [x] **SIGN-04**: Sistema detecta sinal JANELA ÓTIMA quando dias restantes antes do voo entra na faixa 21-90 dias (doméstico) ou 30-120 dias (internacional) — urgência MÉDIA
- [x] **SIGN-05**: Sistema não re-alerta o mesmo sinal para a mesma rota dentro de uma janela de 12 horas (deduplicação)

### Alerts (Alertas via Gmail)

- [x] **ALRT-01**: Sistema envia email via Gmail quando sinal detectado contendo: nome do grupo, rota específica (origem→destino + datas), preço atual, contexto histórico e urgência
- [x] **ALRT-02**: Email contém link de silenciar que pausa alertas daquele grupo por 24 horas ao ser clicado
- [x] **ALRT-03**: Dashboard web exibe status de todos os grupos ativos e melhor preço atual de cada um (substitui o /status do bot)

### Web Dashboard

- [x] **DASH-01**: Dashboard lista todos os Grupos de Rota com: melhor preço atual, rota mais barata encontrada e indicador visual de sinal ativo (nenhum / médio / alto / máximo)
- [x] **DASH-02**: Clicando em um Grupo de Rota abre histórico de preço das últimas 2 semanas em gráfico de linha
- [x] **DASH-03**: Dashboard tem formulário para criar novo Grupo de Rota
- [x] **DASH-04**: Dashboard permite editar e desativar Grupo de Rota existente
- [x] **DASH-05**: Interface funciona em navegador mobile (layout responsivo simples)

### Infrastructure (Infraestrutura)

- [x] **INFRA-01**: Aplicação inicia com um único comando (`python main.py` ou `uvicorn app.main:app`)
- [x] **INFRA-02**: Configuração via arquivo `.env` (Amadeus API keys, Telegram bot token, Telegram chat ID)
- [x] **INFRA-03**: Banco SQLite é criado automaticamente na primeira execução com todas as tabelas necessárias

---

## v2 Requirements

### Extended Sources

- **SRC-01**: Integração com Duffel API como fonte secundária NDC para comparar preços exclusivos não disponíveis no GDS
- **SRC-02**: Integração com SerpApi Google Flights para usar sinal de previsão "prices unlikely to drop" como confirmação

### Extended Monitoring

- **MON-01**: Suporte a voos de ida apenas (one-way), além de roundtrip
- **MON-02**: Histórico de variação por booking class individual (gráfico Y, B, M... separados)
- **MON-03**: Cálculo automático de custo total incluindo bagagem estimada por rota

### Extended Interface

- **UI-01**: Autocomplete de código IATA ao digitar aeroportos no formulário (busca por nome da cidade)
- **UI-02**: Exportar histórico de alertas em CSV
- **UI-03**: Guia de deploy passo a passo para Fly.io integrado na interface

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| Compra de passagens | Apenas monitoramento — integração com booking adiciona complexidade e responsabilidade |
| Múltiplos usuários / autenticação | Ferramenta pessoal; adicionar auth não agrega valor agora |
| Web scraping | Somente APIs oficiais; scraping viola ToS e é frágil |
| Hotéis, carros, multimodal | Foco em voos — expansão dilui o core value |
| App mobile nativo | Interface web responsiva é suficiente para o uso |
| Telegram / WhatsApp | Gmail resolve para uso pessoal de baixo volume; Telegram silenciado pelo usuário |
| Multi-tenant / SaaS | Escopo pessoal — virar SaaS é decisão de negócio futura |
| Real-time streaming de preços | Polling a cada 6h é suficiente; streaming aumentaria custo de API |

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| ROUTE-01 | Phase 1 | Complete |
| ROUTE-02 | Phase 1 | Complete |
| ROUTE-03 | Phase 1 | Complete |
| ROUTE-04 | Phase 1 | Complete |
| ROUTE-05 | Phase 1 | Complete |
| ROUTE-06 | Phase 1 | Complete |
| INFRA-01 | Phase 1 | Complete |
| INFRA-02 | Phase 1 | Complete |
| INFRA-03 | Phase 1 | Complete |
| COLL-01 | Phase 2 | Complete |
| COLL-02 | Phase 2 | Complete |
| COLL-03 | Phase 2 | Complete |
| COLL-04 | Phase 2 | Complete |
| COLL-05 | Phase 2 | Complete |
| COLL-06 | Phase 2 | Complete |
| SIGN-01 | Phase 3 | Complete |
| SIGN-02 | Phase 3 | Complete |
| SIGN-03 | Phase 3 | Complete |
| SIGN-04 | Phase 3 | Complete |
| SIGN-05 | Phase 3 | Complete |
| ALRT-01 | Phase 4 | Complete |
| ALRT-02 | Phase 4 | Complete |
| ALRT-03 | Phase 4 | Complete |
| DASH-01 | Phase 5 | Complete |
| DASH-02 | Phase 5 | Complete |
| DASH-03 | Phase 5 | Complete |
| DASH-04 | Phase 5 | Complete |
| DASH-05 | Phase 5 | Complete |

**Coverage:**
- v1 requirements: 28 total
- Mapped to phases: 28
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-24*
*Last updated: 2026-03-24 after alert channel change (Telegram → Gmail)*
