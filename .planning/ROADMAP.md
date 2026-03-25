# Roadmap: Flight Monitor

## Milestones

- ✅ **v1.0 MVP** - Phases 1-5 (shipped 2026-03-25)
- 🚧 **v1.1 Polish & UX** - Phases 6-8 (in progress)

## Phases

<details>
<summary>v1.0 MVP (Phases 1-5) - SHIPPED 2026-03-25</summary>

- [x] **Phase 1: Foundation** - Aplicacao inicia, banco criado, grupos de rota gerenciados via API
- [x] **Phase 2: Data Collection** - Polling automatico da Amadeus captura snapshots de preco e booking class
- [x] **Phase 3: Signal Detection** - Sistema detecta os 4 sinais de compra e deduplica alertas
- [x] **Phase 4: Gmail Alerts** - Alertas enviados por email com link de silenciar embutido
- [x] **Phase 5: Web Dashboard** - Interface web para visualizar grupos, historico e gerenciar configuracoes

### Phase 1: Foundation
**Goal**: Aplicacao esta rodando e o usuario pode gerenciar Grupos de Rota completos via API
**Depends on**: Nothing (first phase)
**Requirements**: INFRA-01, INFRA-02, INFRA-03, ROUTE-01, ROUTE-02, ROUTE-03, ROUTE-04, ROUTE-05, ROUTE-06
**Success Criteria** (what must be TRUE):
  1. Aplicacao inicia com um unico comando e o servidor responde em localhost
  2. Arquivo `.env` controla todas as credenciais; banco SQLite e criado automaticamente com todas as tabelas na primeira execucao
  3. Usuario pode criar um Grupo de Rota com multiplas origens, multiplos destinos, duracao e periodo via API
  4. Usuario pode editar, ativar, desativar e deletar grupos existentes; sistema rejeita criacao de 11o grupo ativo
**Plans**: 3 plans

Plans:
- [x] 01-01-PLAN.md - Setup projeto + infraestrutura (INFRA-01/02/03)
- [x] 01-02-PLAN.md - CRUD de Route Groups (ROUTE-01 a ROUTE-06)
- [x] 01-03-PLAN.md - Refatoracao + checkpoint humano

### Phase 2: Data Collection
**Goal**: Sistema coleta dados reais da Amadeus de forma autonoma e persiste snapshots para analise historica
**Depends on**: Phase 1
**Requirements**: COLL-01, COLL-02, COLL-03, COLL-04, COLL-05, COLL-06
**Success Criteria** (what must be TRUE):
  1. Scheduler executa polling a cada 6 horas para cada grupo ativo sem intervencao manual
  2. Por ciclo, sistema identifica as 5 combinacoes mais baratas de rota e data dentro do periodo do grupo
  3. Para cada combinacao, snapshot contem booking classes com contagem e classificacao LOW/MEDIUM/HIGH
  4. Snapshots persistem no banco com timestamp; historico acumula entre polling cycles
  5. Falhas de API sao tratadas sem crashar o scheduler
**Plans**: 3 plans

Plans:
- [x] 02-01-PLAN.md - Modelos FlightSnapshot/BookingClassSnapshot + snapshot_service (COLL-05)
- [x] 02-02-PLAN.md - AmadeusClient wrapper com Flight Offers, Availability e Price Metrics (COLL-02/03/04)
- [x] 02-03-PLAN.md - Polling service + scheduler 6h + error handling (COLL-01/06)

### Phase 3: Signal Detection
**Goal**: Sistema analisa snapshots sequenciais e detecta os momentos de compra mais valiosos
**Depends on**: Phase 2
**Requirements**: SIGN-01, SIGN-02, SIGN-03, SIGN-04, SIGN-05
**Success Criteria** (what must be TRUE):
  1. Sistema detecta BALDE FECHANDO (classe K ou Q caiu de >=3 para <=1) com urgencia ALTA
  2. Sistema detecta BALDE REABERTO (classe estava em 0 e voltou a ter assentos) com urgencia MAXIMA
  3. Sistema detecta PRECO ABAIXO DO HISTORICO (LOW + preco abaixo da media) com urgencia MEDIA
  4. Sistema detecta JANELA OTIMA (dias antes do voo na faixa ideal) com urgencia MEDIA
  5. Mesmo sinal para a mesma rota nao e re-emitido dentro de 12 horas
**Plans**: 3 plans

Plans:
- [x] 03-01-PLAN.md - RED tests para todos os sinais e deduplicacao
- [x] 03-02-PLAN.md - GREEN implementacao signal_service + integracao polling
- [x] 03-03-PLAN.md - Refatoracao + checkpoint humano

### Phase 4: Gmail Alerts
**Goal**: Usuario recebe alertas por email no Gmail com contexto completo e link de silenciar embutido
**Depends on**: Phase 3
**Requirements**: ALRT-01, ALRT-02
**Success Criteria** (what must be TRUE):
  1. Quando sinal e detectado, email chega no Gmail contendo grupo, rota, preco atual, contexto historico e urgencia
  2. Email contem link que ao ser clicado pausa alertas daquele grupo por 24 horas
**Plans**: 3 plans

