# Roadmap: Flight Monitor

## Milestones

- ✅ **v1.0 MVP** - Phases 1-5 (shipped 2026-03-25)
- ✅ **v1.1 Polish & UX** - Phases 6-8 (shipped 2026-03-26)
- ✅ **v1.2 Visual Polish** - Phase 9 (shipped 2026-03-28)
- 🚧 **v2.0 Multi-usuario** - Phases 10-13 (in progress)

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

<details>
<summary>v1.1 Polish & UX (Phases 6-8) - SHIPPED 2026-03-26</summary>

- [x] **Phase 6: Quality & Feedback** - Corrigir snapshots duplicados, adicionar mensagens de confirmacao e pagina de erro amigavel
- [x] **Phase 7: Consolidated Email** - Reestruturar alertas para 1 email por grupo com rota mais barata, melhores datas e formato brasileiro
- [x] **Phase 8: Dashboard Redesign** - Cards coloridos por status, area de resumo, estado vazio e datas em formato brasileiro

### Phase 6: Quality & Feedback
**Goal**: Usuario recebe feedback claro das suas acoes e nunca ve erros genericos do servidor
**Depends on**: Phase 5
**Requirements**: FIX-01, UX-01, UX-02
**Success Criteria** (what must be TRUE):
  1. Polling nunca salva o mesmo voo duas vezes no mesmo ciclo de coleta
  2. Apos criar, editar ou desativar um grupo, usuario ve mensagem de confirmacao na tela
  3. Quando ocorre erro inesperado, usuario ve pagina amigavel com orientacao ao inves de "Internal Server Error"
**Plans**: 2 plans

Plans:
- [x] 06-01-PLAN.md - TDD deduplicacao de snapshots no polling (FIX-01)
- [x] 06-02-PLAN.md - Flash messages de feedback + pagina de erro amigavel (UX-01, UX-02)

### Phase 7: Consolidated Email
**Goal**: Usuario recebe 1 email util por grupo com todas as informacoes necessarias para decidir se compra
**Depends on**: Phase 6
**Requirements**: EMAIL-01, EMAIL-02, EMAIL-03
**Success Criteria** (what must be TRUE):
  1. Sistema envia exatamente 1 email por grupo (nao 1 por sinal) contendo rota mais barata com preco, companhia e datas
  2. Email inclui secao com as melhores datas para viajar dentro do periodo configurado
  3. Todas as datas no email aparecem no formato dd/mm/aaaa
  4. Email inclui resumo das demais rotas monitoradas alem da mais barata
**Plans**: 2 plans

Plans:
- [x] 07-01-PLAN.md - TDD compose_consolidated_email: rota mais barata, top 3 datas, resumo, formato brasileiro (EMAIL-01/02/03)
- [x] 07-02-PLAN.md - Refatorar polling_service para acumular sinais e enviar email consolidado (EMAIL-01)

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
**Plans**: 2 plans

Plans:
- [x] 08-01-PLAN.md - Backend summary data + rewrite index.html com cards coloridos, summary bar e estado vazio (UI-01/02/03/04/05)
- [x] 08-02-PLAN.md - Datas dd/mm/aaaa no detail.html + checkpoint visual (UI-05)

</details>

<details>
<summary>v1.2 Visual Polish (Phase 9) - SHIPPED 2026-03-28</summary>

- [x] **Phase 9: Visual Polish** - Aplicar paleta, tipografia, cards redesenhados, summary bar e estado vazio conforme UI-SPEC

