# Domain Pitfalls

**Project:** Flight Monitor v2.1 - Clareza de Preco e Robustez
**Researched:** 2026-04-03
**Confidence:** HIGH (inspecao direta do codebase + documentacao oficial + CVE verificado)

## Critical Pitfalls

Erros que causam rewrite, perda de dados ou vulnerabilidade de seguranca.

### Pitfall 1: Remover SessionMiddleware quebra o fluxo OAuth do Authlib

**O que da errado:** O Authlib Starlette integration usa `request.session` para armazenar o `state` do OAuth durante `authorize_redirect`. Quando o callback (`authorize_access_token`) e chamado, o Authlib le o `state` da sessao para validar o CSRF. Se o SessionMiddleware for removido para "migrar para JWT puro", o fluxo de login OAuth quebra completamente: o `authorize_redirect` falha ao tentar escrever na sessao inexistente, ou o callback nao encontra o state e rejeita o login.

**Por que acontece:** A migracao para JWT e motivada por "sessoes stateless", mas o fluxo OAuth Authorization Code exige estado temporario entre o redirect e o callback. Esse estado (o parametro `state`) precisa sobreviver ao round-trip browser -> Google -> callback. Sessoes sao o mecanismo padrao do Authlib para isso. Internamente, o Authlib chama `set_state_data(session, state, data)` no authorize_redirect e `get_state_data(session, state)` no authorize_access_token (confirmado no source do Authlib starlette integration).

**Codigo afetado neste projeto:**
- `app/auth/oauth.py`: `oauth.google.authorize_redirect(request, redirect_uri)` grava state na sessao
- `app/auth/routes.py` L25: `oauth.google.authorize_access_token(request)` le state da sessao
- `main.py` L38-44: `SessionMiddleware` configurado com secret_key
- `app/auth/middleware.py` L22: `request.session.get("user_id")` para verificar autenticacao
- `app/auth/dependencies.py` L8: `request.session.get("user_id")` para obter usuario
- `tests/conftest.py` L25-29: `_make_session_cookie` para testes autenticados

**Consequencias:** Login impossivel. Usuarios existentes deslogados. 218+ testes de auth quebram.

**Prevencao:** Manter o SessionMiddleware APENAS para o fluxo OAuth (armazenar state temporario). Apos o callback com sucesso, emitir um JWT como cookie httpOnly. O AuthMiddleware e `get_current_user` passam a ler o JWT do cookie em vez de `request.session["user_id"]`. A sessao continua existindo mas so e usada durante os poucos segundos do fluxo OAuth.

**Arquitetura correta:**
1. `SessionMiddleware` permanece (para OAuth state do Authlib)
2. Login callback: recebe userinfo -> cria JWT -> seta cookie `access_token` (httpOnly, secure, samesite=lax)
3. `AuthMiddleware` verifica cookie JWT (nao sessao)
4. `get_current_user` decodifica JWT (nao sessao)
5. Logout: limpa cookie JWT E sessao (por seguranca)

**Deteccao:** Teste de integracao que executa o fluxo completo login -> callback -> dashboard. Se quebrar, o JWT esta substituindo a sessao cedo demais.

**Fase recomendada:** Fazer na fase de JWT, com teste end-to-end do fluxo OAuth como gate.

---

### Pitfall 2: JWT em header Authorization com frontend Jinja2 (app inacessivel)

**O que da errado:** Seguir tutoriais SPA que usam `Authorization: Bearer <token>` em vez de cookie.

**Por que acontece:** A maioria dos tutoriais JWT assume frontend React/Vue que faz fetch() com headers customizados. Flight Monitor usa Jinja2 server-rendered com navegacao por links `<a href>` e formularios `<form>`. Links e formularios HTML nao enviam headers Authorization automaticamente.

**Consequencias:** Todas as paginas HTML retornam 401/redirect. App completamente inacessivel para o usuario.

