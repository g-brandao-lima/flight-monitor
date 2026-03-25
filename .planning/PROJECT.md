# Flight Monitor

## What This Is

Sistema pessoal de monitoramento de passagens aéreas que rastreia a velocidade de fechamento dos baldes de inventário (booking classes) de voos para prever o momento ideal de compra ANTES que o preço suba — não depois. Para uso próprio, rodando localmente com deploy futuro no Fly.io.

## Core Value

Detectar o momento certo de comprar uma passagem antes que o preço suba, usando dados de inventário reais (booking classes via Amadeus API) que nenhum sistema consumer expõe ao usuário.

## Requirements

### Validated

(None yet — ship to validate)

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

**Alertas via Telegram**
- [ ] Alerta enviado quando sinal detectado com: grupo, rota específica, preço atual, contexto histórico, urgência
- [ ] Usuário pode responder /silenciar [grupo] para pausar alertas daquele grupo por 24h

**Dashboard Web (mínimo)**
- [ ] Lista todos os grupos com: melhor preço atual, rota mais barata e indicador de sinal ativo
- [ ] Clicando num grupo: histórico de preço das últimas 2 semanas (gráfico de linha)
- [ ] Formulário para adicionar / editar / desativar grupos
- [ ] Interface em português, simples e funcional

### Out of Scope

- Efetuar compra de passagens — fora do escopo, apenas monitoramento
- Web scraping — somente APIs oficiais (Amadeus)
- Hotéis, carros, multimodal — produto focado em voos
- Múltiplos usuários / autenticação — uso pessoal apenas
- Aplicativo mobile — web responsivo é suficiente
- Notificação por email ou WhatsApp — Telegram é suficiente
- Voos somente ida (one-way) — apenas roundtrip nesta versão
- Multi-tenant / SaaS — produto pessoal
- Integração Duffel/NDC — fase 2 se necessário

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
- Telegram Bot API para alertas (gratuito, push real no celular)

**Limitações conhecidas:**
- Amadeus free tier: ~2.000-3.000 calls/mês grátis; ~38 calls/dia por grupo ativo; comporta ~3-4 grupos no free tier com 2 pollings/dia
- Amadeus capeia contagem de assentos em 9 (não distingue 9 de 50)
- Companhias low-cost sem presença no GDS (Azul, Gol em algumas rotas) têm cobertura parcial

## Constraints

- **API**: Amadeus Self-Service free tier — 2.000 calls/mês; máximo ~4 grupos ativos com 2 pollings/dia
- **Stack**: Python, FastAPI, SQLite, APScheduler, Telegram Bot API — sem JavaScript framework no frontend
- **Infra**: Local first → Fly.io free tier; sem VPS pago nesta versão
- **Usuários**: Single-user, sem autenticação complexa
- **Scope**: Roundtrip only; voos GDS (não LCC direto)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| SQLite over PostgreSQL | Uso pessoal, volume pequeno, zero configuração, arquivo único fácil de backup | — Pending |
| APScheduler embedded (não Celery) | Single-user, sem necessidade de workers distribuídos | — Pending |
| FastAPI + Jinja2 (sem JS framework) | Interface mínima, sem complexidade de build | — Pending |
| Amadeus como fonte primária | Único que expõe availabilityClasses com contagem por booking class | — Pending |
| Telegram para alertas | API gratuita, push nativo no celular, sem app próprio | — Pending |
| Fly.io free tier para cloud | Zero custo, suporte a persistent volume para SQLite, sempre ativo | — Pending |
| Roundtrip only na v1 | Simplifica modelo de dados e lógica de busca; one-way pode ser fase 2 | — Pending |

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
*Last updated: 2026-03-24 after initialization*
