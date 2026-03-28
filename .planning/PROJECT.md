# Flight Monitor

## What This Is

Sistema de monitoramento de passagens aereas que rastreia precos e sinais de oportunidade de compra usando dados de inventario (booking classes) e price insights. Multi-usuario com login via Google OAuth, deploy no Render com PostgreSQL persistente.

## Core Value

Detectar o momento certo de comprar uma passagem antes que o preço suba, usando dados de inventário reais (booking classes via Amadeus API) que nenhum sistema consumer expõe ao usuário.

## Requirements

### Validated

**Phase 11 (Google OAuth) — validated 2026-03-28**
- Login via Google OAuth com um clique (Authlib + OIDC)
- Sessao persistente via cookie assinado (sem expiracao, ate logout)
- Logout visivel em todas as paginas, limpa sessao
- Header exibe nome e foto do Google (iniciais quando sem foto)
- Middleware global protege rotas, flash message para nao logados
- 202 testes passando (14 novos de auth)

**Phase 10 (PostgreSQL Foundation) — validated 2026-03-28**
- Sistema usa PostgreSQL (Neon.tech) em producao, SQLite in-memory nos testes
- Alembic gerencia todas as migrations de schema (baseline com 4 tabelas)
- 188 testes continuam passando com SQLite in-memory sem alteracao

**Phase 1 (Foundation) — validated 2026-03-25**
- Aplicação inicia com um único comando e responde em localhost
- Banco SQLite criado automaticamente com todas as tabelas
- Grupos de Rota: criação, edição, ativação/desativação, deleção via API
- Sistema rejeita criação de 11º grupo ativo
- Validação de IATA codes, duração mínima, campos obrigatórios

### Active

**Grupos de Rotas**
- [ ] Usuário pode criar um "Grupo de Rota" com: nome, lista de aeroportos de origem (múltiplos IATA), lista de aeroportos de destino (múltiplos IATA), duração da viagem em dias (roundtrip), e período de viagem (mês específico ou intervalo de datas)
- [ ] Usuário pode definir preço-alvo opcional por grupo
- [ ] Usuário pode ativar e desativar grupos sem deletar
- [ ] Máximo de 10 grupos ativos (limitação do free tier Amadeus ~2.000 calls/mês)

**Coleta de Dados**
- [ ] Polling a cada 6 horas via APScheduler para cada grupo ativo
- [ ] Por polling: busca as 5 combinações mais baratas de (origem × destino × data_ida × data_volta) no período configurado
- [ ] Para cada combinação, captura booking class inventory (Y7 B4 M3...) via Amadeus Flight Availabilities Search
- [ ] Captura classificação histórica do preço (LOW / MEDIUM / HIGH) via Amadeus Flight Price Analysis
- [ ] Persiste todos os snapshots no banco com timestamp

**Sinais Detectados**
- [ ] BALDE FECHANDO: classe K ou Q passou de >=3 para <=1 vs. snapshot anterior — urgência ALTA
- [ ] BALDE REABERTO: classe que estava em 0 voltou a ter assentos — urgência MÁXIMA
- [ ] PREÇO ABAIXO DO HISTÓRICO: Amadeus retorna LOW + preço atual abaixo da média dos snapshots — urgência MÉDIA
- [ ] JANELA ÓTIMA: dias antes do voo entrou na faixa ideal para o tipo de rota — urgência MÉDIA

**Alertas via Gmail**
- [ ] Alerta enviado por email quando sinal detectado com: grupo, rota específica, preço atual, contexto histórico, urgência
- [ ] Email contém link de silenciar que pausa alertas daquele grupo por 24h ao ser clicado

**Dashboard Web (mínimo)**
- [ ] Lista todos os grupos com: melhor preço atual, rota mais barata e indicador de sinal ativo
- [ ] Clicando num grupo: histórico de preço das últimas 2 semanas (gráfico de linha)
- [ ] Formulário para adicionar / editar / desativar grupos
- [ ] Interface em português, simples e funcional

### Out of Scope

