# Resume Context — Próxima sessão começa por aqui

**Última atualização:** 2026-04-22 (fim da sessão de rebrand Órbita)

## Estado do produto

- **Nome:** Órbita (rebrand recente do Flight Monitor)
- **Produção:** https://orbita-flights.fly.dev (Fly.io GRU, always-on)
- **Repo:** github.com/g-brandao-lima/{nome-novo} — usuário renomeou no GitHub mas pasta local ainda é `flight-monitor`
- **Status v2.3:** 3 de 6 fases shipped (31.9, 32, 33). Falta 34 e 36 (Phase 35 Onboarding é condicional).

## O que a Órbita faz hoje

1. Monitora rotas cadastradas pelo usuário (login Google OAuth)
2. Cron Travelpayouts 4x/dia popula `route_cache` com 28 rotas BR seed × 6 meses
3. Dashboard logado mostra cards de grupos com preço + sparkline + savings
4. Páginas SEO públicas `/rotas/{O}-{D}` indexadas no Google (sitemap submetido)
5. Email consolidado via cron + quando detecta sinal
6. Botão "Comprar agora" redireciona via `/comprar/` (tracked) pro Aviasales com marker 714304
7. Admin panel `/admin/stats` mostra quota SerpAPI, hit rate Travelpayouts, cliques afiliados

## Landing page (orbita-flights.fly.dev/)

Estado final após sessão 2026-04-22:
- Hero split (copy + preview card lado direito com dados reais)
- 3 interatividades: cursor spotlight (23 cards), preço counter animado, órbita girando atrás do hero
- Seções: Como funciona (3 passos) → O que você tem (5 checks positivos) → Por que Órbita (4 diferenciais anti-buscador) → Como sabemos (manifest honesto) → Rotas populares → FAQ → CTA final
- Footer tagline: "Órbita // você dorme, a gente vigia"

## Stack

Python 3.11 + FastAPI + gunicorn + uvicorn[standard] (uvloop). PostgreSQL Neon (prod) + SQLite (tests). SQLAlchemy 2.0 + Alembic. Jinja2 SSR. Space Grotesk + JetBrains Mono. APScheduler in-process. Pillow pra OG image. Authlib OAuth. slowapi. Sentry. Travelpayouts + SerpAPI.

## Convenções críticas

- **Acentuação pt-BR obrigatória** em texto visível
- **Sem emoji** em código/docs/commits
- **Commits atômicos** conventional commits (feat/fix/chore/docs/refactor)
- **SDD + TDD** — spec → RED → GREEN → REFACTOR
- **Sem JS framework** — Jinja2 SSR puro, JS vanilla quando necessário
- **Travessão `—` proibido em copy** (usar ponto ou vírgula)
- **Órbita** (com acento) em prosa, **Orbita** (sem acento) em URL/código

## Próximas fases

Ver specs completas em:
- `.planning/phases/34-price-prediction/34-SPEC.md` — recomendação COMPRE/AGUARDE/MONITORAR com regras determinísticas + backtest (~3h)
- `.planning/phases/36-multi-leg/36-SPEC.md` — grupos multi-trecho encadeados (~8h, depende de 34)

## Pendências do usuário (fora do código)

1. Renomear pasta local `flight-monitor` → `{nome novo}` (guia: deletar .venv, rename, recriar venv, `pip install -r requirements.txt`)
2. `git remote set-url origin https://github.com/g-brandao-lima/{nome-novo}.git`
3. Suspender serviço Render `flight-monitor-ly3p` (quando Fly estiver estável 2-3 dias)
4. Remover URI antiga do Google OAuth redirect
5. Avaliar compra de domínio próprio (gatilho: 100+ visitas orgânicas OU 1ª comissão afiliada)

## Comandos úteis

```bash
# Rodar testes
.venv/Scripts/python.exe -m pytest -q
# Deploy
fly deploy
# Ver logs prod
fly logs
# Status
fly status
```

## Referências de conversas anteriores

- `.planning/archive/` tem `NIGHT-REPORT.md`, `VICTORY-REPORT.md` com histórico das milestones anteriores
- `.planning/rebrand-orbita/` tem UI-SPEC.md, MARKETING.md, HOSTING.md (documentos-base do rebrand)
- `.planning/ROADMAP.md` lista todas as fases
- `.planning/REQUIREMENTS.md` lista REQ-IDs por milestone
- `CLAUDE.md` (raiz do projeto) tem convenções de dev

## Como retomar a próxima sessão

Leitura mínima pra ter contexto:
1. Esse arquivo (`.planning/RESUME-CONTEXT.md`)
2. Spec da fase alvo (`.planning/phases/34-.../34-SPEC.md` ou `.planning/phases/36-.../36-SPEC.md`)
3. `CLAUDE.md` da raiz pra convenções

Depois:
```
/gsd:plan-phase 34
# ou
/gsd:plan-phase 36
```

Ou, pra agilizar, falar pro Claude: "implementa direto a Phase 34 seguindo o SPEC — sem planner, execução direta". Ele vai ler o spec e executar os 4 plans em sequência.