**Prevencao:** JWT DEVE estar em cookie httpOnly com flags secure (producao), samesite=lax, path=/. O browser envia automaticamente em cada request. O middleware le de `request.cookies.get("access_token")`, nao do header Authorization.

**Deteccao:** Primeiro teste de integracao com TestClient falha.

**Fase recomendada:** Fase de JWT.

---

### Pitfall 3: CVE-2025-68158 no Authlib (CSRF no OAuth state)

**O que da errado:** Versoes do Authlib ate 1.6.5 tem vulnerabilidade critica onde o state do OAuth nao e vinculado a sessao do usuario que iniciou o fluxo. Um atacante pode obter um state valido (iniciando seu proprio fluxo) e usa-lo para forcar o callback na sessao da vitima, resultando em account takeover com 1 clique.

**Por que acontece:** O `set_state_data` do Authlib gravava o state em cache global sem vincular a sessao. O `get_state_data` nao verificava se o state pertencia a sessao atual.

**Codigo afetado neste projeto:**
- `requirements.txt`: `authlib==1.6.9` (versao ATUAL ja corrigida)

**Consequencias:** Se o Authlib for downgraded ou pinado incorretamente, qualquer usuario pode ter conta sequestrada.

**Prevencao:** Verificar que `authlib>=1.6.6` esta no requirements.txt. Adicionar check de versao no CI. Nunca usar cache backend para OAuth state neste projeto (manter sessao).

**Deteccao:** `pip show authlib | grep Version` no CI.

**Fase recomendada:** Validar na fase de CI (check automatizado de versao minima).

---

### Pitfall 4: Alembic migration para remover BookingClassSnapshot na ordem errada

**O que da errado:** Dois cenarios de falha: (A) Remover o modelo do Python ANTES de criar a migration: o Alembic autogenerate tenta importar models.py, a relationship `FlightSnapshot.booking_classes` referencia `BookingClassSnapshot` que nao existe mais, SQLAlchemy levanta erro no import. (B) Usar autogenerate sem cuidado: gera migration que dropa a tabela mas tambem tenta alterar outras coisas (false positives comuns com FK no autogenerate).

**Por que acontece:** O fluxo natural e "deletar a classe do models.py, rodar alembic revision --autogenerate". Mas a ordem correta e o inverso: criar migration primeiro, aplicar, depois remover o modelo.

**Codigo afetado neste projeto:**
- `app/models.py` L78-79: `FlightSnapshot.booking_classes` relationship para `BookingClassSnapshot`
- `app/models.py` L83-90: classe `BookingClassSnapshot`
- `app/services/snapshot_service.py` L4, L67-72: import e uso de `BookingClassSnapshot`
- `app/routes/dashboard.py` L413-416: delete de `BookingClassSnapshot` no cascade manual
- `tests/test_snapshot_service.py` L4, L58-73, L146: testes que criam `BookingClassSnapshot`
- `alembic/versions/6438afda32c3_baseline_4_tables_from_v1_2.py` L62-70: baseline que cria a tabela

**Consequencias:** Migration mal feita pode: (1) deixar tabela orfao no banco, (2) quebrar o import do models.py durante a geracao da migration, (3) gerar migration incorreta com side effects.

**Prevencao - ordem segura:**
```
1. Criar migration MANUAL: alembic revision -m "drop_booking_class_snapshots"
   upgrade: op.drop_table('booking_class_snapshots')
   downgrade: op.create_table(...) copiando schema do baseline
2. Aplicar migration localmente (alembic upgrade head)
3. Remover BookingClassSnapshot do models.py
4. Remover relationship booking_classes do FlightSnapshot
5. Remover imports/usos em snapshot_service.py, dashboard.py
6. Atualizar/remover testes que usam BookingClassSnapshot
7. Rodar pytest para confirmar
```

**Deteccao:** `alembic check` apos remover o modelo deve mostrar "no changes detected".

**Fase recomendada:** Fase de limpeza de legado, ANTES de outras migrations. Nao misturar com outras mudancas de schema.

