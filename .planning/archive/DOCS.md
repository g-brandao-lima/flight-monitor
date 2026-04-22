# Flight Monitor - Documentação Técnica

## O que é

Sistema de monitoramento de passagens aéreas que rastreia preços e sinais de oportunidade de compra via Google Flights (SerpAPI). Multi-usuário com login via Google OAuth, banco PostgreSQL persistente (Neon.tech), dashboard dark mode e alertas por email. Deploy no Render, custo zero.

---

## Stack Tecnológica

| Camada | Tecnologia | Versão | Pra quê |
|--------|-----------|--------|---------|
| Backend | Python + FastAPI | 3.11 / 0.115 | API e servidor web |
| Banco (prod) | PostgreSQL via Neon.tech | 17 | Dados persistentes entre deploys |
| Banco (testes) | SQLite in-memory | - | Testes rápidos sem infra externa |
| Migrations | Alembic | 1.18 | Gerenciamento de schema |
| ORM | SQLAlchemy | 2.0.40 | Mapeamento objeto-relacional |
| Auth | Authlib (Google OAuth OIDC) | 1.6.9 | Login com Google em um clique |
| Sessão | SessionMiddleware + itsdangerous | 2.2.0 | Cookie assinado, persistente |
| Frontend | Jinja2 + HTML/CSS | 3.1.6 | Dashboard e landing page (dark mode) |
| Gráficos | Chart.js (CDN) | 4.5.1 | Histórico de preços |
| Calendário | Flatpickr (CDN) | - | Date picker nos formulários |
| Fonte | Inter (Google Fonts) | - | Tipografia moderna |
| Scheduler | APScheduler (CronTrigger) | 3.11.2 | Polling diário às 04:00 BRT |
| API de voos | SerpAPI (Google Flights) | 2.4.2 | Busca preços e disponibilidade |
| Email | Gmail SMTP (smtplib) | stdlib | Alertas + boas-vindas |
| Validação | Pydantic + pydantic-settings | 2.11.1 | Schemas e configuração via .env |
| Testes | Pytest + HTTPX | 8.3.5 / 0.28.1 | 221 testes automatizados |
| Deploy | Render + Gunicorn | 23.0.0 | Produção free tier |
| Keep-alive | UptimeRobot | - | Pinga HEAD / a cada 5min |

---

## Fluxo de Operação

```
1. Visitante acessa a URL
   (não logado = landing page, logado = dashboard)
        |
        v
2. Login via Google OAuth (Authlib + OIDC)
   → Cria conta no banco + email de boas-vindas (primeiro acesso)
   → Sessão via cookie assinado (sem expiração)
        |
        v
3. Usuário cria um Grupo de Rota no dashboard
   (origens, destinos, datas, passageiros, paradas)
        |
        v
4. A cada 24h, o Scheduler dispara o polling
   (ou o usuário clica "Buscar agora")
   → Verifica quota SerpAPI antes de iniciar
        |
        v
5. O Polling Service gera combinações:
   origem x destino x datas (a cada 7 dias no período)
        |
        v
6. Pra cada combinação, chama a SerpAPI:
   1 chamada = voos + price insights
   → Incrementa contador de quota
        |
        v
7. Salva FlightSnapshots no PostgreSQL
   (preço, companhia, classificação LOW/MEDIUM/HIGH)
   → Deduplicação: não salva o mesmo voo 2x no mesmo ciclo
        |
        v
8. Signal Service analisa os snapshots:
   - PRECO_ABAIXO_HISTORICO: preço atual < média dos últimos 14 snapshots
   - JANELA_OTIMA: falta 21-90 dias (doméstico) ou 30-120 (internacional)
   → Deduplicação: mesmo sinal não repete em 12h
        |
        v
9. Se detectou sinal, envia 1 email consolidado por grupo
   (para o email do Google do dono, não mais para GMAIL_RECIPIENT fixo)
   (rota mais barata, top 3 datas, resumo, link de silenciar)
        |
        v
10. Dashboard mostra tudo: cards com preço, badge de sinal,
    tendência, sparkline, quota SerpAPI restante,
    links Google Flights/Kayak/Skyscanner/Momondo
```

---

## Autenticação e Multi-usuário

### Google OAuth (Authlib)

