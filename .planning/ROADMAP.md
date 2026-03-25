# Roadmap: Flight Monitor

## Overview

O Flight Monitor é construído em cinco fases que seguem a cadeia de valor natural do produto: primeiro a infraestrutura e gerenciamento de grupos (o que monitorar), depois a coleta de dados reais da Amadeus (os dados brutos), depois a detecção de sinais (a inteligência), depois os alertas por Gmail (a entrega do valor), e por fim o dashboard web (a visibilidade). Cada fase entrega uma capacidade verificável e desbloqueia a próxima.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation** - Aplicação inicia, banco criado, grupos de rota gerenciados via API (completed 2026-03-25)
- [x] **Phase 2: Data Collection** - Polling automático da Amadeus captura snapshots de preço e booking class (completed 2026-03-25)
- [ ] **Phase 3: Signal Detection** - Sistema detecta os 4 sinais de compra e deduplica alertas
- [ ] **Phase 4: Gmail Alerts** - Alertas são enviados por email com link de silenciar embutido
- [ ] **Phase 5: Web Dashboard** - Interface web permite visualizar grupos, histórico e gerenciar configurações

## Phase Details

### Phase 1: Foundation
**Goal**: Aplicação está rodando e o usuário pode gerenciar Grupos de Rota completos via API
**Depends on**: Nothing (first phase)
**Requirements**: INFRA-01, INFRA-02, INFRA-03, ROUTE-01, ROUTE-02, ROUTE-03, ROUTE-04, ROUTE-05, ROUTE-06
**Success Criteria** (what must be TRUE):
  1. Aplicação inicia com um único comando e o servidor responde em localhost
  2. Arquivo `.env` controla todas as credenciais; banco SQLite é criado automaticamente com todas as tabelas na primeira execução
  3. Usuário pode criar um Grupo de Rota com múltiplas origens, múltiplos destinos, duração e período via API
  4. Usuário pode editar, ativar, desativar e deletar grupos existentes; sistema rejeita criação de 11º grupo ativo
**Plans**: 3 plans

Plans:
- [x] 01-01-PLAN.md - Setup projeto + testes RED + implementacao GREEN para infraestrutura (INFRA-01/02/03)
- [x] 01-02-PLAN.md - Testes RED + implementacao GREEN para CRUD de Route Groups (ROUTE-01 a ROUTE-06)
- [ ] 01-03-PLAN.md - Refatoracao (REFACTOR) + checkpoint humano de verificacao

### Phase 2: Data Collection
**Goal**: Sistema coleta dados reais da Amadeus de forma autônoma e persiste snapshots para análise histórica
**Depends on**: Phase 1
**Requirements**: COLL-01, COLL-02, COLL-03, COLL-04, COLL-05, COLL-06
**Success Criteria** (what must be TRUE):
  1. Scheduler executa polling a cada 6 horas para cada grupo ativo sem intervenção manual
  2. Por ciclo, sistema identifica as 5 combinações mais baratas de rota e data dentro do período do grupo
  3. Para cada combinação, snapshot contém booking classes com contagem (ex: Y7 B4 M3) e classificação LOW/MEDIUM/HIGH
  4. Snapshots persistem no banco com timestamp; histórico acumula entre polling cycles
  5. Falhas de API (timeout, rate limit) são tratadas sem crashar o scheduler; próximo ciclo executa normalmente
**Plans**: 3 plans

Plans:
- [x] 02-01-PLAN.md - Modelos FlightSnapshot/BookingClassSnapshot + snapshot_service + config Gmail (COLL-05)
- [x] 02-02-PLAN.md - AmadeusClient wrapper com Flight Offers, Availability e Price Metrics (COLL-02/03/04)
- [x] 02-03-PLAN.md - Polling service + scheduler 6h + integracao lifespan + error handling (COLL-01/06)

### Phase 3: Signal Detection
**Goal**: Sistema analisa snapshots sequenciais e detecta os momentos de compra mais valiosos
**Depends on**: Phase 2
**Requirements**: SIGN-01, SIGN-02, SIGN-03, SIGN-04, SIGN-05
**Success Criteria** (what must be TRUE):
  1. Sistema detecta BALDE FECHANDO (classe K ou Q caiu de >=3 para <=1) e marca urgência ALTA
  2. Sistema detecta BALDE REABERTO (classe estava em 0 e voltou a ter assentos) e marca urgência MAXIMA
  3. Sistema detecta PRECO ABAIXO DO HISTORICO (Amadeus retorna LOW e preço atual abaixo da média dos últimos 14 snapshots) e marca urgência MEDIA
  4. Sistema detecta JANELA OTIMA (dias antes do voo entra na faixa ideal por tipo de rota) e marca urgência MEDIA
  5. Mesmo sinal para a mesma rota não é re-emitido dentro de 12 horas (deduplicação funciona)
**Plans**: TBD

### Phase 4: Gmail Alerts
**Goal**: Usuário recebe alertas por email no Gmail com contexto completo e link de silenciar embutido
**Depends on**: Phase 3
**Requirements**: ALRT-01, ALRT-02, ALRT-03
**Success Criteria** (what must be TRUE):
  1. Quando sinal é detectado, email chega no Gmail contendo grupo, rota, preço atual, contexto histórico e nível de urgência
  2. Email contém link que ao ser clicado pausa alertas daquele grupo por 24 horas
  3. Dashboard web mostra status de todos os grupos ativos e melhor preço atual (substitui o /status do bot)
**Plans**: TBD
**UI hint**: yes

### Phase 5: Web Dashboard
**Goal**: Usuário pode visualizar o estado atual de todos os grupos, histórico de preços e gerenciar grupos pelo navegador
**Depends on**: Phase 4
**Requirements**: DASH-01, DASH-02, DASH-03, DASH-04, DASH-05
**Success Criteria** (what must be TRUE):
  1. Dashboard exibe todos os grupos com melhor preço atual, rota mais barata e indicador visual de sinal ativo (nenhum/medio/alto/maximo)
  2. Clicando em um grupo, usuário vê gráfico de linha com histórico de preço das últimas 2 semanas
  3. Usuário pode criar novo Grupo de Rota pelo formulário no dashboard sem usar a API diretamente
  4. Usuário pode editar e desativar grupos existentes pelo dashboard
  5. Interface carrega e é utilizável no celular (layout responsivo)
**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 2/3 (checkpoint) | Complete    | 2026-03-25 |
| 2. Data Collection | 3/3 | Complete   | 2026-03-25 |
| 3. Signal Detection | 0/TBD | Not started | - |
| 4. Gmail Alerts | 0/TBD | Not started | - |
| 5. Web Dashboard | 0/TBD | Not started | - |