### Phase 9: Visual Polish
**Goal**: Dashboard tem aparencia profissional e coesa seguindo o UI-SPEC aprovado, com paleta de cores padronizada, tipografia hierarquica e componentes visualmente refinados
**Depends on**: Phase 8
**Requirements**: VIS-01, VIS-02, VIS-03, VIS-04, VIS-05, VIS-06
**UI-SPEC**: .planning/phases/08-dashboard-redesign/08-UI-SPEC.md
**Success Criteria** (what must be TRUE):
  1. Dashboard usa paleta de cores consistente: fundo #f8fafc, cards brancos, accent sky blue #0ea5e9, e cores semanticas verde/amarelo/vermelho para classificacao de preco (LOW/MEDIUM/HIGH)
  2. Preco em cada card e exibido em fonte monospace 28px bold como elemento focal, com borda esquerda de 4px colorida pela classificacao do preco
  3. Cards respondem a hover com transicao de sombra em 0.2s, footer tem separador visivel, e grupos inativos aparecem com opacidade reduzida (0.6)
  4. Summary bar tem fundo escuro (#1e293b) com metricas em 20px bold e labels em 13px, visualmente distinta do restante da pagina
  5. Estado vazio exibe icone SVG de aviao, texto em 14px e botao CTA verde com min-height 40px, convidando o usuario a criar o primeiro grupo
**Plans**: 2 plans
**UI hint**: yes

Plans:
- [x] 09-01-PLAN.md - Paleta global (base.html) + cards, summary bar, estado vazio e tipografia (index.html) (VIS-01/02/03/04/05/06)
- [x] 09-02-PLAN.md - Paginas secundarias (detail, create, edit) + checkpoint visual (VIS-01/06)

</details>

### v2.0 Multi-usuario (In Progress)

**Milestone Goal:** Transformar o Flight Monitor de ferramenta pessoal em produto multi-usuario com landing page publica, login via Google OAuth e banco PostgreSQL persistente.

- [x] **Phase 10: PostgreSQL Foundation** - Migrar banco para PostgreSQL com Alembic, mantendo todos os testes passando (completed 2026-03-28)
- [ ] **Phase 11: Google OAuth** - Login com Google, sessoes persistentes e infraestrutura de autenticacao
- [ ] **Phase 12: Data Isolation** - Isolamento completo de dados por usuario, alertas por email do dono e controle de quota SerpAPI
- [ ] **Phase 13: Landing Page** - Pagina publica com hero, proposta de valor e CTA de login

## Phase Details

### Phase 10: PostgreSQL Foundation
**Goal**: Aplicacao roda sobre PostgreSQL em producao com migrations gerenciadas por Alembic, sem quebrar nenhum teste existente
**Depends on**: Phase 9
**Requirements**: DB-01, DB-02, DB-03
**Success Criteria** (what must be TRUE):
  1. Aplicacao conecta ao PostgreSQL (Neon.tech) em producao e ao SQLite in-memory nos testes, sem alteracao manual de configuracao entre ambientes
  2. Alembic gerencia o schema completo: `alembic upgrade head` cria todas as tabelas a partir de um banco vazio, e `alembic revision --autogenerate` detecta mudancas nos models
  3. Todos os 188+ testes existentes continuam passando com SQLite in-memory (nenhuma dependencia de PostgreSQL nos testes)
  4. Dados existentes no Render sobrevivem a um redeploy (persistencia real, nao mais SQLite efemero)
**Plans**: 2 plans

Plans:
- [x] 10-01-PLAN.md - database.py condicional + Alembic init + baseline migration (DB-01, DB-02)
- [x] 10-02-PLAN.md - render.yaml + .env.example + regressao + checkpoint (DB-01, DB-03)

### Phase 11: Google OAuth
**Goal**: Usuario pode fazer login com Google e navegar pelo dashboard com sessao persistente, vendo seu nome e foto no header
**Depends on**: Phase 10
**Requirements**: AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05
**Success Criteria** (what must be TRUE):
  1. Usuario clica "Entrar com Google" e apos autorizar no Google e redirecionado de volta ao dashboard logado
  2. Sessao do usuario persiste entre abas e refreshes do navegador (cookie assinado com user_id)
  3. Botao de logout aparece em todas as paginas autenticadas e ao clicar limpa a sessao e redireciona para a landing page
  4. Header de todas as paginas autenticadas exibe nome e foto do usuario (vindos do perfil Google)
  5. Se o login falhar (usuario cancelou, erro do Google), landing page exibe mensagem de erro clara sem mostrar stacktrace
**Plans**: 3 plans

Plans:
- [x] 11-01-PLAN.md — User model + Authlib + config + Alembic migration + test fixtures (AUTH-01, AUTH-02)
- [x] 11-02-PLAN.md — OAuth routes + SessionMiddleware + AuthMiddleware + testes (AUTH-01, AUTH-02, AUTH-03, AUTH-05)
- [ ] 11-03-PLAN.md — Header UI (avatar/nome/logout) + render.yaml + checkpoint visual (AUTH-04, AUTH-05)

### Phase 12: Data Isolation
**Goal**: Cada usuario ve exclusivamente seus proprios dados, alertas vao para o email correto e o consumo de SerpAPI e visivel
**Depends on**: Phase 11
**Requirements**: MULTI-01, MULTI-02, MULTI-03, MULTI-04
**Success Criteria** (what must be TRUE):
  1. Usuario A nao consegue ver grupos, snapshots ou sinais do Usuario B por nenhuma rota da aplicacao (isolamento completo verificado por teste automatizado de dois usuarios)
  2. Alertas por email sao enviados para o email do Google do dono do grupo (nao mais para um email fixo em .env)
  3. Dashboard exibe indicador de buscas SerpAPI restantes no mes, visivel para todos os usuarios (budget compartilhado global)
  4. Usuario pode acessar pagina "Meus alertas" com historico de todos os sinais detectados para seus grupos
**Plans**: TBD

### Phase 13: Landing Page
**Goal**: Visitante nao logado ve uma landing page publica que explica o produto e convida a entrar com Google
**Depends on**: Phase 11
**Requirements**: LAND-01, LAND-02, LAND-03, LAND-04
**Success Criteria** (what must be TRUE):
  1. Visitante nao logado que acessa a URL raiz ve landing page publica com hero section e descricao do produto (nao e redirecionado para login)
  2. Landing page contem secao "Por que somos diferentes" comparando Flight Monitor com Google Flights e Skyscanner
  3. Botao "Entrar com Google" aparece como CTA principal e inicia o fluxo OAuth ao ser clicado
  4. Landing page e responsiva e utilizavel em telas mobile (layout mobile-first)
**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:** Phase 10 -> 11 -> 12 -> 13

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation | v1.0 | 3/3 | Complete | 2026-03-25 |
| 2. Data Collection | v1.0 | 3/3 | Complete | 2026-03-25 |
| 3. Signal Detection | v1.0 | 3/3 | Complete | 2026-03-25 |
| 4. Gmail Alerts | v1.0 | 3/3 | Complete | 2026-03-25 |
| 5. Web Dashboard | v1.0 | 3/3 | Complete | 2026-03-25 |
| 6. Quality & Feedback | v1.1 | 2/2 | Complete | 2026-03-26 |
| 7. Consolidated Email | v1.1 | 2/2 | Complete | 2026-03-26 |
| 8. Dashboard Redesign | v1.1 | 2/2 | Complete | 2026-03-26 |
| 9. Visual Polish | v1.2 | 2/2 | Complete | 2026-03-28 |
| 10. PostgreSQL Foundation | v2.0 | 2/2 | Complete    | 2026-03-28 |
| 11. Google OAuth | v2.0 | 2/3 | In Progress|  |
| 12. Data Isolation | v2.0 | 0/? | Not started | - |
| 13. Landing Page | v2.0 | 0/? | Not started | - |
