# Flight Monitor

Sistema de monitoramento de passagens aéreas com detecção inteligente de oportunidades de compra. Multi-usuário com login via Google, banco PostgreSQL na nuvem e alertas por email. Deploy no Render, custo zero.

**Produção:** https://flight-monitor-ly3p.onrender.com

## O que faz

- Monitora preços de voos 24h por dia via Google Flights (SerpAPI)
- Detecta quando o preço está abaixo do histórico ou quando a janela de compra é ideal
- Envia 1 email consolidado por grupo com a rota mais barata, melhores datas e resumo
- Dashboard dark mode com cards de preço, tendência, sparkline e indicador de quota
- Landing page pública com explicação do produto e login via Google OAuth

## Stack

| Camada | Tecnologia | Versão |
|--------|-----------|--------|
| Backend | Python + FastAPI | 3.11 / 0.115 |
| Banco (produção) | PostgreSQL via Neon.tech | 17 |
| Banco (testes) | SQLite in-memory | - |
| Migrations | Alembic | 1.18 |
| ORM | SQLAlchemy | 2.0 |
| Auth | Google OAuth via Authlib | 1.6 |
| Sessão | Starlette SessionMiddleware + itsdangerous | - |
| Frontend | Jinja2 + HTML/CSS (dark mode) | 3.1 |
| Gráficos | Chart.js (CDN) | 4.5 |
| Calendário | Flatpickr (CDN) | - |
| Fonte | Inter (Google Fonts) | - |
| Scheduler | APScheduler (CronTrigger) | 3.11 |
| API de voos | SerpAPI (Google Flights) | 2.4 |
| Email | Gmail SMTP (smtplib) | stdlib |
| Validação | Pydantic + pydantic-settings | 2.11 |
| Testes | Pytest | 8.3 |
| Deploy | Render (free tier) | - |
| Keep-alive | UptimeRobot | - |

## Arquitetura

```
Visitante ──► Landing Page (/) ──► "Entrar com Google" ──► Google OAuth
                                                              │
                                                              ▼
Usuário logado ──► Dashboard (/) ──► Grupos de Rota ──► Polling SerpAPI
                       │                                      │
                       ├── Meus Alertas                       ▼
                       ├── Detalhe (gráfico Chart.js)    Snapshots no PostgreSQL
                       └── Criar/Editar grupo                 │
                                                              ▼
                                                    Signal Detection
                                                              │
                                                              ▼
                                                    Email consolidado
                                                    (para o dono do grupo)
```

## Fluxo de operação

1. **Usuário cria conta** via Google OAuth (recebe email de boas-vindas)
2. **Cria um Grupo de Rota** com origens, destinos, datas, passageiros e paradas
3. **Polling automático** roda 1x/dia às 04:00 BRT (ou manual pelo dashboard)
4. **Para cada combinação** (origem x destino x janela de datas), chama a SerpAPI
5. **Salva snapshots** no PostgreSQL (preço, companhia, classificação LOW/MEDIUM/HIGH)
6. **Detecta sinais**: preço abaixo do histórico ou janela ótima de compra
7. **Envia email** consolidado para o email do Google do dono do grupo
8. **Dashboard** mostra cards com preço, tendência, melhor dia da semana, quota SerpAPI

## Funcionalidades

### Multi-usuário (v2.0)
- Login exclusivo via Google OAuth (um clique)
- Sessão persistente (cookie assinado, sem expiração)
- Isolamento completo de dados por usuário (user_id FK em route_groups)
- Alertas enviados para o email do Google de cada usuário
- Email de boas-vindas na criação da conta

### Monitoramento
- Múltiplas origens e destinos por grupo
- Passageiros, paradas (direto/conexão), modo exploração
- Deduplicação de snapshots (não salva o mesmo voo 2x no mesmo ciclo)
- Deduplicação de sinais (mesmo sinal não repete em 12h)

### Dashboard
- Cards com preço em destaque, borda colorida por classificação (verde/amarelo/vermelho)
- Summary bar com total de grupos, menor preço e próximo polling
- Tendência de preço (subindo/descendo/estável)
- Melhor dia da semana para comprar
- Sparkline de histórico
- Links diretos para Google Flights, Kayak, Skyscanner, Momondo
- Indicador de quota SerpAPI restante (X/250 buscas no mês)
- Página "Meus Alertas" com histórico de sinais por usuário