---

### Pitfall 5: Rate limiting por IP do proxy (todos os usuarios limitados juntos)

**O que da errado:** O slowapi usa `get_remote_address` por padrao, que le `request.client.host`. Atras do reverse proxy do Render, TODOS os requests chegam com o IP do proxy. Resultado: todos os usuarios compartilham o mesmo rate limit e sao bloqueados juntos.

**Por que acontece:** O Render termina a conexao TLS no edge e faz proxy para o container. O `request.client.host` retorna o IP do proxy interno do Render, nao do usuario real.

**Codigo afetado neste projeto:**
- `render.yaml` L7: `--forwarded-allow-ips="*"` (gunicorn confia em qualquer proxy)
- `main.py`: nao tem ProxyHeadersMiddleware nem custom key_func

**Consequencias:** Rate limit inutil (todos compartilham) ou um usuario bloqueia todos os outros.

**Prevencao:** Usar key function customizada para o slowapi:
```python
def get_rate_limit_key(request: Request) -> str:
    # Usuarios autenticados: rate limit por user_id (do JWT)
    token = request.cookies.get("access_token")
    if token:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            return f"user:{payload['sub']}"
        except Exception:
            pass
    # Fallback: IP do X-Forwarded-For
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host or "unknown"
```

**Deteccao:** Logar a key usada pelo rate limiter nos primeiros dias de producao.

**Fase recomendada:** Fazer junto com JWT (depende de ter user_id no token).

## Moderate Pitfalls

### Pitfall 6: GitHub Actions CI e Render autodeploy em conflito

**O que da errado:** Se o GitHub Actions CI for adicionado SEM alterar o modo de autodeploy do Render, push na main dispara deploy IMEDIATAMENTE em paralelo com o CI. Codigo que falha nos testes vai para producao.

**Por que acontece:** O Render tem 3 modos de auto-deploy: "Yes" (sempre, o default atual), "No" (manual/hook), e "After CI Checks Pass" (disponivel desde maio 2025). Se nao mudar para o terceiro modo, CI e deploy sao independentes.

**Codigo afetado neste projeto:**
- `render.yaml`: nao configura auto-deploy mode
- Nao existe `.github/workflows/` ainda

**Consequencias:** CI passa a ser apenas informativo, sem bloquear deploys quebrados.

**Prevencao:**
1. Criar `.github/workflows/ci.yml` que roda `pytest`
2. No Render Dashboard -> Settings -> Auto-Deploy: setar para "After CI Checks Pass"
3. O Render detecta os checks do GitHub Actions via GitHub Checks API
4. Deploy so acontece se todos os checks passarem

**Alternativa (se free tier nao suportar):** Desativar auto-deploy, usar deploy hook chamado pelo workflow apos testes passarem.

**Deteccao:** Verificar no Render Dashboard que o modo esta correto apos configurar CI.

**Fase recomendada:** Fase de CI.

---

### Pitfall 7: Testes quebram em massa ao mudar para JWT

**O que da errado:** O `conftest.py` atual cria cookies de sessao assinados com `itsdangerous.TimestampSigner`. Ao migrar para JWT, TODOS os 218+ testes que usam `client` fixture quebram porque o cookie de sessao nao e mais verificado pelo novo middleware.

**Codigo afetado neste projeto:**
- `tests/conftest.py` L25-29: `_make_session_cookie` (funcao que fica obsoleta para auth)
- `tests/conftest.py` L97-98: `client.cookies.set("session", cookie_value)`

**Consequencias:** Suite de testes inteira falha. Sem rede de seguranca.

**Prevencao:**
1. Criar `_make_jwt_cookie(user_id: int) -> str` no conftest.py
2. Alterar `client_fixture` para `client.cookies.set("access_token", jwt_token)`
3. Manter `_make_session_cookie` temporariamente para testes especificos do OAuth flow
4. Rodar testes apos CADA mudanca incremental