Plans:
- [x] 04-01-PLAN.md - TDD alert_service: composicao email, envio SMTP, token HMAC, silenciamento
- [x] 04-02-PLAN.md - TDD silence endpoint GET /api/v1/alerts/silence/{token}
- [x] 04-03-PLAN.md - Integracao polling_service + refatoracao + checkpoint

### Phase 5: Web Dashboard
**Goal**: Usuario pode visualizar o estado atual de todos os grupos, historico de precos e gerenciar grupos pelo navegador
**Depends on**: Phase 4
**Requirements**: ALRT-03, DASH-01, DASH-02, DASH-03, DASH-04, DASH-05
**Success Criteria** (what must be TRUE):
  1. Dashboard exibe todos os grupos com melhor preco atual, rota mais barata e indicador visual de sinal ativo
  2. Clicando em um grupo, usuario ve grafico de linha com historico de preco das ultimas 2 semanas
  3. Usuario pode criar novo Grupo de Rota pelo formulario no dashboard
  4. Usuario pode editar e desativar grupos existentes pelo dashboard
  5. Interface carrega e e utilizavel no celular (layout responsivo)
**Plans**: 3 plans

Plans:
- [x] 05-01-PLAN.md - TDD dashboard_service: queries de aggregation + dependencias Jinja2
- [x] 05-02-PLAN.md - Dashboard routes + templates: lista de grupos com badges + detalhe com Chart.js
- [x] 05-03-PLAN.md - Formularios criar/editar/toggle grupo + checkpoint visual

</details>

### v1.1 Polish & UX (In Progress)

**Milestone Goal:** Melhorar a experiencia do usuario com email consolidado, dashboard redesenhado e correcoes de qualidade

- [ ] **Phase 6: Quality & Feedback** - Corrigir snapshots duplicados, adicionar mensagens de confirmacao e pagina de erro amigavel
- [ ] **Phase 7: Consolidated Email** - Reestruturar alertas para 1 email por grupo com rota mais barata, melhores datas e formato brasileiro
- [ ] **Phase 8: Dashboard Redesign** - Cards coloridos por status, area de resumo, estado vazio e datas em formato brasileiro

## Phase Details

### Phase 6: Quality & Feedback
**Goal**: Usuario recebe feedback claro das suas acoes e nunca ve erros genericos do servidor
**Depends on**: Phase 5
**Requirements**: FIX-01, UX-01, UX-02
**Success Criteria** (what must be TRUE):
  1. Polling nunca salva o mesmo voo duas vezes no mesmo ciclo de coleta
  2. Apos criar, editar ou desativar um grupo, usuario ve mensagem de confirmacao na tela
  3. Quando ocorre erro inesperado, usuario ve pagina amigavel com orientacao ao inves de "Internal Server Error"
**Plans**: TBD

### Phase 7: Consolidated Email
**Goal**: Usuario recebe 1 email util por grupo com todas as informacoes necessarias para decidir se compra
**Depends on**: Phase 6
**Requirements**: EMAIL-01, EMAIL-02, EMAIL-03
**Success Criteria** (what must be TRUE):
  1. Sistema envia exatamente 1 email por grupo (nao 1 por sinal) contendo rota mais barata com preco, companhia e datas
  2. Email inclui secao com as melhores datas para viajar dentro do periodo configurado
  3. Todas as datas no email aparecem no formato dd/mm/aaaa
  4. Email inclui resumo das demais rotas monitoradas alem da mais barata
**Plans**: TBD

### Phase 8: Dashboard Redesign
**Goal**: Dashboard apresenta informacoes de forma visual e intuitiva com cards, cores e estados claros
**Depends on**: Phase 6
**Requirements**: UI-01, UI-02, UI-03, UI-04, UI-05
**Success Criteria** (what must be TRUE):
  1. Topo do dashboard mostra area de resumo com total de grupos ativos, menor preco encontrado e horario do proximo polling
  2. Cada grupo aparece como card com borda colorida (verde=LOW, amarelo=MEDIUM, vermelho=HIGH, cinza=sem dados)
  3. Card exibe nome, rotas, preco mais barato em destaque, companhia, datas e badge de sinal
  4. Quando nao ha grupos cadastrados, tela mostra mensagem amigavel com botao de criar grupo
  5. Todas as datas no dashboard aparecem no formato dd/mm/aaaa
**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:** Phase 6 > Phase 7 > Phase 8 (Phases 7 and 8 both depend on 6; 7 and 8 are independent of each other)

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation | v1.0 | 3/3 | Complete | 2026-03-25 |
| 2. Data Collection | v1.0 | 3/3 | Complete | 2026-03-25 |
| 3. Signal Detection | v1.0 | 3/3 | Complete | 2026-03-25 |
| 4. Gmail Alerts | v1.0 | 3/3 | Complete | 2026-03-25 |
| 5. Web Dashboard | v1.0 | 3/3 | Complete | 2026-03-25 |
| 6. Quality & Feedback | v1.1 | 0/? | Not started | - |
| 7. Consolidated Email | v1.1 | 0/? | Not started | - |
| 8. Dashboard Redesign | v1.1 | 0/? | Not started | - |
