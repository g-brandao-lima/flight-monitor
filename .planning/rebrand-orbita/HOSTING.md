# HOSTING — Análise de Alternativas ao Render Free

> Projeto: Órbita (ex-Flight Monitor) — FastAPI + Postgres + APScheduler in-process.
> Documento: decisão de hosting para fase de validação (~10-100 users) e transição para escala (>1k users).
> Data: 2026-04-20.

---

## 1. Resumo Executivo

**TL;DR (3 linhas):**
1. **Agora (validação):** migrar de Render free para **Fly.io pay-as-you-go** com 1 máquina `shared-cpu-1x` 256/512MB always-on (~US$2-4/mês). Mantém Neon Postgres free. Elimina cold start e preserva APScheduler in-process sem gambiarra de UptimeRobot.
2. **Fase escala (>1k users):** **Hetzner Cloud CX22** (~€4/mês, 2 vCPU / 4GB) com Docker Compose + Postgres local ou Neon Scale, Cloudflare na frente como CDN/WAF. Extrair scheduler para worker separado e emails para fila (RQ + Redis local no mesmo box).
3. **Não-recomendado como primário:** Vercel/Cloudflare Workers (serverless não combina com APScheduler in-process) e Koyeb free (dorme igual Render).

**Comparativo top 3 (1-glance):**

| Critério | Fly.io PAYG | Railway Hobby | Render Starter |
|---|---|---|---|
| Custo mensal estimado | ~US$2-5 | US$5 fixo + uso | US$7 fixo |
| Always-on | Sim (máquina dedicada) | Sim | Sim |
| Cold start | Zero | Zero | Zero |
| APScheduler in-process | OK (1 máquina, singleton) | OK | OK |
| Custom domain + SSL | Sim, grátis | Sim, grátis | Sim, grátis |
| Deploy git push | Sim (via GitHub Actions ou `fly deploy`) | Sim (nativo) | Sim (nativo) |
| Postgres gerenciado | Fly Postgres (MPG) ou Neon | Railway Postgres | Render Postgres (US$7) |
| Fit para este projeto | **9/10** | 8/10 | 7/10 |

---

## 2. Análise dos Candidatos

### 2.1 Render (atual) — free + Starter US$7
- **Preço:** free tier 750h/mês; Starter US$7 sempre-ligado; Postgres pago US$7.
- **Always-on:** só pago. Free dorme em 15min.
- **Cron in-process:** suportado, mas free mata o worker enquanto dorme.
- **Cold start:** 30-60s no free (confirmado pela comunidade, pior que os 2-5s percebidos).
- **CPU/RAM free:** 0.1 vCPU / 512MB (Starter: 0.5 vCPU / 512MB).
- **Postgres mesma plataforma:** sim, mas caro (US$7 após tier de 256MB).
- **Deploy git:** excelente.
- **Custom domain:** sim, grátis com cert automático.
- **Logs/observabilidade:** dashboard básico, retenção curta; precisa exportar.
- **Limitações:** singleton worker em planos baixos, CPU fraca para Pillow, banco free de 256MB caduca em 30 dias de inatividade.
- **Fit: 6/10** (Starter US$7 resolve 80% das dores, mas paga premium por pouco).

### 2.2 Fly.io — pay-as-you-go
- **Preço:** sem free tier novo desde out/2024. Trial 7 dias. `shared-cpu-1x 256MB` always-on ~US$1.94/mês; 512MB ~US$3.89/mês. Egress generoso incluído (~160GB no cluster).
- **Always-on:** sim, por padrão; `auto_stop_machines=false` no `fly.toml`.
- **Cron in-process:** ideal — 1 máquina persistente, APScheduler sobrevive.
- **Cold start:** zero com máquina travada up; ~300ms se habilitar scale-to-zero.
- **CPU/RAM:** shared-cpu-1x 256-2048MB configurável; CPU burst decente para Pillow em picos curtos.
- **Postgres:** Managed Postgres (MPG) ou continuar Neon. MPG starter ~US$5/mês single-node; Neon free cobre hoje.
- **Deploy git:** `fly deploy` local ou via GitHub Actions com `FLY_API_TOKEN`.
- **Custom domain:** sim, grátis, cert Let's Encrypt automático via `fly certs add`.
- **Logs:** `fly logs` tail live; integra com Axiom/Grafana free tier.
- **Limitações:** sem dashboard rico por default; billing PAYG exige cartão desde o primeiro byte; região mais próxima do BR é GRU (São Paulo, presente).
- **Fit: 9/10** — melhor custo/controle, região BR, always-on barato.