### Email
- 1 email consolidado por grupo (não 1 por sinal)
- Rota mais barata com preço, companhia e datas
- Top 3 melhores datas
- Resumo das demais rotas
- Link de silenciar alertas por 24h (token HMAC)
- Datas em formato brasileiro (dd/mm/aaaa)

### Landing page
- Hero com headline e CTA
- Seção "Como funciona" (3 passos)
- Seção "Por que somos diferentes" (3 cards com ícones SVG)
- CTA final com botão Google OAuth
- Dark mode coeso com o dashboard
- Responsiva (mobile-first)

## Banco de dados

PostgreSQL (Neon.tech) em produção, SQLite in-memory nos testes. Schema gerenciado por Alembic.

### Tabelas

| Tabela | Descrição |
|--------|-----------|
| `users` | Usuários (google_id, email, name, picture_url) |
| `route_groups` | Grupos de monitoramento (user_id FK, origens, destinos, datas) |
| `flight_snapshots` | Snapshots de preço coletados pelo polling |
| `detected_signals` | Sinais de oportunidade detectados |
| `api_usage` | Contador global de uso da SerpAPI por mês |
| `booking_class_snapshots` | Legado (Amadeus), mantida no schema |

## Estrutura de arquivos

```
flight-monitor/
├── main.py                         # FastAPI app + middlewares + scheduler
├── alembic.ini                     # Config Alembic
├── alembic/
│   ├── env.py                      # Lê DATABASE_URL do ambiente
│   └── versions/                   # Migrations (baseline + users + user_id + api_usage)
├── app/
│   ├── config.py                   # Settings via pydantic-settings (.env)
│   ├── database.py                 # Engine condicional (SQLite/PostgreSQL)
│   ├── models.py                   # 6 tabelas ORM (User, RouteGroup, etc.)
│   ├── schemas.py                  # Validação Pydantic para API REST
│   ├── scheduler.py                # APScheduler CronTrigger (04:00 BRT)
│   ├── auth/
│   │   ├── oauth.py                # Authlib OAuth client (Google OIDC)
│   │   ├── routes.py               # /auth/login, /auth/callback, /auth/logout
│   │   ├── middleware.py           # AuthMiddleware global (protege rotas)
│   │   └── dependencies.py        # get_current_user (Depends)
│   ├── routes/
│   │   ├── dashboard.py            # Páginas HTML + landing page condicional
│   │   ├── route_groups.py         # API REST JSON (CRUD grupos)
│   │   └── alerts.py               # Silenciar alertas via HMAC token
│   ├── services/
│   │   ├── serpapi_client.py       # Wrapper SerpAPI (voos + price insights)
│   │   ├── polling_service.py      # Orquestra polling + quota guard
│   │   ├── snapshot_service.py     # Salva snapshots + deduplicação
│   │   ├── signal_service.py       # Detecta sinais de compra
│   │   ├── alert_service.py        # Email consolidado + boas-vindas + HMAC
│   │   ├── dashboard_service.py    # Queries de agregação (dialect-agnostic)
│   │   ├── quota_service.py        # Contador global SerpAPI
│   │   ├── airport_service.py      # Busca aeroportos por IATA/cidade
│   │   └── route_group_service.py  # Limite de 10 grupos ativos
│   ├── templates/
│   │   ├── base.html               # Layout base (header, auth condicional)
│   │   ├── landing.html            # Landing page pública
│   │   ├── error.html              # Página de erro amigável
│   │   └── dashboard/
│   │       ├── index.html          # Dashboard (cards, summary, quota)
│   │       ├── detail.html         # Detalhe com Chart.js
│   │       ├── create.html         # Formulário criar grupo
│   │       ├── edit.html           # Formulário editar grupo
│   │       └── alerts.html         # Meus Alertas (histórico)
│   └── data/
│       └── airports.json           # ~150 aeroportos (IATA, cidade, país)
├── tests/                          # 221 testes automatizados
│   ├── conftest.py                 # Fixtures (SQLite in-memory, auth mock)
│   └── test_*.py                   # 21 arquivos de teste
├── render.yaml                     # Blueprint Render (build + env vars)
├── requirements.txt                # Dependências Python
└── runtime.txt                     # Python 3.11 para Render
```

