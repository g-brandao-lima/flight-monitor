# Stack Research: v2.1 Additions

**Domain:** Flight monitoring (v2.1 Clareza de Preco e Robustez)
**Researched:** 2026-04-03
**Confidence:** HIGH

## Stack Atual (permanece)

| Technology | Version | Purpose |
|------------|---------|---------|
| FastAPI | 0.115.12 | Web framework |
| SQLAlchemy | 2.0.40 | ORM |
| PostgreSQL (Neon) | - | Banco producao |
| SQLite | - | Banco testes |
| Alembic | 1.18.4 | Migrations |
| Authlib | 1.6.9 | Google OAuth |
| APScheduler | 3.11.2 | Polling cron jobs |
| Jinja2 | 3.1.6 | Templates |
| fast-flights | 2.2 | Google Flights scraper (primario) |
| google-search-results | 2.4.2 | SerpAPI client (fallback) |
| pytest | 8.3.5 | Testes |
| gunicorn | 23.0.0 | WSGI server producao |

## Novas Dependencias (v2.1)

### PyJWT

| Atributo | Valor |
|----------|-------|
| Package | `PyJWT>=2.8` |
| Proposito | Codificar/decodificar JWT para sessoes stateless |
| Por que este | Leve (~150KB), sem dependencias extras, recomendado pela doc oficial FastAPI. python-jose e alternativa mas mais pesada e menos mantida |
| Substitui | `itsdangerous` (signing de cookies para SessionMiddleware) |

### slowapi

| Atributo | Valor |
|----------|-------|
| Package | `slowapi>=0.1.9` |
| Proposito | Rate limiting por endpoint |
| Por que este | Unica opcao madura para FastAPI/Starlette. Baseado em flask-limiter (battle-tested). Suporta in-memory e Redis. Decorator pattern natural |
| Alternativa | Implementar manualmente com middleware. Nao vale a complexidade |

## Dependencias Removidas

| Package | Razao da remocao |
|---------|-----------------|
| `itsdangerous` | Era usado pelo SessionMiddleware para assinar cookies. JWT substitui. Nota: verificar se Authlib depende de itsdangerous internamente antes de remover do requirements.txt |

## Alternatives Considered

| Categoria | Escolhido | Alternativa | Por que nao |
|-----------|-----------|-------------|-------------|
| JWT | PyJWT | python-jose | python-jose tem manutencao irregular, PyJWT e mais ativo e leve |
| JWT | PyJWT | authlib JWT | Authlib tem capacidade JWT mas misturar OAuth e sessao no mesmo modulo aumenta acoplamento |
| Rate Limiting | slowapi | Middleware customizado | Reinventar a roda. slowapi ja resolve in-memory e Redis |
| Cache | Dict in-memory | Redis | Instancia unica no Render, Redis adicionaria custo e complexidade desnecessarios |
| Cache | Dict in-memory | Tabela PostgreSQL | I/O de banco para cache e contraproducente. Cache deve ser mais rapido que a fonte |
| CI | GitHub Actions | Nenhum (confiar no deploy) | Render faz autodeploy na main. Sem CI, testes quebrados vao para producao |

## Installation (pos v2.1)

```bash
# requirements.txt final (diff)
# ADICIONAR:
PyJWT>=2.8
slowapi>=0.1.9

# REMOVER (se nao for dependencia transitiva):
# itsdangerous==2.2.0
```

**Nota sobre itsdangerous:** Antes de remover, rodar `pip show itsdangerous` para verificar se Authlib ou outro pacote depende dele. Se sim, manter no requirements.txt.

## Config (novas env vars)

```bash
# .env.example (adicionar)
JWT_SECRET_KEY=gerar-com-openssl-rand-hex-32
JWT_EXPIRY_HOURS=168
```

## Sources

- [PyJWT PyPI](https://pypi.org/project/PyJWT/) - Versao e compatibilidade
- [slowapi PyPI](https://pypi.org/project/slowapi/) - Versao e compatibilidade
- [FastAPI JWT Docs](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/) - Recomendacao oficial de PyJWT
- [SlowAPI Docs](https://slowapi.readthedocs.io/) - Configuracao e uso
