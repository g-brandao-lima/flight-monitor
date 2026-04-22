<!-- GSD:project-start source:PROJECT.md -->
## Project

**Órbita** (repositório ainda chamado `flight-monitor` por legado)

Produto web que monitora rotas aéreas cadastradas pelo usuário e avisa por email quando o preço está historicamente baixo. Público: viajantes BR. Rodando em produção no Fly.io (orbita-flights.fly.dev), multi-usuário com Google OAuth.

**Core Value:** Transformar dados de preço histórico em decisão acionável — "compre agora vs espere" — em vez de só mostrar "preço atual". Canal monetizado via affiliate Aviasales (marker 714304).

### Constraints

- **APIs de dados:** Travelpayouts (Aviasales Data API, free, bulk 4×/dia) como primária; SerpAPI (free 250/mês, refresh on-demand) como fallback. fast-flights removido.
- **Stack:** Python 3.11, FastAPI, Jinja2 SSR (sem framework JS), PostgreSQL Neon, APScheduler in-process.
- **Infra:** Fly.io máquina always-on em GRU (~US$4/mês). NUNCA escalar para múltiplas máquinas com scheduler ativo (duplica cron).
- **Escopo atual:** Roundtrip. Multi-trecho planejado (Phase 36).
- **Monetização:** affiliate Aviasales — usuário clica "Comprar", Órbita recebe comissão.

<!-- GSD:project-end -->

<!-- GSD:stack-start source:STACK.md -->
## Technology Stack

- FastAPI 0.115, uvicorn[standard] com uvloop, gunicorn
- SQLAlchemy 2.0 + Alembic 1.18
- PostgreSQL (Neon.tech free)
- Jinja2 + HTML/CSS, paleta Órbita (indigo-cyan duotone)
- Space Grotesk + JetBrains Mono (Google Fonts)
- Chart.js CDN (só em detalhe de grupo)
- APScheduler BackgroundScheduler
- Pillow (OG image dinâmica)
- Authlib (OAuth), SessionMiddleware (cookie assinado)
- slowapi (rate limit), Sentry SDK
- Travelpayouts Data API, SerpAPI

<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

- **pt-BR acentuação obrigatória** em texto visível (landing, emails, templates). Código/identificadores/URLs sem acento ("Orbita" OK no domínio, "Órbita" OK em prosa).
- **CSS tokens centralizados** em `base.html` (`--bg-0`, `--brand-500`, etc). Não usar hex hardcoded em templates novos.
- **SSR puro** — evitar adicionar JS framework. JS só pra interações pontuais (loading overlay, FAQ details nativo).
- **SDD + TDD** — spec → teste RED → implementação GREEN → refactor. Ver `.planning/` pra phases e plans.
- **Alembic sequencial** — revisions encadeadas, nunca edite migration publicada.
- **Atomic commits** — um escopo por commit com Conventional Commits (feat/fix/chore/docs/refactor).
- **Sem emojis** em código/commits/docs.
- **Travessão proibido** em copy. Usar ponto final ou vírgula.

<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Arquitetura em 3 camadas de preço:

1. **Cache in-memory 30min** (`flight_cache.py`) — mesmo ciclo de polling.
2. **Cache persistente 6h** (`route_cache` table, alimentado pelo cron Travelpayouts) — pré-populado das 28 rotas BR top.
3. **SerpAPI fallback** — só em cache miss de grupo ativo do usuário.

Páginas públicas `/rotas/{O}-{D}` servem **100% do banco**, zero API externa por pageview. Botão "Comprar agora" passa por `/comprar/O-D` (grava AffiliateClick) antes de 302 pro Aviasales.

Scheduler in-process com 4 jobs: polling 2×/dia, weekly digest, travelpayouts refresh 4×/dia.

<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Antes de usar Edit/Write direto, passar por comando GSD quando aplicável:

- `/gsd:quick` — fix rápido / doc update
- `/gsd:debug` — investigar bug
- `/gsd:execute-phase` — fase planejada
- `/gsd:plan-phase N` — planejar próxima fase

Plans e summaries vivem em `.planning/phases/`. Histórico anterior em `.planning/archive/`.

<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->
## Developer Profile

> Solo dev, PO 29 anos, BR. Valoriza: spec-first, commits atômicos, tom pt-BR direto sem jargão corporativo. Comunicação fora do código em pt-BR. Revisar sempre antes de `git push -f` ou destrutivo.
<!-- GSD:profile-end -->