### 2.3 Railway — Hobby US$5/mês
- **Preço:** US$5 de assinatura que vira crédito de uso; excedente pay-as-you-go. Trial US$5 one-time.
- **Always-on:** sim.
- **Cron in-process:** OK.
- **Cold start:** zero.
- **CPU/RAM:** até 8 vCPU / 8GB por serviço; shared, medido por consumo real.
- **Postgres:** Railway Postgres provisionado no mesmo projeto, conexão por variável.
- **Deploy git:** nativo, webhook GitHub.
- **Custom domain:** sim, grátis.
- **Logs:** dashboard bom, live tail, retenção limitada sem addon.
- **Limitações:** métrica de uso pode estourar os US$5 se Pillow puxar CPU; egress cobrado. Região us-west/eu por padrão (latência BR ~180ms).
- **Fit: 8/10** — mais fácil de operar que Fly, um pouco mais caro e mais longe do BR.

### 2.4 Koyeb — free web service
- **Preço:** 1 web service free (0.1 vCPU / 512MB), 1GB transfer.
- **Always-on:** **não** — dorme por inatividade (reportado pela comunidade). Mesmo problema do Render free.
- **Cron in-process:** quebra ao dormir.
- **Cold start:** sim, similar ao Render.
- **Deploy/custom domain:** OK.
- **Fit: 3/10** — não resolve o problema central.

### 2.5 DigitalOcean App Platform — Basic US$5/mês
- **Preço:** US$5 Basic (512MB/1 vCPU shared), Postgres dev US$7.
- **Always-on:** sim.
- **Cron:** OK; DO tem Jobs separados, mas in-process funciona.
- **Cold start:** zero.
- **Custom domain/SSL:** grátis.
- **Deploy git:** bom, webhook GitHub.
- **Limitações:** preço do Postgres gerenciado sobe rápido; build minutes limitados no Basic; região NYC/SFO/AMS (sem BR).
- **Fit: 7/10** — sólido, mas paga o mesmo que Render Starter sem ganho claro.

### 2.6 AWS Lightsail — US$5/mês
- **Preço:** US$5 (512MB/2 vCPU/20GB SSD/1TB transfer). Postgres gerenciado à parte (US$15+).
- **Always-on:** sim (VPS).
- **Cron:** total liberdade.
- **Cold start:** zero.
- **Overhead admin:** alto — você gerencia OS, nginx, systemd, Let's Encrypt, updates, firewall.
- **Fit: 5/10** — bom preço, mas custo-hora humano maior que economia.

### 2.7 Hetzner Cloud — CX22 ~€4/mês (~US$4.5)
- **Preço:** CX22 2 vCPU / 4GB / 40GB SSD / 20TB traffic por €4,51/mês (AMD). CPX11 similar em Ashburn-US para latência BR.
- **Always-on:** sim.
- **Cron:** total liberdade; cabe app + Postgres local + Redis no mesmo box.
- **Cold start:** zero.
- **Custom domain/SSL:** via Caddy ou nginx + certbot.
- **Overhead admin:** **real** — setup ~4-6h inicial (Docker, Caddy, backup cron, UFW, fail2ban, monitoring). Depois ~1-2h/mês de manutenção (patches, logs).
- **Localização:** DCs em Falkenstein/Nuremberg/Helsinki/Ashburn/Hillsboro/Singapura. Ashburn para BR (~130ms).
- **Fit: 8/10 para fase escala, 6/10 para validação** — vale quando já se justifica o overhead.

