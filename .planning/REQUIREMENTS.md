# Requirements: Flight Monitor

**Defined:** 2026-03-24
**Core Value:** Detectar o momento certo de comprar uma passagem antes que o preco suba, usando dados de inventario reais (booking classes via Amadeus API) que nenhum sistema consumer expoe.

## v1 Requirements

### Route Groups (Grupos de Rota)

- [x] **ROUTE-01**: Usuario pode criar um Grupo de Rota com: nome, lista de aeroportos de origem (multiplos codigos IATA), lista de aeroportos de destino (multiplos codigos IATA), duracao da viagem em dias, e periodo de viagem (mes especifico ou intervalo de datas)
- [x] **ROUTE-02**: Usuario pode definir preco-alvo opcional por Grupo de Rota
- [x] **ROUTE-03**: Usuario pode ativar e desativar um Grupo de Rota sem deletar
- [x] **ROUTE-04**: Usuario pode editar um Grupo de Rota existente
- [x] **ROUTE-05**: Usuario pode deletar um Grupo de Rota
- [x] **ROUTE-06**: Sistema limita a 10 grupos ativos simultaneamente (constraint do free tier Amadeus)

### Data Collection (Coleta de Dados)

- [x] **COLL-01**: Sistema faz polling da Amadeus API a cada 6 horas para cada Grupo de Rota ativo
- [x] **COLL-02**: Por ciclo de polling, sistema encontra as 5 combinacoes mais baratas de (origem x destino x data_ida x data_volta) dentro do periodo configurado via Amadeus Flight Cheapest Date Search e Flight Offers Search
- [x] **COLL-03**: Para cada combinacao encontrada, sistema captura inventario de booking classes (Y, B, M, H, Q, K, L com contagem de assentos) via Amadeus Flight Availabilities Search
- [x] **COLL-04**: Sistema captura classificacao historica do preco (LOW / MEDIUM / HIGH) via Amadeus Flight Price Analysis para cada combinacao
- [x] **COLL-05**: Sistema persiste todos os dados como snapshots com timestamp no banco SQLite
- [x] **COLL-06**: Sistema trata graciosamente falhas de API (timeout, rate limit) sem crashar o scheduler

### Signal Detection (Deteccao de Sinais)

- [x] **SIGN-01**: Sistema detecta sinal BALDE FECHANDO quando classe K ou Q passou de >=3 para <=1 comparado ao snapshot anterior - urgencia ALTA
- [x] **SIGN-02**: Sistema detecta sinal BALDE REABERTO quando classe estava em 0 e voltou a ter assentos no snapshot atual - urgencia MAXIMA
- [x] **SIGN-03**: Sistema detecta sinal PRECO ABAIXO DO HISTORICO quando Amadeus retorna LOW e preco atual esta abaixo da media dos ultimos 14 snapshots - urgencia MEDIA
- [x] **SIGN-04**: Sistema detecta sinal JANELA OTIMA quando dias restantes antes do voo entra na faixa 21-90 dias (domestico) ou 30-120 dias (internacional) - urgencia MEDIA
- [x] **SIGN-05**: Sistema nao re-alerta o mesmo sinal para a mesma rota dentro de uma janela de 12 horas (deduplicacao)

### Alerts (Alertas via Gmail)

- [x] **ALRT-01**: Sistema envia email via Gmail quando sinal detectado contendo: nome do grupo, rota especifica (origem>destino + datas), preco atual, contexto historico e urgencia
- [x] **ALRT-02**: Email contem link de silenciar que pausa alertas daquele grupo por 24 horas ao ser clicado
- [x] **ALRT-03**: Dashboard web exibe status de todos os grupos ativos e melhor preco atual de cada um (substitui o /status do bot)

### Web Dashboard

- [x] **DASH-01**: Dashboard lista todos os Grupos de Rota com: melhor preco atual, rota mais barata encontrada e indicador visual de sinal ativo (nenhum / medio / alto / maximo)
- [x] **DASH-02**: Clicando em um Grupo de Rota abre historico de preco das ultimas 2 semanas em grafico de linha
- [x] **DASH-03**: Dashboard tem formulario para criar novo Grupo de Rota
- [x] **DASH-04**: Dashboard permite editar e desativar Grupo de Rota existente
- [x] **DASH-05**: Interface funciona em navegador mobile (layout responsivo simples)

### Infrastructure (Infraestrutura)