- Login via `/auth/login` → redirect para Google → callback `/auth/callback`
- Authlib com OIDC auto-discovery (não precisa configurar endpoints manualmente)
- Scopes: `openid`, `email`, `profile`
- Sessão: `SessionMiddleware` com `max_age=1 ano`, `httpOnly`, `https_only` em produção

### Middleware global

- `AuthMiddleware` protege todas as rotas por padrão
- Exceções (rotas públicas): `/`, `/auth/*`, `HEAD /` (UptimeRobot)
- Visitante não logado → redirect para `/?msg=login_required` com flash message

### Isolamento de dados

- `user_id` FK na tabela `route_groups` (child tables herdam via FK chain)
- Todas as queries em `dashboard_service.py` filtram por `user_id`
- Rotas de detalhe/edição verificam ownership (`group.user_id != user.id` → 404)
- Teste automatizado com 2 usuários confirma isolamento completo

### Email de boas-vindas

- Dispara apenas na criação da conta (primeiro login)
- Design dark mode coeso com o produto
- Contém: saudação com nome, o que o Flight Monitor faz, CTA "Criar meu primeiro grupo"
- Falha no envio é silenciosa (não bloqueia o login)

---

## Banco de Dados

PostgreSQL 17 (Neon.tech) em produção. SQLite in-memory nos testes. Schema gerenciado por Alembic.

### Tabela: users
Usuários autenticados via Google OAuth.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| id | INTEGER PK | Identificador |
| google_id | VARCHAR UNIQUE | Sub ID do Google (único por conta) |
| email | VARCHAR | Email do Google |
| name | VARCHAR | Nome completo do Google |
| picture_url | VARCHAR (null) | URL da foto do perfil |
| created_at | DATETIME | Data de criação |

### Tabela: route_groups
Grupos de monitoramento criados pelo usuário.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| id | INTEGER PK | Identificador |
| user_id | INTEGER FK (null) | Dono do grupo (users.id) |
| name | VARCHAR(100) | Nome do grupo (ex: "SP Setembro") |
| origins | JSON | Lista de códigos IATA de origem |
| destinations | JSON | Lista de códigos IATA de destino |
| duration_days | INTEGER | Duração da viagem em dias |
| travel_start | DATE | Início do período de viagem |
| travel_end | DATE | Fim do período de viagem |
| target_price | FLOAT (null) | Preço-alvo opcional |
| passengers | INTEGER | Número de passageiros (padrão: 1) |
| max_stops | INTEGER (null) | null=qualquer, 0=direto, 1=até 1 conexão |
| is_active | BOOLEAN | Se o grupo está ativo para polling |
| silenced_until | DATETIME (null) | Até quando os alertas estão silenciados |
| created_at | DATETIME | Data de criação |
| updated_at | DATETIME | Última atualização |

### Tabela: flight_snapshots
Cada voo encontrado pelo polling.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| id | INTEGER PK | Identificador |
| route_group_id | INTEGER FK | Grupo que gerou este snapshot |
| origin | VARCHAR(3) | Código IATA de origem |
| destination | VARCHAR(3) | Código IATA de destino |
| departure_date | DATE | Data de ida |
| return_date | DATE | Data de volta |
| price | FLOAT | Preço em BRL (ida e volta, 1 passageiro) |
| currency | VARCHAR(3) | Moeda (sempre "BRL") |
| airline | VARCHAR(2) | Companhia aérea |
| price_min | FLOAT (null) | Menor preço (price insights) |
| price_first_quartile | FLOAT (null) | Limite inferior da faixa típica |
| price_median | FLOAT (null) | Mediana da faixa típica |
| price_third_quartile | FLOAT (null) | Limite superior da faixa típica |
| price_max | FLOAT (null) | Maior preço (price insights) |
| price_classification | VARCHAR(10) (null) | LOW, MEDIUM ou HIGH |
| collected_at | DATETIME | Timestamp da coleta |