### 2.8 Oracle Cloud Free Tier — Always Free VM
- **Preço:** zero. Ampere ARM 4 OCPU / 24GB grátis "para sempre" (A1 Flex).
- **Always-on:** sim.
- **Cron/Cold start:** liberdade total, zero cold start.
- **Postgres:** instalar local ou continuar Neon.
- **Deploy git:** via CI/CD manual (GitHub Actions → SSH).
- **Overhead admin:** igual a Hetzner.
- **Limitações críticas:** a Oracle tem histórico de **recuperar** instâncias Always Free por "inatividade" ou decisões unilaterais de capacidade, especialmente em regiões populares. Relatos frequentes de conta suspensa sem aviso. ARM exige builds multi-arch.
- **Fit: 5/10** — preço imbatível, mas risco operacional alto para algo que precisa estar up 100%.

### 2.9 Vercel — serverless
- **FastAPI:** roda via adapter (Mangum-like), mas cada request é uma função com cold start.
- **APScheduler in-process:** **incompatível** — não existe processo persistente. Teria que migrar para Vercel Cron (HTTP ping endpoints) ou externalizar.
- **Fit: 2/10** — quebra o requisito de cron in-process.

### 2.10 Cloudflare Workers (Python)
- **Python Workers:** em beta/GA limitado via Pyodide, sem suporte completo a libs nativas (Pillow provavelmente quebra — precisa de libs C). SQLAlchemy síncrono não cabe no modelo.
- **Cron triggers:** existem (cron triggers Worker), mas são invocações HTTP efêmeras, não um processo longo com estado.
- **Fit: 1/10** — impróprio para FastAPI + APScheduler + Pillow.

---

## 3. Recomendação Fase Atual (validação, <100 users)

**Provedor: Fly.io PAYG.**

### Justificativa
1. Custo esperado US$2-5/mês para 1 máquina `shared-cpu-1x` 512MB always-on em GRU (SP) — dentro do budget com folga.
2. Máquina dedicada = APScheduler in-process não dorme, elimina a gambiarra UptimeRobot.
3. Cold start zero com `auto_stop_machines=false`; se quiser economizar, deixar em `auto_start_machines=true` + min 1 máquina.
4. Região GRU baixa TTFB para SEO Googlebot BR.
5. CPU burst decente para Pillow em picos curtos (shared-cpu não é bare-metal, mas bate Render free e iguala Starter).

### Infra diagram
```
GitHub repo
   │ push main
   ▼
GitHub Actions (fly-deploy.yml, FLY_API_TOKEN secret)
   │ flyctl deploy
   ▼
Fly.io GRU
   └─ app "orbita"
       └─ 1x shared-cpu-1x 512MB always-on
          ├─ uvicorn (workers=2, --loop uvloop, --http httptools)
          ├─ APScheduler BackgroundScheduler (in-process)
          └─ Pillow OG generator (com cache em /data volume 1GB)
   │
   ▼ DATABASE_URL
Neon Postgres (free tier, mantido)
   └─ project "orbita-prod" us-east-1 ou sa-east-1 se existir
```

### Banco: manter Neon
- Neon free cobre até 0.5GB storage + compute autoscaling. Suficiente para 100-1k users.
- Migrar para Fly MPG só quando Neon free virar gargalo (provável gatilho: 300+ users ativos OU latência app↔db > 80ms).
- **Risco Neon:** banco free suspende após 5 dias de inatividade; acordar adiciona ~500ms no primeiro request. Mitigação: o próprio APScheduler rodando polling 2x/dia já mantém o banco quente.

### Custo mensal estimado
| Item | Custo |
|---|---|
| Fly machine 512MB always-on | ~US$3.89 |
| Fly volume 1GB (cache OG) | ~US$0.15 |
| Egress (baixo) | ~US$0 |
| Neon Postgres free | US$0 |
| Sentry dev free | US$0 |
| **Total** | **~US$4/mês** |

### Pros vs Render atual
- Sem cold start, sem keep-alive gambiarra.
- CPU burst maior que Render free, similar a Starter.
- Região BR (GRU) vs Render Oregon/Frankfurt = ~100ms TTFB a menos.
- Preço menor que Render Starter (US$4 vs US$7).

