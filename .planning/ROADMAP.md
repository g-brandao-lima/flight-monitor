# Roadmap: Flight Monitor

## Milestones

- ✅ **v1.0 MVP** - Phases 1-5 (shipped 2026-03-25)
- ✅ **v1.1 Polish & UX** - Phases 6-8 (shipped 2026-03-26)
- ✅ **v1.2 Visual Polish** - Phase 9 (shipped 2026-03-28)
- ✅ **v2.0 Multi-usuario** - Phases 10-14 (shipped 2026-03-30)
- ✅ **v2.1 Clareza de Preco e Robustez** - Phases 15-23 (shipped 2026-04-20, 11 phases, Phase 18 deferred)
- ✅ **v2.2 UX Polish e Quick Wins** - Phases 24-31 (shipped 2026-04-20)
- 🚧 **v2.3 Growth Features e Cache Centralizado** - Phases 31.9, 32-36 (in progress, started 2026-04-21)

### v2.3 Growth Features e Cache Centralizado (In Progress)

**Milestone Goal:** Eliminar gargalo SerpAPI via cache centralizado Travelpayouts, abrir canal de aquisicao organica (paginas publicas indexaveis), transformar historico em recomendacao acionavel e suportar roteiros multi-trecho.

- [ ] **Phase 31.9: Price Fidelity Hygiene** - Rotulo "preco de referencia", disclaimer de divergencia, remocao do fast-flights
- [ ] **Phase 32: Cache Layer Travelpayouts** - Polling 6h das top 500 rotas BR × 45 datas em tabela route_cache, SerpAPI como fallback
- [ ] **Phase 33: Public Route Index (SEO)** - Paginas publicas /rotas/{ORIG}-{DEST} com historico, sitemap, Open Graph, affiliate link
- [ ] **Phase 34: Price Prediction Engine** - Recomendacao deterministica "Compre agora / Aguarde / Monitorar" com backtest retrospectivo
- [ ] **Phase 35: Onboarding Wizard** - Wizard condicional 2 passos para primeiro login cria grupo automatico e revisa copy
- [ ] **Phase 36: Multi-Leg Trip Builder** - Grupo-pai com N trechos encadeados, preco total e sinal sobre o total

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

<details>
<summary>v2.0 Multi-usuario (Phases 10-14) - SHIPPED 2026-03-30</summary>

- [x] **Phase 10: PostgreSQL Foundation** - Migrar banco para PostgreSQL com Alembic, mantendo todos os testes passando
- [x] **Phase 11: Google OAuth** - Login com Google, sessoes persistentes e infraestrutura de autenticacao
- [x] **Phase 12: Data Isolation** - Isolamento completo de dados por usuario, alertas por email do dono e controle de quota SerpAPI
- [x] **Phase 13: Landing Page** - Pagina publica com hero, proposta de valor e CTA de login
- [x] **Phase 14: Production Fixes** - Corrigir func.strftime SQLite-only e adicionar APP_BASE_URL ao render.yaml

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
- [x] 11-01-PLAN.md - User model + Authlib + config + Alembic migration + test fixtures (AUTH-01, AUTH-02)
- [x] 11-02-PLAN.md - OAuth routes + SessionMiddleware + AuthMiddleware + testes (AUTH-01, AUTH-02, AUTH-03, AUTH-05)
- [x] 11-03-PLAN.md - Header UI (avatar/nome/logout) + render.yaml + checkpoint visual (AUTH-04, AUTH-05)

### Phase 12: Data Isolation
**Goal**: Cada usuario ve exclusivamente seus proprios dados, alertas vao para o email correto e o consumo de SerpAPI e visivel
**Depends on**: Phase 11
**Requirements**: MULTI-01, MULTI-02, MULTI-03, MULTI-04
**Success Criteria** (what must be TRUE):
  1. Usuario A nao consegue ver grupos, snapshots ou sinais do Usuario B por nenhuma rota da aplicacao (isolamento completo verificado por teste automatizado de dois usuarios)
  2. Alertas por email sao enviados para o email do Google do dono do grupo (nao mais para um email fixo em .env)
  3. Dashboard exibe indicador de buscas SerpAPI restantes no mes, visivel para todos os usuarios (budget compartilhado global)
  4. Usuario pode acessar pagina "Meus alertas" com historico de todos os sinais detectados para seus grupos
**Plans**: 3 plans

Plans:
- [x] 12-01-PLAN.md - user_id FK + migration + isolamento completo de services e routes (MULTI-01)
- [x] 12-02-PLAN.md - Email alertas para dono do grupo + pagina Meus Alertas (MULTI-02, MULTI-04)
- [x] 12-03-PLAN.md - Contador SerpAPI global + indicador no dashboard (MULTI-03)