- [x] **INFRA-01**: Aplicacao inicia com um unico comando (`python main.py` ou `uvicorn app.main:app`)
- [x] **INFRA-02**: Configuracao via arquivo `.env` (Amadeus API keys, Telegram bot token, Telegram chat ID)
- [x] **INFRA-03**: Banco SQLite e criado automaticamente na primeira execucao com todas as tabelas necessarias

---

## v1.1 Requirements

### Email Consolidado

- [ ] **EMAIL-01**: Sistema envia 1 email por grupo (nao por sinal) contendo: rota mais barata, preco, companhia, datas ida/volta, e resumo das demais rotas monitoradas
- [ ] **EMAIL-02**: Email mostra as melhores datas para viajar dentro do periodo configurado
- [ ] **EMAIL-03**: Datas no email usam formato brasileiro dd/mm/aaaa

### Dashboard UI

- [ ] **UI-01**: Tela inicial mostra area de resumo no topo com: total de grupos ativos, menor preco encontrado e horario do proximo polling
- [ ] **UI-02**: Grupos sao exibidos como cards com borda colorida por classificacao (verde=LOW, amarelo=MEDIUM, vermelho=HIGH, cinza=sem dados)
- [ ] **UI-03**: Cada card mostra: nome, rotas, preco mais barato em destaque, companhia, datas e badge de sinal
- [ ] **UI-04**: Estado vazio (sem grupos) mostra mensagem amigavel com botao de criar grupo
- [ ] **UI-05**: Datas no dashboard usam formato brasileiro dd/mm/aaaa

### Feedback e Erros

- [ ] **UX-01**: Mensagem de confirmacao aparece apos criar, editar ou desativar grupo
- [ ] **UX-02**: Pagina de erro amigavel ao inves de "Internal Server Error" generico

### Correcoes

- [ ] **FIX-01**: Polling nao salva snapshots duplicados (mesmo voo salvo 2x no mesmo ciclo)

---

## v2 Requirements

### Extended Sources

- **SRC-01**: Integracao com Duffel API como fonte secundaria NDC para comparar precos exclusivos nao disponiveis no GDS
- **SRC-02**: Integracao com SerpApi Google Flights para usar sinal de previsao "prices unlikely to drop" como confirmacao

### Extended Monitoring

- **MON-01**: Suporte a voos de ida apenas (one-way), alem de roundtrip
- **MON-02**: Historico de variacao por booking class individual (grafico Y, B, M... separados)
- **MON-03**: Calculo automatico de custo total incluindo bagagem estimada por rota

### Extended Interface

- **UI-01**: Autocomplete de codigo IATA ao digitar aeroportos no formulario (busca por nome da cidade)
- **UI-02**: Exportar historico de alertas em CSV
- **UI-03**: Guia de deploy passo a passo para Fly.io integrado na interface

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| Compra de passagens | Apenas monitoramento - integracao com booking adiciona complexidade e responsabilidade |
| Multiplos usuarios / autenticacao | Ferramenta pessoal; adicionar auth nao agrega valor agora |
| Web scraping | Somente APIs oficiais; scraping viola ToS e e fragil |
| Hoteis, carros, multimodal | Foco em voos - expansao dilui o core value |
| App mobile nativo | Interface web responsiva e suficiente para o uso |
| Telegram / WhatsApp | Gmail resolve para uso pessoal de baixo volume; Telegram silenciado pelo usuario |
| Multi-tenant / SaaS | Escopo pessoal - virar SaaS e decisao de negocio futura |
| Real-time streaming de precos | Polling a cada 6h e suficiente; streaming aumentaria custo de API |

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
| FIX-01 | Phase 6 | Pending |
| UX-01 | Phase 6 | Pending |
| UX-02 | Phase 6 | Pending |
| EMAIL-01 | Phase 7 | Pending |
| EMAIL-02 | Phase 7 | Pending |
| EMAIL-03 | Phase 7 | Pending |
| UI-01 | Phase 8 | Pending |
| UI-02 | Phase 8 | Pending |
| UI-03 | Phase 8 | Pending |
| UI-04 | Phase 8 | Pending |
| UI-05 | Phase 8 | Pending |

**Coverage:**
- v1 requirements: 28 total, 28 mapped, 0 unmapped
- v1.1 requirements: 11 total, 11 mapped, 0 unmapped

---
*Requirements defined: 2026-03-24*
*Last updated: 2026-03-25 after v1.1 roadmap creation*