### Cons
- Fly exige cartão desde dia 1 (não tem free real).
- CLI `flyctl` tem curva pequena vs dashboard Render.
- Billing PAYG pede monitoramento de alertas (configurar spend cap no dashboard).

### Passos de migração (estimativa 2-3h)
1. `brew install flyctl` / equivalente Windows, `fly auth signup` ou `login`.
2. `fly launch --no-deploy` na raiz do projeto → gera `fly.toml` e `Dockerfile` (se não existir).
3. Ajustar `fly.toml`: `primary_region = "gru"`, `[[vm]] memory = "512mb"`, `auto_stop_machines = false`, `min_machines_running = 1`.
4. `fly volumes create ogcache --size 1 --region gru`, montar em `/data`.
5. `fly secrets set DATABASE_URL=... GOOGLE_CLIENT_ID=... GMAIL_APP_PASSWORD=... AUTHLIB_INSECURE_TRANSPORT=0`.
6. `fly deploy` — valida build e startup.
7. Smoke test: home, /rotas/, /auth/login, disparar um job APScheduler manual.
8. Adicionar GitHub Action `.github/workflows/fly.yml` com `superfly/flyctl-actions/setup-flyctl@master` + `flyctl deploy --remote-only`.
9. Apontar Render para "suspended" (manter rollback por 2 semanas).
10. Configurar billing alert em US$10/mês no Fly dashboard.

---

## 4. Recomendação Fase Escala (>1k users)

**Provedor alvo: Hetzner Cloud CX22 (ou CPX21) + Cloudflare front.**

### Por quê mudar
Em 1k+ users, o perfil muda:
- Polling 2x/dia começa a gerar picos de CPU longos (não mais "picos curtos").
- OG image generation pode virar hotpath (cache HIT ratio cai quando as URLs distintas explodem).
- Emails em fila começam a fazer sentido (Gmail SMTP limita 500/dia; alternativa SES).
- Backup precisa ser dedicado.

### Arquitetura proposta

```
Cloudflare (free) — DNS + CDN + WAF + cache edge para OG images
   │
   ▼
Hetzner CX22 (Ashburn, €4.51)
   ├─ Caddy (reverse proxy, SSL auto, HTTP/2)
   ├─ App container (FastAPI uvicorn 4 workers)
   ├─ Worker container (APScheduler dedicado, sem tráfego HTTP)
   ├─ Email worker (RQ consumer)
   ├─ Redis (cache + RQ queue)
   └─ Postgres 16 (local, ou manter Neon Scale ~US$19)

Backup: restic diário → Backblaze B2 (~US$0.005/GB)
Observability: Grafana Cloud free + Sentry
```

### Mudanças de código necessárias
1. **Scheduler separado:** extrair APScheduler para processo próprio (`python -m app.worker`), compartilhando mesmo codebase mas sem uvicorn. Evita contenção CPU com requests.
2. **Fila de email:** Gmail SMTP → `rq` + Redis. Email send vira `enqueue("send_digest", user_id)`.
3. **OG cache no Cloudflare:** headers `Cache-Control: public, max-age=86400, s-maxage=604800` + CF Rules para cachear rotas `/og/*`.
4. **Connection pool:** SQLAlchemy `pool_size=10, max_overflow=20, pool_pre_ping=True`.
5. **Health checks:** endpoint `/healthz` leve (sem DB) para liveness e `/readyz` (com DB) para readiness.

### Custo estimado
| Usuários | Infra | Custo/mês |
|---|---|---|
| 1k ativos | CX22 + Neon free + Cloudflare free + B2 | ~US$5 |
| 10k ativos | CPX31 (4 vCPU/8GB €15) + Neon Scale US$19 + B2 US$2 | ~US$36 |

Se > 10k ativos, considerar split app/db em duas VPS ou voltar a managed (Railway Pro ou Fly com MPG replicado).

---

## 5. Performance Quick Wins (aplicar AGORA, antes da migração)

Ordenado por impacto × esforço. Alvo: reduzir TTFB de ~500ms para <200ms e LCP para <1.5s.