### Phase 13: Landing Page
**Goal**: Visitante nao logado ve uma landing page publica que explica o produto e convida a entrar com Google
**Depends on**: Phase 11
**Requirements**: LAND-01, LAND-02, LAND-03, LAND-04
**Success Criteria** (what must be TRUE):
  1. Visitante nao logado que acessa a URL raiz ve landing page publica com hero section e descricao do produto (nao e redirecionado para login)
  2. Landing page contem secao "Por que somos diferentes" comparando Flight Monitor com Google Flights e Skyscanner
  3. Botao "Entrar com Google" aparece como CTA principal e inicia o fluxo OAuth ao ser clicado
  4. Landing page e responsiva e utilizavel em telas mobile (layout mobile-first)
**Plans**: 1 plan

Plans:
- [x] 13-01-PLAN.md - Landing page template + rota condicional + checkpoint visual (LAND-01, LAND-02, LAND-03, LAND-04)
**UI hint**: yes

### Phase 14: Production Fixes
**Goal**: Corrigir funcoes SQL SQLite-only que crasham em PostgreSQL e adicionar APP_BASE_URL ao deploy config
**Depends on**: Phase 12
**Requirements**: DB-01, MULTI-01, MULTI-02, MULTI-03
**Gap Closure**: Closes gaps from v2.0 milestone audit
**Success Criteria** (what must be TRUE):
  1. Dashboard funciona em PostgreSQL sem erros (func.strftime substituido por funcoes dialect-agnostic)
  2. APP_BASE_URL declarado no render.yaml como env var sync:false
  3. Link de silenciar alerta no email aponta para URL de producao (nao localhost)
  4. Todos os 218+ testes continuam passando
**Plans**: 1 plan

Plans:
- [x] 14-01-PLAN.md - Substituir func.strftime por Python-side processing + adicionar APP_BASE_URL ao render.yaml (DB-01, MULTI-01, MULTI-02, MULTI-03)

</details>

### v2.1 Clareza de Preco e Robustez (SHIPPED 2026-04-20)

**Milestone Goal:** Tornar o preco das passagens imediatamente compreensivel para o usuario e fortalecer a infraestrutura do projeto (CI, rate limiting, otimizacao de cota, limpeza de legado).

- [ ] **Phase 15: CI Pipeline** - GitHub Actions roda pytest automaticamente e bloqueia deploy com testes falhando
- [ ] **Phase 16: Passengers Fix** - Corrigir bug de passengers hardcoded no fast-flights
- [ ] **Phase 17: Price Labels** - Rotulo "por pessoa, ida e volta" e total para multiplos passageiros em todos os contextos
- [ ] **Phase 18: JWT Sessions** - Migrar sessoes de cookie stateful para JWT stateless em cookie httponly
- [ ] **Phase 19: Rate Limiting** - Proteger endpoints com limites por usuario e por custo de operacao
- [ ] **Phase 20: SerpAPI Cache** - Cache in-memory para evitar chamadas duplicadas no mesmo ciclo de polling
- [ ] **Phase 21: Legacy Removal** - Remover tabela e modelo BookingClassSnapshot do banco e do codigo

## Phase Details

### Phase 15: CI Pipeline
**Goal**: Todo push e PR na main tem testes executados automaticamente, e deploy so acontece se testes passarem
**Depends on**: Phase 14
**Requirements**: CI-01, CI-02
**Success Criteria** (what must be TRUE):
  1. Push ou PR na branch main dispara workflow do GitHub Actions que executa pytest e reporta resultado
  2. Render so faz deploy apos CI checks passarem (configuracao "Auto-Deploy" condicional)
  3. PR com teste falhando mostra status check vermelho no GitHub
**Plans**: TBD

### Phase 15.1: Security Emergency Fix (INSERTED)

**Goal:** [Urgent work - to be planned]
**Requirements**: TBD
**Depends on:** Phase 15
**Plans:** 0 plans

Plans:
- [ ] TBD (run /gsd:plan-phase 15.1 to break down)

### Phase 16: Passengers Fix
**Goal**: Sistema envia o numero correto de passageiros para a API de busca de voos
**Depends on**: Phase 15
**Requirements**: PRICE-03
**Success Criteria** (what must be TRUE):
  1. Chamada ao fast-flights usa o numero de passageiros configurado no grupo (nao mais Passengers(adults=1) hardcoded)
  2. Resultados de busca refletem preco por pessoa para a quantidade correta de passageiros
