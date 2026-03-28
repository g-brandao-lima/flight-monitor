# flight-monitor

Sistema pessoal de monitoramento de passagens aéreas. Busca preços automaticamente, detecta oportunidades de compra e envia alertas por email. Roda na nuvem 24h (Render + UptimeRobot), custo zero.

## Estrutura

| Pasta | Descrição |
|---|---|
| `app/routes/` | Rotas do dashboard (HTML) e API REST |
| `app/services/` | Lógica de negócio: polling, sinais, email, aeroportos |
| `app/templates/` | Templates Jinja2 (dark mode) |
| `app/data/` | Base de aeroportos (150+ IATA codes) |
| `app/models.py` | Tabelas SQLAlchemy (RouteGroup, FlightSnapshot, DetectedSignal) |
| `app/scheduler.py` | CronTrigger diário às 04:00 BRT |
| `tests/` | 188 testes automatizados (Pytest) |

## Stack

- Python 3.11 + FastAPI + SQLAlchemy + SQLite
- SerpAPI (Google Flights) para busca de preços
- Jinja2 + Chart.js + Flatpickr para o dashboard
- Gmail SMTP para alertas por email
- APScheduler com CronTrigger (polling diário às 04:00 BRT)
- Gunicorn para produção

## Deploy (nuvem)

Roda no Render (free tier) com UptimeRobot mantendo o servidor ativo 24h.

- **URL**: deploy via `render.yaml` (Blueprint)
- **Polling**: automático às 04:00 BRT via APScheduler CronTrigger
- **Keep-alive**: UptimeRobot pinga a cada 5 min pra evitar spin-down
- **Auto-deploy**: push no GitHub atualiza o Render automaticamente

## Como usar (local)

```bash
# Instalar
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Configurar (.env)
SERPAPI_API_KEY=sua_chave
GMAIL_SENDER=seu@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
GMAIL_RECIPIENT=seu@gmail.com

# Rodar
python main.py
# Acessar: http://localhost:8000
```

## O que faz

- **Grupos de Rota**: múltiplas origens/destinos, passageiros, paradas (direto/conexão), modo exploração
- **Polling**: busca preços via Google Flights 1x/dia às 04:00 BRT (ou manual pelo dashboard)
- **Sinais**: detecta preço abaixo do histórico e janela ótima de compra
- **Email**: 1 email consolidado por grupo com rota mais barata e top 3 datas
- **Dashboard**: dark mode, cards com preço, tendência, melhor dia da semana, sparkline, links Kayak/Skyscanner/Momondo
- **Autocomplete**: busca aeroporto por cidade ou código IATA
- **Insights**: tendência de preço (subindo/descendo), melhor dia da semana, melhor preço já visto

## Requisitos

- Python 3.10+
- Conta SerpAPI (grátis: 100 buscas/mês)
- Gmail com Senha de App (para alertas)

## Autor

**Gustavo Brandão** - [@g-brandao-lima](https://github.com/g-brandao-lima)