### Alta prioridade (fazer esta semana)
1. **Uvicorn config** — `--workers 2 --loop uvloop --http httptools --proxy-headers --forwarded-allow-ips='*'` no `Procfile`/`Dockerfile`. Esforço: 10min. Impacto: ~20% RPS.
2. **Gzip middleware** — `app.add_middleware(GZipMiddleware, minimum_size=1024)`. Esforço: 5min. Impacto: -60% payload em HTML/JSON.
3. **Cache HTTP headers em rotas públicas** — já feito em `/rotas/` e `/sitemap.xml`. Estender para `/rotas/{slug}` (5min) e adicionar `ETag` via middleware.
4. **Lazy imports no startup** — mover Pillow, authlib providers e outros imports pesados para dentro das funções que os usam. Reduz cold start de ~2.5s para ~1s. Esforço: 30min.
5. **Connection pool SQLAlchemy** — `pool_pre_ping=True, pool_recycle=1800`. Evita conexões mortas com Neon. Esforço: 5min. Impacto: zera erros `OperationalError: server closed` aleatórios.

### Média prioridade (próximas 2 semanas)
6. **Auditar N+1** — rodar com `echo=True` em dev por 30min navegando as telas principais, anotar queries repetidas; aplicar `selectinload`/`joinedload`. Esforço: 2h. Impacto: 30-50% TTFB em páginas com listas.
7. **OG image cache em disco** — escrever PNG gerado em `/data/og/{hash}.png` com TTL 7 dias; servir direto. Esforço: 1h. Impacto: render vai de 400ms para 5ms em HIT.
8. **Otimização Pillow** — usar `JPEG quality=85 optimize=True progressive=True` onde for foto; PNG só onde tem transparência real. Esforço: 20min. Impacto: -50% bytes OG.
9. **Minify CSS inline** — `csscompressor` no build, ou mover CSS para arquivo estático cacheável. Esforço: 30min. Impacto: -30% HTML bytes.

### Baixa prioridade (só se virar gargalo)
10. **CDN Cloudflare na frente** — DNS proxy + page rules; OG images cacheadas no edge. Esforço: 1h. Impacto: TTFB global -200ms. Fazer junto com compra de domínio.
11. **Brotli** (além de gzip) — Cloudflare já faz automaticamente; no origin só se não usar CF.
12. **Skip OG síncrono** — ficar em `/data` é suficiente até 10k users; S3 só em escala.

---

## 6. Domínio

### Quando comprar
Gatilhos (qualquer um):
- Primeiros **10 usuários reais** (não seed/amigos) cadastrados.
- Primeiro click rastreado em link afiliado (prova de intenção de compra).
- Primeira visita orgânica do Google (prova de indexação).
- Se passar 60 dias sem nenhum gatilho, reavaliar o produto, não comprar domínio.

### Onde comprar
- **`.com.br`:** Registro.br (oficial, sem revendedor). ~R$40/ano. DNS pode ficar no Cloudflare via nameservers.
- **`.com`:** Cloudflare Registrar a preço de custo (~US$10/ano, sem markup) OU Porkbun (~US$10/ano, boa UX). **Evitar GoDaddy/Namecheap** pelo preço de renovação inflado.
- **Recomendação:** `.com` no Cloudflare Registrar — já integrado ao CDN, DNS e email routing.

### Reserva
- Reservar R$80 para o ano 1 (um `.com.br` + um `.com` se quiser proteger marca). Renovações anuais.

### Configuração no Fly.io
1. `fly certs add orbita.app` e `fly certs add www.orbita.app`.
2. No Cloudflare DNS: criar `A` record para o IPv4 do Fly + `AAAA` para IPv6 (proxy DESLIGADO inicialmente, até o cert emitir; depois pode religar).
3. Fly emite Let's Encrypt automático em ~30s.
4. Depois, ligar proxy Cloudflare (nuvem laranja) para ganhar CDN/WAF.

---

## 7. CDN + Anti-DDoS