**Plans**: TBD

### Phase 17: Price Labels
**Goal**: Usuario entende imediatamente o que o preco significa e quanto vai pagar no total
**Depends on**: Phase 16
**Requirements**: PRICE-01, PRICE-02
**Success Criteria** (what must be TRUE):
  1. Todo preco exibido no dashboard (cards, grafico, detalhe) tem rotulo "por pessoa, ida e volta" visivel
  2. Todo preco em emails de alerta tem rotulo "por pessoa, ida e volta"
  3. Quando grupo tem mais de 1 passageiro, total calculado (preco x passageiros) aparece ao lado do preco unitario em todos os contextos (dashboard, email, alertas)
**Plans**: TBD
**UI hint**: yes

### Phase 17.1: Price Source Indicator (INSERTED)

**Goal:** [Urgent work - to be planned]
**Requirements**: TBD
**Depends on:** Phase 17
**Plans:** 0 plans

Plans:
- [ ] TBD (run /gsd:plan-phase 17.1 to break down)

### Phase 18: JWT Sessions
**Goal**: Sessoes de autenticacao sao stateless via JWT, permitindo escalabilidade horizontal sem perder o fluxo OAuth
**Depends on**: Phase 15
**Requirements**: JWT-01, JWT-02, JWT-03
**Success Criteria** (what must be TRUE):
  1. Apos login via Google, usuario recebe JWT em cookie httponly (nao mais session cookie stateful com user_id)
  2. SessionMiddleware permanece ativo exclusivamente para o fluxo OAuth (state parameter do Authlib) e nao e usado para autenticacao
  3. Token JWT expira em 7 dias; apos expiracao usuario e redirecionado para login com mensagem clara
  4. Todos os 218+ testes continuam passando apos a migracao
**Plans**: TBD

### Phase 19: Rate Limiting
**Goal**: Endpoints estao protegidos contra uso excessivo com limites diferenciados por tipo de operacao
**Depends on**: Phase 18
**Requirements**: RATE-01, RATE-02
**Success Criteria** (what must be TRUE):
  1. Endpoints tem rate limiting ativo: usuario autenticado e identificado por user_id, anonimo por IP (X-Forwarded-For)
  2. Limites variam por custo da operacao (endpoints de escrita tem limite menor que leitura, autocomplete tem limite proprio)
  3. Quando limite e excedido, usuario recebe resposta HTTP 429 com mensagem clara de "tente novamente em X segundos"
**Plans**: TBD

### Phase 20: SerpAPI Cache
**Goal**: Sistema nao desperdiça cota SerpAPI com buscas duplicadas no mesmo ciclo de polling
**Depends on**: Phase 16
**Requirements**: CACHE-01, CACHE-02
**Success Criteria** (what must be TRUE):
  1. Resultados de busca SerpAPI sao cacheados in-memory com TTL de 13 horas
  2. Cache key inclui todos os parametros relevantes (origem, destino, datas, passengers, max_stops) — mesma busca dentro do TTL retorna resultado cacheado sem chamar a API
  3. Buscas com parametros diferentes (ex: passengers diferente) nao colidem no cache
**Plans**: TBD

### Phase 21: Legacy Removal
**Goal**: Codigo e banco estao limpos, sem restos do modelo Amadeus que nao e mais usado
**Depends on**: Phase 15
**Requirements**: CLEAN-01, CLEAN-02
**Success Criteria** (what must be TRUE):
  1. Tabela booking_class_snapshots removida do banco via migration Alembic executavel com `alembic upgrade head`
  2. Modelo BookingClassSnapshot e todas as referencias (imports, queries, testes) removidos do codigo
  3. Todos os testes continuam passando apos a remocao
**Plans**: TBD

### Phase 22: Historical Context in Alerts

**Goal:** [To be planned]
**Requirements**: TBD
**Depends on:** Phase 21
**Plans:** 0 plans

Plans:
- [ ] TBD (run /gsd:plan-phase 22 to break down)

### Phase 23: Inventory Signal Empirical Validation

**Goal:** [To be planned]
**Requirements**: TBD
**Depends on:** Phase 22
**Plans:** 0 plans

Plans:
- [ ] TBD (run /gsd:plan-phase 23 to break down)

## v2.3 Growth Features e Cache Centralizado (In Progress)

**Milestone Goal:** Eliminar gargalo SerpAPI via cache centralizado Travelpayouts, abrir canal de aquisicao organica (paginas publicas indexaveis), transformar historico em recomendacao acionavel e suportar roteiros multi-trecho.

