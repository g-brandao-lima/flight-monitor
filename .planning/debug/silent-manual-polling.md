---
status: awaiting_human_verify
trigger: "silent-manual-polling — Buscar agora não gera snapshot em prod para rotas fora do cache"
created: 2026-04-24T23:10:00Z
updated: 2026-04-24T23:10:00Z
---

## Current Focus

hypothesis: APLICACAO NAO CONFIGURA LOGGING. main.py nao chama logging.basicConfig/dictConfig. uvicorn/gunicorn so configura seus proprios loggers (uvicorn.access, uvicorn.error). Todo logger obtido via logging.getLogger(__name__) em app.services.* nao tem handler, apenas propaga ate o root. Sentry LoggingIntegration instala um handler no root (breadcrumb), suprimindo o fallback lastResort que normalmente imprimiria WARNING+ em stderr. Resultado: INFO/WARNING/ERROR de polling_service sao capturados como breadcrumbs Sentry mas NAO aparecem no stdout/stderr do container → nunca chegam ao fly logs. O polling provavelmente ESTA rodando; somente esta invisivel.
test: fly ssh exec "python -c 'import logging; logging.getLogger(\"app.services.polling_service\").info(\"teste\")'" + observar se aparece em fly logs
expecting: linha nao aparece → confirma silencio por falta de config; aparece → hipotese errada
next_action: rodar via fly ssh um ciclo de polling sincrono com print() direto para comparar, OU confirmar com user e aplicar fix (adicionar logging.basicConfig em main.py)

## Symptoms

expected: após clicar "Buscar agora", logs "Polling N active groups", iteração com search_flights, snapshot gravado, "Background polling completed"
actual: apenas redirect 303 → /?msg=polling_ok (23:01:42 UTC). Silêncio total após isso. Nenhum snapshot novo.
errors: nenhum erro visível em fly logs.
reproduction: login → grupo REC/JPA/CPV → SCL/PUQ/PUC → Buscar agora → nada.
started: 2026-04-24 23:01 UTC, após deploy 22:54 UTC com Phase 36 (multi-leg + coluna flight_snapshot.details) + Phase 34 (prediction) + hero carousel.

## Eliminated

(vazio — investigação apenas começou)

## Evidence

- timestamp: 2026-04-24T23:10:00Z
  checked: contexto do prompt (pytest local 419/419 verde, deploy recente, grep de logs silencioso)
  found: pytest passa ⇒ bug nao e logica testada por unit/integration. Deploy recente introduziu coluna nova (flight_snapshot.details) via migration j0k1l2m3n4o5.
  implication: hipotese initial: divergencia prod vs local.

- timestamp: 2026-04-24T23:14:00Z
  checked: Dockerfile CMD + fly.toml
  found: CMD `alembic upgrade head && gunicorn main:app -w 1 -k uvicorn.workers.UvicornWorker`. UvicornWorker suporta BackgroundTasks corretamente.
  implication: descarta hipotese "gunicorn sync mata background task".

- timestamp: 2026-04-24T23:16:00Z
  checked: dashboard carrega (user ve flash "Busca iniciada em segundo plano"), dashboard_service.py:47 faz db.query(FlightSnapshot) full-load.
  found: se migration j0k1l2m3n4o5 nao tivesse rodado, SELECT ... details FROM flight_snapshots falharia e a dashboard retornaria 500. Mas a dashboard carrega.
  implication: migration ROUROU em prod. coluna details existe. descarta hipotese "migration atrasou".

- timestamp: 2026-04-24T23:18:00Z
  checked: main.py completo (1-172), observability.py (init_sentry), busca por logging.basicConfig/dictConfig em TODO repo.
  found: **NENHUMA configuracao de logging na aplicacao.** Somente alembic/env.py tem fileConfig (para migrations). main.py nao chama logging.basicConfig nem define dictConfig. Nenhum modulo de app configura handlers no root logger.
  implication: logger = logging.getLogger(__name__) em app.services.polling_service nao tem handler. Logs propagam ate o root logger.

- timestamp: 2026-04-24T23:20:00Z
  checked: observability.init_sentry e chamado em main.py:13 (no import top-level, antes do app = FastAPI(...)). LoggingIntegration configurado com level=INFO, event_level=ERROR.
  found: Sentry LoggingIntegration SUBSTITUI o mecanismo lastResort ao instalar seu proprio handler no root. Handler Sentry captura INFO como breadcrumb e ERROR como evento, porem NAO imprime em stderr/stdout. Resultado: logs aplicacao silenciados no container.
  implication: explica PERFEITAMENTE o sintoma. Mesmo se o polling rodar corretamente OU falhar com warning, nada aparece em fly logs. Logs visiveis ("/api/airports/search?q=Santia") vem de uvicorn.access (logger separado, pre-configurado pelo proprio uvicorn). Nao ha forma do `logger.info("Polling N active groups")` aparecer.

- timestamp: 2026-04-24T23:22:00Z
  checked: pytest passa 419/419 localmente.
  found: pytest instala seu proprio handler (caplog) que captura logs e permite assercoes. Por isso os testes validam logger.info() sem problema — mas isso NAO reflete o comportamento de producao.
  implication: cego nos testes. Testes usam caplog; producao usa Sentry-sem-stdout. O bug e invisivel ao pytest.

## Resolution

root_cause: main.py nao chama logging.basicConfig nem dictConfig. Em producao, Sentry LoggingIntegration instala handler no root logger que captura INFO como breadcrumb e ERROR como evento, mas nao imprime em stdout/stderr. Como o proprio uvicorn so configura loggers uvicorn.*, os loggers app.services.* ficam sem handler visivel → logger.info/warning/error do polling_service nao aparecem no `fly logs`. Consequencia: qualquer falha (ou sucesso) do BackgroundTask e invisivel em producao. Explica silencio total apos POST /polling/manual. Observacao: pode haver bug secundario (falha real no polling para REC→SCL) mascarado pelo mesmo problema; so sera visivel apos aplicar este fix.

fix: Adicionar `logging.basicConfig(level=INFO, format=..., stream=sys.stdout)` em main.py ANTES de init_sentry(). Instala StreamHandler explicito no root → logs da aplicacao vao para stdout do container → aparecem em `fly logs`. Sentry LoggingIntegration continua funcionando em paralelo (ambos loggers coexistem).

verification: pendente deploy em producao + novo teste de "Buscar agora"
files_changed:
  - main.py (adicionado logging.basicConfig antes de init_sentry)