## Configuração

### Desenvolvimento local (.env)

```env
DATABASE_URL=sqlite:///./flight_monitor.db
SERPAPI_API_KEY=sua_chave_aqui
GMAIL_SENDER=seu@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
GMAIL_RECIPIENT=seu@gmail.com
GOOGLE_CLIENT_ID=seu_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxx
SESSION_SECRET_KEY=qualquer-string-para-dev
APP_BASE_URL=http://localhost:8000
```

### Produção (Render env vars)

| Variável | Descrição |
|----------|-----------|
| `DATABASE_URL` | Connection string PostgreSQL (Neon.tech, prefixo `postgresql+psycopg://`) |
| `SERPAPI_API_KEY` | Chave da SerpAPI (free tier: 250 buscas/mês) |
| `GMAIL_SENDER` | Email Gmail para enviar alertas |
| `GMAIL_APP_PASSWORD` | Senha de app do Gmail (requer 2FA) |
| `GMAIL_RECIPIENT` | Fallback para alertas (grupos sem user_id) |
| `GOOGLE_CLIENT_ID` | OAuth client ID (Google Cloud Console) |
| `GOOGLE_CLIENT_SECRET` | OAuth client secret |
| `SESSION_SECRET_KEY` | Chave para assinar cookies de sessão |
| `APP_BASE_URL` | URL de produção (ex: `https://flight-monitor-ly3p.onrender.com`) |

## Como rodar localmente

```bash
# Clonar
git clone https://github.com/g-brandao-lima/flight-monitor.git
cd flight-monitor

# Ambiente virtual
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Linux/Mac

# Dependências
pip install -r requirements.txt

# Configurar .env (copiar de .env.example)

# Criar banco e migrations
alembic upgrade head

# Rodar
python main.py
# Acessar: http://localhost:8000
```

## Testes

```bash
python -m pytest tests/ -v          # Suite completa (221 testes)
python -m pytest tests/ -x -q       # Parar no primeiro erro
python -m pytest tests/test_auth.py  # Só testes de auth
```

Testes rodam com SQLite in-memory (sem dependência de PostgreSQL).

## Deploy

O Render faz deploy automático a cada push no GitHub.

- **Build:** `pip install -r requirements.txt && alembic upgrade head`
- **Start:** `gunicorn main:app -w 1 -k uvicorn.workers.UvicornWorker --forwarded-allow-ips="*"`
- **Keep-alive:** UptimeRobot pinga `HEAD /` a cada 5 minutos
- **Polling:** APScheduler CronTrigger às 04:00 BRT (07:00 UTC)

## Limites

- **SerpAPI free tier:** 250 buscas/mês (renova no dia de criação da conta)
- **Neon.tech free tier:** 0.5 GB storage, 100 CU-hrs/mês, scales to zero quando inativo
- **Render free tier:** spin-down após 15min inatividade (UptimeRobot mitiga)
- **Sinais ativos:** PRECO_ABAIXO_HISTORICO e JANELA_OTIMA
- **Companhias:** cobertura parcial de low-cost (Azul, Gol em algumas rotas)

## Histórico de versões

| Versão | Data | O que entregou |
|--------|------|---------------|
| v1.0 | 2026-03-25 | Foundation, Data Collection, Signal Detection, Gmail Alerts, Web Dashboard |
| v1.1 | 2026-03-26 | Email consolidado, datas BR, feedback UX, página de erro, fix duplicatas |
| v1.2 | 2026-03-28 | Visual polish (dark mode profissional, cards, tipografia, cores semânticas) |
| v2.0 | 2026-03-30 | Multi-usuário: PostgreSQL, Google OAuth, isolamento de dados, landing page, quota SerpAPI, email de boas-vindas |

## Autor

**Gustavo Brandão** - [@g-brandao-lima](https://github.com/g-brandao-lima)