### Tabela: detected_signals
Sinais de oportunidade detectados.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| id | INTEGER PK | Identificador |
| route_group_id | INTEGER FK | Grupo relacionado |
| flight_snapshot_id | INTEGER FK | Snapshot que gerou o sinal |
| origin | VARCHAR(3) | Origem |
| destination | VARCHAR(3) | Destino |
| departure_date | DATE | Data de ida |
| return_date | DATE | Data de volta |
| signal_type | VARCHAR(30) | PRECO_ABAIXO_HISTORICO ou JANELA_OTIMA |
| urgency | VARCHAR(10) | MEDIA |
| details | VARCHAR(500) | Detalhes do sinal |
| price_at_detection | FLOAT | Preço no momento da detecção |
| detected_at | DATETIME | Timestamp da detecção |

### Tabela: api_usage
Contador global de uso da SerpAPI por mês.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| id | INTEGER PK | Identificador |
| year_month | VARCHAR UNIQUE | Mês no formato "2026-03" |
| search_count | INTEGER | Número de buscas realizadas |
| updated_at | DATETIME | Última atualização |

### Tabela: booking_class_snapshots (legado)
Herdada do Amadeus. Não utilizada com SerpAPI. Mantida no schema.

---

## Configuração (.env)

```env
# Banco (SQLite local, PostgreSQL em produção)
DATABASE_URL=sqlite:///./flight_monitor.db

# SerpAPI
SERPAPI_API_KEY=sua_chave_aqui

# Gmail (alertas + boas-vindas)
GMAIL_SENDER=seu@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
GMAIL_RECIPIENT=seu@gmail.com

# Google OAuth
GOOGLE_CLIENT_ID=seu_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxx
SESSION_SECRET_KEY=qualquer-string-para-dev

# URL base (para links de silenciar alerta no email)
APP_BASE_URL=http://localhost:8000
```

### Obtenção das credenciais

- **SERPAPI_API_KEY**: https://serpapi.com (free tier: 250 buscas/mês)
- **GMAIL_APP_PASSWORD**: Google > Segurança > Senhas de app (requer 2FA)
- **GOOGLE_CLIENT_ID/SECRET**: Google Cloud Console > APIs & Services > Credentials > OAuth client
- **DATABASE_URL (produção)**: Neon.tech > Project > Connection string (prefixo `postgresql+psycopg://`)

---

## Como Rodar

```bash
cd flight-monitor
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
alembic upgrade head           # Cria tabelas
python main.py                 # http://localhost:8000
```

---

## Testes

```bash
python -m pytest tests/ -v     # 221 testes, ~5 segundos
```

Testes usam SQLite in-memory com fixtures de autenticação (`test_user`, `authenticated_client`). Não dependem de PostgreSQL, SerpAPI ou Gmail.

---

## Deploy (Render)

Configurado via `render.yaml`. Auto-deploy a cada push no GitHub.

- **Build:** `pip install -r requirements.txt && alembic upgrade head`
- **Start:** `gunicorn main:app -w 1 -k uvicorn.workers.UvicornWorker --forwarded-allow-ips="*"`
- **Env vars:** DATABASE_URL, SERPAPI_API_KEY, GMAIL_*, GOOGLE_*, SESSION_SECRET_KEY, APP_BASE_URL

---

## Limites

| Recurso | Limite | Impacto |
|---------|--------|---------|
| SerpAPI free tier | 250 buscas/mês | ~2 grupos com polling diário |
| Neon.tech free tier | 0.5 GB, 100 CU-hrs | Suficiente para uso pessoal |
| Render free tier | Spin-down após 15min | UptimeRobot mantém ativo |
| Sinais ativos | PRECO_ABAIXO_HISTORICO, JANELA_OTIMA | 2 tipos de detecção |
| Companhias | Cobertura parcial low-cost | Azul, Gol parciais no GDS |

---

## Histórico de Versões

| Versão | Data | Fases | Testes | O que entregou |
|--------|------|-------|--------|---------------|
| v1.0 | 2026-03-25 | 1-5 | 188 | Foundation, Data Collection, Signal Detection, Gmail Alerts, Web Dashboard |
| v1.1 | 2026-03-26 | 6-8 | 188 | Email consolidado, datas BR, feedback UX, página de erro, deduplicação |
| v1.2 | 2026-03-28 | 9 | 188 | Visual polish (dark mode profissional, cards, tipografia, cores semânticas) |
| v2.0 | 2026-03-30 | 10-14 | 221 | Multi-usuário: PostgreSQL, Google OAuth, isolamento de dados, landing page, quota SerpAPI, email de boas-vindas |