### Cloudflare free
**Sim, ativar junto com a compra do domínio.** Pros:
- DNS rápido e grátis.
- SSL universal (além do origin cert Let's Encrypt).
- WAF básico + rate limiting grátis (10k requests/mês free).
- Cache edge automático para assets estáticos.
- Analytics grátis (substitui parcialmente Google Analytics para dados server-side).

Cons:
- Adiciona um hop (mas geralmente compensa no cache HIT).
- Algumas features (Page Rules ilimitadas, Image Resizing) são pagas.

### Cache de OG images no edge
Relevante quando SEO pegar tração (>1k impressões/dia no GSC). Configurar:
```
Cache Rule: URI Path matches /og/*
  → Cache Eligibility: Eligible for cache
  → Edge TTL: 7 days
  → Browser TTL: 1 day
```
Com isso, 95%+ dos OG bots (Twitter, Facebook, LinkedIn, WhatsApp, Telegram) pegam do edge e o origin nunca processa Pillow.

---

## 8. Observabilidade

- **Sentry:** manter. Plano Developer free cobre 5k errors/mês, suficiente.
- **Logs por provedor:**
  - Fly: `fly logs` live tail; exportar para Axiom free (500GB/mês) via log shipper.
  - Railway: dashboard nativo, retenção ~7 dias.
  - Hetzner: Docker logs + `loki` local ou Grafana Cloud free (50GB logs/mês).
- **Uptime:** substituir UptimeRobot por **BetterStack** free (10 monitors, check a cada 3min) ou **Healthchecks.io** free (20 checks) — este último é ótimo para validar que os cron jobs APScheduler de fato rodaram (ping de heartbeat no fim de cada job).
- **APM/traces:** **Sentry Performance** (já grátis no plano atual) cobre traces. Alternativa: Grafana Cloud free tier com Tempo (50GB traces/mês). Não vale assinar Datadog/New Relic nesta fase.

---

## 9. Cenário Pessimista

### Se Fly derrubar o projeto
- Fly nunca derrubou contas pagas sem aviso; risco baixo. Plano B: Railway Hobby em 30min (mesmo Dockerfile, só trocar `fly.toml` por `railway.json`).

### Se Neon perder o banco free
- Neon já faz snapshots diários (Point-in-Time Recovery 7 dias no free).
- **Backup adicional obrigatório:** cron diário `pg_dump` → volume Fly `/data/backups/` + upload semanal para Backblaze B2 (~US$0.005/GB). ~5 linhas num `backup.sh`.

### Se Oracle Free cair (não usaremos como primário, mas se virasse fallback)
- Assumir que vai cair a qualquer momento. Backup externo é obrigatório.

### Plano B rápido
Manter 1 script `deploy-anywhere.sh` que sobe o app em Railway OU Hetzner em < 1h a partir de backup recente. Testar esse plano a cada trimestre.

---

## 10. Ação Imediata

### 3 ações para esta semana
1. **Aplicar Quick Wins 1-5** no código (gzip, uvloop, lazy imports, pool, cache headers estendidos). ~2h total. Faz diferença em Render mesmo se a migração atrasar.
2. **Criar conta Fly.io, rodar `fly launch` em branch `infra/fly`**, deployar numa app de teste `orbita-stage`, validar APScheduler sobrevive 24h. ~3h.
3. **Configurar Healthchecks.io** para receber heartbeat dos 3 jobs APScheduler (polling, digest, cache). Substituir UptimeRobot. ~30min.

### 3 métricas para validar sucesso em 14 dias
1. **TTFB p50** em `/rotas/` — alvo < 200ms (hoje ~500ms no Render free com cold start).
2. **Cold start %** — alvo 0% (hoje ~5-10% dos requests pagam cold start).
3. **Cron skip rate** — alvo 0 jobs perdidos/semana (hoje ~1-2/semana por dormência).

Bônus: monitorar custo Fly real após 30 dias. Se > US$8 sem uso extraordinário, investigar (provável memória subdimensionada causando restarts ou egress descontrolado).

---

**Resumo operacional:** fazer os Quick Wins primeiro (valor independente do provedor), migrar para Fly.io em janela de fim de semana, manter Neon até o gargalo chegar, comprar domínio quando houver sinal de tração real, e deixar Hetzner como destino planejado de fase 2 — não prematuro.