**Deteccao:** `pytest` falha em massa imediatamente.

**Fase recomendada:** Mesma fase do JWT, como primeira tarefa apos alterar o middleware.

---

### Pitfall 8: Rate limiting bloqueia TestClient nos testes

**O que da errado:** Testes de integracao falham com 429 porque slowapi conta requests do TestClient em sequencia rapida.

**Prevencao:** Desabilitar rate limiting em testes:
- `limiter.enabled = False` no conftest.py
- Ou checar env var `TESTING=true` para nao registrar o limiter

**Fase recomendada:** Fase de rate limiting.

---

### Pitfall 9: Cache de SerpAPI com key incorreta ou TTL desalinhado

**O que da errado:** Se a cache key nao incluir todos os parametros (origem, destino, datas, passengers, max_stops), rotas diferentes compartilham resultados errados. Se o TTL for desalinhado com o ciclo de polling (12h), o cache pode servir dados stale ou nunca ser aproveitado.

**Codigo afetado neste projeto:**
- `app/scheduler.py`: 2 jobs diarios (07:00 e 19:00 UTC)
- `app/services/serpapi_client.py`: chamada real a SerpAPI

**Prevencao:** Cache key = `(origin, destination, departure_date, return_date, passengers, max_stops)`. TTL = 13h (cobre um ciclo de 12h com margem). Dict em memoria (single-worker no Render, sem necessidade de Redis).

**Deteccao:** Logar cache hit/miss ratio.

**Fase recomendada:** Fase de otimizacao SerpAPI.

---

### Pitfall 10: Labels de preco inconsistentes entre templates e email

**O que da errado:** O rotulo "por pessoa, ida e volta" precisa aparecer em 7+ locais. Se um for esquecido, o usuario ve precos sem contexto e pode tomar decisao errada.

**Codigo afetado neste projeto:**
- `app/templates/dashboard/index.html` L326-330: preco no card (ja tem "/ pessoa" e total)
- `app/templates/dashboard/detail.html`: grafico de preco
- `app/services/alert_service.py` L241+, L324+: HTML e plain text do email consolidado
- `app/templates/dashboard/alerts.html`: pagina de alertas

**Prevencao:** Criar filtro Jinja2 centralizado `format_price_label(price, passengers)` e funcao Python equivalente para emails. Usar em TODOS os pontos de exibicao. Testes verificam presenca do texto "por pessoa" em respostas HTML e email.

**Fase recomendada:** PRIMEIRA fase (clareza de preco).

## Minor Pitfalls

### Pitfall 11: JWT secret key fraca em producao

**O que da errado:** `config.py` tem `session_secret_key: str = "dev-secret-change-in-production"`. Se o mesmo padrao for usado para JWT secret e o deploy nao configurar a env var, tokens podem ser forjados.

**Prevencao:** Validar no startup que JWT_SECRET_KEY NAO e o default quando `DATABASE_URL` nao e sqlite.

---

### Pitfall 12: Alembic downgrade impossivel apos drop de BookingClassSnapshot

**O que da errado:** Downgrade recria tabela vazia, dados antigos sao perdidos.

**Prevencao:** Aceitar como one-way. Documentar na migration. Verificar que a tabela esta vazia em producao antes de aplicar (projeto migrou de Amadeus para SerpAPI).

---

### Pitfall 13: GitHub Actions sem cache de pip

**O que da errado:** CI leva 2-3 minutos em vez de 30 segundos.

**Prevencao:** `actions/cache@v4` com key no hash de requirements.txt.

---

### Pitfall 14: JWT expiry muito curto para uso pessoal

**O que da errado:** Expiry de 1h (padrao de tutoriais) forca re-login a cada hora. UX terrivel para dashboard aberto.

**Prevencao:** 7 dias de expiry. Produto pessoal, sem requisito de seguranca extremo.

---

### Pitfall 15: itsdangerous ainda necessario como dependencia transitiva