**Execution Order:** 31.9 → 32 → 33 → 34 → (avaliar) → 35 → 36

### Phase 31.9: Price Fidelity Hygiene
**Goal**: Usuario entende que o preco exibido e referencia Google Flights, nao valor final de checkout, e o sistema nao usa mais scraping fragil como fonte
**Depends on**: Nothing (foundation hygiene quick win, independent of Phase 32)
**Requirements**: HYG-01, HYG-02, HYG-03
**Success Criteria** (what must be TRUE):
  1. Dashboard cards, pagina de detalhe do grupo e email consolidado exibem rotulo "preco de referencia Google Flights" em vez de apenas "preco"
  2. Proximo a cada preco (tooltip, nota de rodape ou infobox) aparece disclaimer: "pode divergir ate 5% do valor final; bagagem e taxas nao incluidas"
  3. fast-flights removido do codigo (imports, chamadas, dependencia); apenas SerpAPI e cache local restam como fontes de preco
  4. Todos os testes continuam passando apos remocao do fast-flights
**Plans**: 2 plans
Plans:
- [ ] 31.9-01-PLAN.md — UI copy: rotulo preco de referencia + disclaimer em cards, detalhe e email (HYG-01, HYG-02)
- [ ] 31.9-02-PLAN.md — Remocao fast-flights do orchestrator e requirements (HYG-03)
**UI hint**: yes

### Phase 32: Cache Layer Travelpayouts
**Goal**: 95% das leituras do dashboard sao servidas do banco local sem consumir cota SerpAPI; gargalo da API externa desaparece
**Depends on**: Phase 31.9
**Requirements**: CACHE-03, CACHE-04, CACHE-05, CACHE-06, CACHE-07
**Success Criteria** (what must be TRUE):
  1. Nova tabela `route_cache` existe em producao com colunas origin, destination, departure_date, return_date, min_price, currency, cached_at, source; populada via migration Alembic
  2. Cron APScheduler a cada 6h executa polling Travelpayouts `prices_for_dates` nas top 500 rotas BR × 45 datas e grava em `route_cache`
  3. `flight_search.search_flights_ex()` consulta `route_cache` primeiro e so chama SerpAPI em cache miss ou refresh sob demanda de grupo ativo
  4. Painel `/admin/stats` exibe cache hit rate percentual dos ultimos 7 dias e quota Travelpayouts restante
  5. Quota SerpAPI mensal observada em producao cai para menos de 500 chamadas/mes mantendo o mesmo numero de usuarios ativos
**Plans**: TBD

### Phase 33: Public Route Index (SEO)
**Goal**: Visitante do Google buscando "passagem GRU Lisboa" cai em pagina publica do Flight Monitor indexada, com CTA de monitoramento e link de compra monetizado
**Depends on**: Phase 32
**Requirements**: SEO-01, SEO-02, SEO-03, SEO-04, SEO-05
**Success Criteria** (what must be TRUE):
  1. Visitante nao logado acessa `/rotas/{ORIG}-{DEST}` e ve pagina publica com preco mediano atual, historico 180d, melhores meses historicos e CTA "monitore essa rota" (dados servidos 100% do `route_cache`, zero chamada externa por pageview)
  2. `sitemap.xml` dinamico lista todas as rotas com 30 ou mais snapshots acumulados e e servido em `/sitemap.xml`
  3. Cada pagina de rota inclui meta tags Open Graph + Twitter Card com imagem preview dinamica mostrando preco atual
  4. `robots.txt` permite indexacao de `/rotas/*` e cada rota tem tag `rel="canonical"` apontando pra si mesma
  5. Botao "comprar" na pagina publica usa affiliate link Travelpayouts (monetizacao passiva por clique)
**Plans**: TBD
**UI hint**: yes

### Phase 34: Price Prediction Engine
**Goal**: Dashboard e email transformam historico em recomendacao acionavel ("Compre agora" / "Aguarde ate DD/MM" / "Monitorar") com hit rate comprovado retrospectivamente
**Depends on**: Phase 32
**Requirements**: PRED-01, PRED-02, PRED-03, PRED-04
**Success Criteria** (what must be TRUE):
  1. Dashboard exibe recomendacao por grupo em uma de tres classes: "Compre agora", "Aguarde ate DD/MM" ou "Monitorar"
  2. Cada recomendacao vem acompanhada de justificativa de 1 frase combinando janela otima, delta vs media 90d e volatilidade da rota
  3. Script `scripts/backtest_predictions.py` roda contra `route_cache` historico e reporta hit rate por classe; meta interna >=60% antes de promover copy
  4. Email consolidado exibe a recomendacao no topo do corpo (acima do preco atual)