- Efetuar compra de passagens — apenas monitoramento
- Web scraping — somente APIs oficiais
- Hoteis, carros, multimodal — produto focado em voos
- Aplicativo mobile — web responsivo e suficiente
- Telegram / WhatsApp — Gmail resolve; Telegram silenciado pelo usuario
- Voos somente ida (one-way) — apenas roundtrip nesta versao
- Integracao Duffel/NDC — fase futura se necessario
- Login com email/senha — apenas Google OAuth no v2.0
- Plano pago SerpAPI — free tier compartilhado por enquanto

## Context

**Por que este produto existe:**
Sistemas consumer (Google Flights, Kayak) são reativos: alertam quando o preço caiu, mas o usuário já perdeu o momento ideal. A Amadeus API expõe dados de booking class availability (Y7 B4 M3...) que revelam a velocidade de enchimento do voo. Quando um balde barato reabre (estava em 0, volta a ter assentos), o algoritmo da companhia está ativamente estimulando demanda — esse é o momento de menor preço e menor duração, e nenhum app consumer expõe esse sinal.

**Contexto técnico construído antes do projeto:**
- Pesquisa aprofundada de Revenue Management / Yield Management realizada
- Amadeus Self-Service API validada: expõe `availabilityClasses` com booking class + contagem (capada em 9)
- Duffel API pesquisada como fonte NDC secundária futura
- SerpApi Google Flights pesquisada para confirmação de sinais

**Infraestrutura:**
- Rodar local inicialmente; deploy em Fly.io free tier quando estável
- SQLite via SQLAlchemy (arquivo único, zero infra, fácil migração)
- Gmail SMTP para alertas (senha de app do Google, zero custo)

**Limitações conhecidas:**
- Amadeus free tier: ~2.000-3.000 calls/mês grátis; ~38 calls/dia por grupo ativo; comporta ~3-4 grupos no free tier com 2 pollings/dia
- Amadeus capeia contagem de assentos em 9 (não distingue 9 de 50)
- Companhias low-cost sem presença no GDS (Azul, Gol em algumas rotas) têm cobertura parcial

## Constraints

- **API**: SerpAPI free tier (250 buscas/mes) compartilhada entre usuarios
- **Stack**: Python, FastAPI, PostgreSQL, APScheduler, Jinja2 — sem JS framework no frontend
- **Infra**: Render (web) + Neon.tech (PostgreSQL) — ambos free tier
- **Auth**: Google OAuth exclusivo (Google Cloud Console)
- **Scope**: Roundtrip only; voos GDS (nao LCC direto)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| SQLite over PostgreSQL | Uso pessoal, volume pequeno, zero configuracao | ⚠️ Revisit — migrando para PostgreSQL no v2.0 |
| APScheduler embedded (nao Celery) | Single-user, sem necessidade de workers distribuidos | ✓ Good |
| FastAPI + Jinja2 (sem JS framework) | Interface minima, sem complexidade de build | ✓ Good |
| SerpAPI como fonte primaria | Google Flights data via API, price insights incluidos | ✓ Good |
| Gmail para alertas | Usuario ja usa, volume baixo de alertas | ✓ Good |
| Render para deploy | Free tier, build automatico do GitHub | ✓ Good |
| Roundtrip only | Simplifica modelo de dados e logica de busca | ✓ Good |
| Google OAuth exclusivo (v2.0) | Sem gerenciar senhas, setup mais simples, usuarios ja tem Google | — Pending |
| PostgreSQL via Neon.tech (v2.0) | Persistencia entre deploys, multi-usuario, free tier generoso | — Pending |

## Current Milestone: v2.0 Multi-usuario

**Goal:** Transformar o Flight Monitor de ferramenta pessoal em produto multi-usuario com landing page publica, login via Google OAuth e banco PostgreSQL persistente.

**Target features:**
- Landing page minimalista (about + diferencial vs Google Flights/Skyscanner)
- Login exclusivo via Google OAuth
- Migracao SQLite para PostgreSQL (Neon.tech free tier)
- Multi-usuario com isolamento de dados por usuario
- Redesign das telas autenticadas

## Evolution

Este documento evolui a cada transição de fase e milestone.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-03-28 after Phase 11 completion*