**O que da errado:** Remover itsdangerous do requirements.txt, mas SessionMiddleware (que permanece para OAuth) depende dele via Starlette.

**Prevencao:** Manter itsdangerous no requirements.txt. SessionMiddleware continua ativo.

## Phase-Specific Warnings

| Fase | Pitfall provavel | Mitigacao |
|------|-------------------|-----------|
| Clareza de preco (labels) | #10: label inconsistente entre templates/email | Centralizar em filtro Jinja2 + funcao Python |
| CI (GitHub Actions) | #6: deploy sem gate de CI | Configurar Render "After CI Checks Pass" |
| CI (GitHub Actions) | #3: Authlib CVE check | Adicionar verificacao de versao no workflow |
| CI (GitHub Actions) | #13: CI lento | Cache de pip no workflow |
| JWT stateless | #1: remover SessionMiddleware quebra OAuth | Manter SessionMiddleware para OAuth state |
| JWT stateless | #2: JWT em header em vez de cookie | Usar cookie httpOnly |
| JWT stateless | #7: testes quebram em massa | Migrar conftest.py junto com middleware |
| JWT stateless | #11: secret key fraca | Validar no startup |
| JWT stateless | #14: expiry muito curto | 7 dias |
| Rate limiting | #5: rate limit por IP do proxy | Key function com user_id do JWT |
| Rate limiting | #8: TestClient bloqueado por 429 | Desabilitar limiter nos testes |
| Otimizacao SerpAPI | #9: cache key incorreta/TTL errado | Key com todos os params, TTL 13h |
| Remocao BookingClassSnapshot | #4: migration na ordem errada | Migration manual ANTES de remover modelo |
| Remocao BookingClassSnapshot | #12: downgrade impossivel | Aceitar one-way, verificar tabela vazia |

## Ordem de Fases Recomendada (baseada em dependencias de pitfalls)

1. **Clareza de preco** - sem dependencias tecnicas, reduz confusao do usuario imediatamente
2. **CI (GitHub Actions)** - rede de seguranca para todas as fases seguintes
3. **JWT stateless** - mudanca mais arriscada, precisa do CI como safety net
4. **Rate limiting** - depende do JWT (para key function por user_id)
5. **Otimizacao SerpAPI** - independente, mas beneficia-se do CI
6. **Remocao BookingClassSnapshot** - ultima, limpeza sem impacto funcional

## Sources

- [Authlib Starlette OAuth Client docs](https://docs.authlib.org/en/latest/client/starlette.html)
- [Authlib starlette integration source - set_state_data/get_state_data](https://github.com/authlib/authlib/blob/main/authlib/integrations/starlette_client/integration.py)
- [Authlib issue #425 - SessionMiddleware requirement](https://github.com/authlib/authlib/issues/425)
- [CVE-2025-68158 - Authlib CSRF vulnerability (account takeover)](https://github.com/advisories/GHSA-fg6f-75jq-6523)
- [SlowAPI GitHub repo - key_func documentation](https://github.com/laurentS/slowapi)
- [Are You Rate Limiting the Wrong IPs? A SlowAPI Story](https://medium.com/@amarharolikar/are-you-rate-limiting-the-wrong-ips-a-slowapi-story-88c2755f5318)
- [Render changelog - Skip auto-deploy if CI checks fail](https://render.com/changelog/skip-auto-deploying-if-ci-checks-fail)
- [Render community - GitHub Actions + Render trigger after CI](https://community.render.com/t/how-to-trigger-render-deployments-from-github-actions-after-ci-passes/38798)
- [Alembic cookbook - batch operations and FK](https://alembic.sqlalchemy.org/en/latest/cookbook.html)
- [Alembic batch migrations - FK limitation](https://alembic.sqlalchemy.org/en/latest/batch.html)
- Inspecao direta do codebase: main.py, app/auth/*, app/models.py, app/services/*, tests/conftest.py, render.yaml, requirements.txt, alembic/versions/