**Plans**: TBD
**UI hint**: yes

### Phase 35: Onboarding Wizard
**Goal**: Usuario novo sai da landing com grupo ativo em menos de 30 segundos, sem jargao tecnico na copy
**Depends on**: Phase 32
**Requirements**: ONB-01, ONB-02, ONB-03
**Success Criteria** (what must be TRUE):
  1. Usuario novo apos OAuth (sem grupos) ve wizard de 2 passos perguntando destino e periodo aproximado, nao o dashboard vazio
  2. Ao final do wizard, sistema cria grupo automaticamente e redireciona para o dashboard ja populado com preco vindo do `route_cache`
  3. Copy do dashboard e do email consolidado foi revisada: sem jargao tecnico (ex: "balde fechando" substituido por "vagas acabando rapido")
**Condicional**: so executar se Phase 33 trouxer >=3 usuarios novos organicos
**Plans**: TBD
**UI hint**: yes

### Phase 36: Multi-Leg Trip Builder
**Goal**: Usuario monitora roteiro encadeado (ex: BR → Italia → Espanha → BR) em um unico grupo-pai, com sinal de compra aplicado sobre o preco total do encadeamento
**Depends on**: Phase 32 and Phase 34
**Requirements**: MULTI-01, MULTI-02, MULTI-03, MULTI-04
**Success Criteria** (what must be TRUE):
  1. Usuario cria grupo-pai com N trechos sequenciais via UI, cada trecho com origin, destination, janela de datas e min/max stay em dias
  2. Sistema valida encadeamento temporal: data de saida do trecho N+1 deve ser >= data de chegada do trecho N + min_stay (rejeita combinacoes invalidas)
  3. Sistema busca precos de cada trecho via cache/SerpAPI e calcula preco total do roteiro exibido no dashboard
  4. Sinal de compra e recomendacao de prediction sao aplicados sobre o preco total do encadeamento, nao trecho a trecho
**Plans**: 4 plans
- [x] 36-01-PLAN.md — Model RouteGroupLeg + FlightSnapshot.details + schemas Pydantic + migration Alembic + Wave 0 tests RED
- [x] 36-02-PLAN.md — multi_leg_service (produto cartesiano + cache-first) + branch polling_service + dedup multi
- [x] 36-03-PLAN.md — UI toggle + construtor dinamico JS vanilla + POST handler multi + edit.html
- [x] 36-04-PLAN.md — Dashboard card multi + pagina detalhe breakdown + email consolidado multi (D-19/D-20)
**UI hint**: yes

## Progress

**Execution Order:** Phase 15 -> 16 -> 17 -> 18 -> 19 -> 20 -> 21 -> 22 -> 23 -> 24 -> 25 -> 26 -> 27 -> 28 -> 29 -> 30 -> 31 -> 31.9 -> 32 -> 33 -> 34 -> 35 -> 36

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
| 10. PostgreSQL Foundation | v2.0 | 2/2 | Complete | 2026-03-28 |
| 11. Google OAuth | v2.0 | 3/3 | Complete | 2026-03-28 |
| 12. Data Isolation | v2.0 | 3/3 | Complete | 2026-03-29 |
| 13. Landing Page | v2.0 | 1/1 | Complete | 2026-03-30 |
| 14. Production Fixes | v2.0 | 1/1 | Complete | 2026-03-30 |
| 15. CI Pipeline | v2.1 | 0/? | Not started | - |
| 16. Passengers Fix | v2.1 | 0/? | Not started | - |
| 17. Price Labels | v2.1 | 0/? | Not started | - |
| 18. JWT Sessions | v2.1 | 0/? | Not started | - |
| 19. Rate Limiting | v2.1 | 0/? | Not started | - |
| 20. SerpAPI Cache | v2.1 | 0/? | Not started | - |
| 21. Legacy Removal | v2.1 | 0/? | Not started | - |
| 31.9. Price Fidelity Hygiene | v2.3 | 0/? | Not started | - |
| 32. Cache Layer Travelpayouts | v2.3 | 0/? | Not started | - |
| 33. Public Route Index (SEO) | v2.3 | 0/? | Not started | - |
| 34. Price Prediction Engine | v2.3 | 0/? | Not started | - |
| 35. Onboarding Wizard | v2.3 | 0/? | Not started | - |
| 36. Multi-Leg Trip Builder | v2.3 | 4/4 | Complete    | 2026-04-23 |
