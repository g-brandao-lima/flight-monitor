# Phase 11: Google OAuth - Research

**Researched:** 2026-03-28
**Domain:** Google OAuth authentication for FastAPI server-rendered app (Authlib + SessionMiddleware)
**Confidence:** HIGH

## Summary

Phase 11 adds Google OAuth login to an existing FastAPI + Jinja2 SSR application. The stack is locked: Authlib for OAuth, Starlette SessionMiddleware with signed cookies for session persistence, and a middleware global approach for route protection. The codebase already has Alembic configured, PostgreSQL support in database.py, and 188 passing tests that assume no authentication.

The primary risk is breaking all 188 existing tests when adding auth middleware. The solution is creating auth test fixtures in conftest.py BEFORE adding any middleware, using FastAPI's dependency override pattern. The second risk is the SessionMiddleware max_age configuration: the default is 14 days, but the user decision requires sessions that persist until explicit logout, which requires setting max_age to a large value (1 year).

**Primary recommendation:** Build in strict order: (1) User model + Alembic migration, (2) auth fixtures in conftest.py, (3) OAuth routes + SessionMiddleware, (4) auth middleware on existing routes, (5) header UI changes. Never add middleware before test fixtures exist.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Apos login com Google, usuario e sempre redirecionado para /dashboard (pagina principal com grupos)
- **D-02:** Sessao nao expira. Dura ate o usuario fazer logout explicitamente. Cookie httpOnly assinado com user_id.
- **D-03:** Authlib para OAuth + SessionMiddleware (Starlette) com signed cookies. Nao usar JWT.
- **D-04:** Claude tem discricionariedade sobre o layout do avatar/nome/logout no header. Deve respeitar o design existente (glassmorphism, Inter font, paleta dark mode #0b0e14).
- **D-05:** Middleware global protege todas as rotas por padrao. Excecoes explicitas: / (landing), /auth/* (login/callback/logout), HEAD / (UptimeRobot)
- **D-06:** Visitante nao logado que tenta acessar rota protegida e redirecionado para / com flash message "Faca login para acessar"
- **D-07:** Falha no login Google (cancelamento, erro de rede) redireciona para / com flash message descritiva ("Login cancelado" ou "Erro ao conectar com Google")
- **D-08:** Conta Google sem foto de perfil exibe circulo com iniciais do nome (ex: "GB") em cor accent do design system

### Claude's Discretion
- Layout especifico do avatar/nome/dropdown no header (manter coerencia com design existente)
- Modelo User (campos, tabela) - pesquisa indica: id, google_id, email, name, picture, created_at
- Escolha entre SessionMiddleware (Starlette) ou cookie manual (itsdangerous)
- Estrutura de arquivos para auth (routes, middleware, services)

### Deferred Ideas (OUT OF SCOPE)
None - discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AUTH-01 | Usuario pode fazer login com um clique via Google OAuth | Authlib OAuth client com `authorize_redirect` + `authorize_access_token` + `server_metadata_url` do Google OIDC |
| AUTH-02 | Sessao do usuario persiste entre abas e refreshes do navegador | SessionMiddleware com `max_age=365*24*60*60` (1 ano), cookie httpOnly assinado com user_id |
| AUTH-03 | Usuario pode fazer logout de qualquer pagina | Rota `/auth/logout` que limpa `request.session` e redireciona para `/` |
| AUTH-04 | Header exibe nome e foto do usuario logado (dados do Google) | Template condicional em base.html usando variavel `user` no contexto Jinja2 |
| AUTH-05 | Falha na autenticacao mostra mensagem clara na landing page | try/except no callback, redirect para `/?msg=login_cancelado` usando flash pattern existente |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- SDD + TDD obrigatorio: spec antes de codigo, testes antes de implementacao (Red-Green-Refactor)
- YAGNI estrito: nao adicionar features nao testadas
- Sem JS framework no frontend (Jinja2 + vanilla JS)
- Complexidade ciclomatica maxima 5 por funcao
- Nao usar emojis nas respostas
- Acentuacao correta em pt-BR

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Authlib | 1.6.x (instalar via pip) | Google OAuth OIDC client | Biblioteca padrao Python para OAuth. Integracao nativa com Starlette via `StarletteOAuth2App`. Lida com token exchange, OIDC discovery, state validation automaticamente. |
| starlette (SessionMiddleware) | 0.46.2 (ja instalado) | Cookie de sessao assinado | Ja vem com FastAPI. Usa `itsdangerous.TimestampSigner` para assinar cookies. Armazena dados serializados em JSON + base64 no cookie. |
| itsdangerous | 2.2.0 (ja instalado) | Assinatura de cookies | Dependencia transitiva do Starlette. Ja esta no ambiente. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Alembic | 1.18.4 (ja instalado) | Migration para tabela users | Ja configurado no projeto. Usar `alembic revision --autogenerate` para gerar migration da tabela User. |

### What NOT to Install
| Avoid | Why |
|-------|-----|
| authlib (ja instalado?) | Verificar: authlib NAO aparece em requirements.txt. Precisa instalar e adicionar. |
| python-jose | Authlib ja faz validacao JWT internamente para OIDC. Duplicaria funcionalidade. |
| fastapi-users | Peso morto para single-provider OAuth. Adiciona password reset, email verify, multiplos backends. |
| Flask-Dance | Flask-specific. Nao funciona com FastAPI/Starlette. |

**Installation:**
```bash
pip install authlib
```

Adicionar ao `requirements.txt`:
```
authlib==1.6.9
```

## Architecture Patterns

### Recommended File Structure (novos arquivos)
```
app/
  auth/
    __init__.py        # empty
    oauth.py           # Authlib OAuth client registration
    routes.py          # /auth/login, /auth/callback, /auth/logout
    middleware.py       # AuthMiddleware global (redirect unauthed to /)
    dependencies.py    # get_current_user() FastAPI dependency
```

### Pattern 1: Authlib OAuth Client Registration
**What:** Registrar cliente Google OAuth com OIDC auto-discovery
**When to use:** Sempre que usar Google OAuth com Authlib

```python
# app/auth/oauth.py
from authlib.integrations.starlette_client import OAuth
from app.config import settings

oauth = OAuth()
oauth.register(
    name="google",
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)
```
**Source:** [Authlib blog - FastAPI Google Login](https://blog.authlib.org/2020/fastapi-google-login)
**Confidence:** HIGH - verificado contra documentacao oficial e exemplos recentes (fev 2026)

### Pattern 2: OAuth Routes (login, callback, logout)
**What:** Tres rotas para o fluxo completo de autenticacao
**When to use:** Toda implementacao de Google OAuth

```python
# app/auth/routes.py
from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.auth.oauth import oauth
from app.database import get_db
from app.models import User

router = APIRouter(prefix="/auth", tags=["auth"])

@router.get("/login")
async def login(request: Request):
    redirect_uri = request.url_for("auth_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get("/callback", name="auth_callback")
async def auth_callback(request: Request, db: Session = Depends(get_db)):
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception:
        return RedirectResponse(url="/?msg=login_erro", status_code=303)

    userinfo = token.get("userinfo")
    if not userinfo:
        return RedirectResponse(url="/?msg=login_erro", status_code=303)

    # find_or_create user
    user = db.query(User).filter(User.google_id == userinfo["sub"]).first()
    if not user:
        user = User(
            google_id=userinfo["sub"],
            email=userinfo["email"],
            name=userinfo.get("name", ""),
            picture_url=userinfo.get("picture"),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    request.session["user_id"] = user.id
    return RedirectResponse(url="/", status_code=303)

@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)
```
**Source:** [Authlib blog](https://blog.authlib.org/2020/fastapi-google-login) + adaptacao para decisoes D-01/D-07
**Confidence:** HIGH

### Pattern 3: Global Auth Middleware (nao decorator por rota)
**What:** Middleware ASGI que intercepta todas as requests e redireciona para / se nao autenticado
**When to use:** Quando a maioria das rotas requer autenticacao (decisao D-05)

```python
# app/auth/middleware.py
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse
from fastapi import Request

PUBLIC_PATHS = frozenset({"/", "/auth/login", "/auth/callback", "/auth/logout"})
PUBLIC_PREFIXES = ("/auth/",)

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # HEAD / para UptimeRobot
        if request.method == "HEAD" and path == "/":
            return await call_next(request)

        # Rotas publicas
        if path in PUBLIC_PATHS or any(path.startswith(p) for p in PUBLIC_PREFIXES):
            return await call_next(request)

        # Static files e assets
        if path.startswith("/static/"):
            return await call_next(request)

        # Verificar sessao
        user_id = request.session.get("user_id")
        if not user_id:
            return RedirectResponse(url="/?msg=login_required", status_code=303)

        return await call_next(request)
```
**Confidence:** HIGH - padrao bem estabelecido para Starlette BaseHTTPMiddleware

### Pattern 4: get_current_user Dependency
**What:** FastAPI dependency que extrai o User do banco via session cookie
**When to use:** Em rotas que precisam do objeto User (nao so do user_id)

```python
# app/auth/dependencies.py
from fastapi import Depends, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User

def get_current_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return db.get(User, user_id)
```
**Confidence:** HIGH

### Pattern 5: SessionMiddleware Configuration (sessao "eterna")
**What:** Configurar max_age para que o cookie persista ate logout explicito
**Critical detail:** O default do SessionMiddleware e `max_age=14*24*60*60` (14 dias). Para a decisao D-02, precisa de um valor muito maior.

```python
# main.py
from starlette.middleware.sessions import SessionMiddleware

# 1 ano em segundos (efetivamente "nunca expira")
SESSION_MAX_AGE = 365 * 24 * 60 * 60

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret_key,
    max_age=SESSION_MAX_AGE,
    https_only=True,  # Render usa HTTPS; dev local precisa de False
    same_site="lax",
)
```

**ATENCAO:** `max_age=None` faz o cookie desaparecer ao fechar o navegador (session cookie). Isso viola D-02. Usar valor numerico grande.

**ATENCAO:** `https_only=True` impede uso em localhost (HTTP). Precisar condicionar:
```python
is_production = not settings.database_url.startswith("sqlite")
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret_key,
    max_age=SESSION_MAX_AGE,
    https_only=is_production,
    same_site="lax",
)
```
**Confidence:** HIGH - verificado no [codigo-fonte do SessionMiddleware](https://github.com/encode/starlette/blob/master/starlette/middleware/sessions.py)

### Anti-Patterns to Avoid
- **Armazenar dados do usuario no cookie:** SessionMiddleware assina mas NAO criptografa. Qualquer pessoa pode ler o conteudo via base64 decode. Armazenar SOMENTE `user_id` (inteiro).
- **Usar email como identificador primario:** Email do Google pode mudar. Usar `sub` claim (google_id) como chave unica imutavel.
- **Adicionar middleware antes de criar fixtures de teste:** 188 testes vao quebrar. Fixtures primeiro.
- **Esquecer `name="auth_callback"` no decorator da rota:** `request.url_for("auth_callback")` depende desse name para gerar a redirect_uri corretamente.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OAuth state/nonce validation | Validacao manual de state param | Authlib (faz automaticamente) | CSRF via state e critico; Authlib gera e valida o state transparently |
| Cookie signing | Assinar cookies manualmente com hmac | SessionMiddleware (usa itsdangerous) | Replay attacks, timing attacks, encoding bugs |
| OIDC discovery | URLs hardcoded de authorize/token/userinfo | `server_metadata_url` do Authlib | Google pode mudar endpoints; discovery automatico resolve |
| User initials extraction | Regex complexo para nomes | `name[0]` + split para segundo nome | Simples, funciona para 99% dos nomes |

**Key insight:** Authlib abstrai toda a complexidade do OAuth/OIDC (state, nonce, token exchange, JWT validation do ID token). Implementar manualmente e uma fonte garantida de vulnerabilidades de seguranca.

## Common Pitfalls

### Pitfall 1: 188 Testes Quebram ao Adicionar SessionMiddleware
**What goes wrong:** Ao adicionar SessionMiddleware e AuthMiddleware, TODAS as requests nos testes retornam redirect 303 para / porque nao tem session cookie.
**Why it happens:** conftest.py atual nao configura sessao nem usuario. TestClient nao envia cookies de sessao.
**How to avoid:**
1. Criar fixture `authenticated_client` em conftest.py que injeta user_id na sessao
2. Criar fixture `test_user` que insere um User no banco de teste
3. Usar `app.dependency_overrides` para mockar `get_current_user`
4. Manter `client` fixture original para testes de rotas publicas
5. Criar tudo isso ANTES de adicionar qualquer middleware

**Warning signs:** `pytest` retorna 188 FAILED de uma vez.

```python
# conftest.py - fixtures novas
from app.models import User

@pytest.fixture(name="test_user")
def test_user_fixture(db):
    user = User(
        google_id="google-test-123",
        email="test@gmail.com",
        name="Test User",
        picture_url=None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture(name="authenticated_client")
def authenticated_client_fixture(client, test_user):
    # SessionMiddleware no TestClient: setar cookie via request
    # Approach: override get_current_user para retornar test_user
    from app.auth.dependencies import get_current_user
    app.dependency_overrides[get_current_user] = lambda: test_user
    yield client
    # cleanup happens in client_fixture via dependency_overrides.clear()
```

### Pitfall 2: redirect_uri Mismatch com Google
**What goes wrong:** Google retorna "Error 400: redirect_uri_mismatch" no callback.
**Why it happens:** A redirect_uri gerada por `request.url_for("auth_callback")` usa o scheme/host do request. Atras de um proxy (Render), pode gerar `http://` em vez de `https://`.
**How to avoid:**
1. Configurar `FORWARDED_ALLOW_IPS="*"` no Gunicorn/Uvicorn para confiar no header X-Forwarded-Proto
2. No Google Cloud Console, registrar AMBAS URIs: `http://localhost:8000/auth/callback` e `https://flight-monitor-ly3p.onrender.com/auth/callback`
3. Render ja configura `X-Forwarded-Proto: https` automaticamente

**Warning signs:** Login funciona local mas falha em producao com "redirect_uri_mismatch".

### Pitfall 3: SessionMiddleware max_age Default de 14 Dias
**What goes wrong:** Usuario reclama que foi deslogado "do nada" apos 2 semanas.
**Why it happens:** O default do SessionMiddleware e 14 dias. `itsdangerous.TimestampSigner` rejeita cookies mais velhos que max_age.
**How to avoid:** Definir `max_age=365*24*60*60` (1 ano) explicitamente. Documentar a decisao.
**Warning signs:** Usuarios sendo deslogados sem clicar logout.

### Pitfall 4: https_only em Dev Local
**What goes wrong:** Cookie nao e enviado pelo browser em localhost (HTTP).
**Why it happens:** `https_only=True` adiciona flag `Secure` ao cookie, que browsers ignoram em HTTP.
**How to avoid:** Condicionar `https_only` baseado no ambiente (sqlite = dev = False, postgresql = prod = True).
**Warning signs:** Login parece funcionar (redirect ok) mas sessao nao persiste no refresh.

### Pitfall 5: Ordem dos Middlewares no FastAPI
**What goes wrong:** SessionMiddleware nao funciona porque foi adicionado na ordem errada.
**Why it happens:** FastAPI/Starlette aplica middlewares em ordem reversa (LIFO). O SessionMiddleware precisa executar ANTES do AuthMiddleware para popular `request.session`.
**How to avoid:** Adicionar na ordem correta em main.py:
```python
# Adicionar DEPOIS (executa PRIMEIRO por ser LIFO)
app.add_middleware(AuthMiddleware)
# Adicionar PRIMEIRO (executa por ultimo, mas popula session antes)
app.add_middleware(SessionMiddleware, secret_key=..., max_age=...)
```
Na pratica: `SessionMiddleware` deve ser adicionado ANTES do `AuthMiddleware` no codigo (porque Starlette inverte a ordem).
**Warning signs:** `request.session` esta vazio mesmo apos login bem-sucedido.

### Pitfall 6: Flash Messages para Auth Errors
**What goes wrong:** Flash message de auth nao aparece na landing page.
**Why it happens:** O sistema atual de flash usa query param `?msg=key` que so funciona no dashboard_index. A landing page (rota `/`) precisa suportar o mesmo mecanismo.
**How to avoid:** Ao redirecionar para `/` com erro, usar `?msg=login_cancelado` e tratar no handler da rota `/`. Reutilizar o mesmo FLASH_MESSAGES dict.
**Warning signs:** Redirect para `/` acontece mas sem mensagem visivel.

## Code Examples

### User Model
```python
# app/models.py - adicionar ao arquivo existente
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    google_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    picture_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
```

### Config Changes
```python
# app/config.py - adicionar campos
class Settings(BaseSettings):
    # ... campos existentes ...
    google_client_id: str = ""
    google_client_secret: str = ""
    session_secret_key: str = "dev-secret-change-in-production"
```

### Header Avatar (base.html)
```html
<!-- Dentro de .header-actions -->
{% if user %}
    <div class="user-menu">
        {% if user.picture_url %}
            <img src="{{ user.picture_url }}" alt="" class="avatar" width="32" height="32">
        {% else %}
            <div class="avatar-initials">{{ user.name[:1] }}{{ user.name.split(' ')[-1][:1] if ' ' in user.name else '' }}</div>
        {% endif %}
        <span class="user-name">{{ user.name.split(' ')[0] }}</span>
        <a href="/auth/logout" class="btn btn-ghost btn-sm">Sair</a>
    </div>
{% else %}
    <a href="/groups/create" class="btn btn-primary">+ Novo Grupo</a>
{% endif %}
```

### Alembic Migration (gerada via autogenerate)
```bash
alembic revision --autogenerate -m "add users table"
alembic upgrade head
```

### Google Cloud Console Redirect URIs
```
# Development
http://localhost:8000/auth/callback

# Production
https://flight-monitor-ly3p.onrender.com/auth/callback
```

### Environment Variables (novas)
```
GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxx
SESSION_SECRET_KEY=<random-string-32-chars>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Authlib usa `starlette.config.Config` para ler .env | Pode usar `client_id`/`client_secret` diretos no `register()` | Authlib 1.0+ | Nao precisa de `Config('.env')`, pode injetar valores do pydantic-settings |
| SessionMiddleware max_age so aceitava int | Aceita `None` para browser-session cookies | Starlette 0.31+ | Permite cookies de sessao do browser (nao e o que queremos aqui) |
| Google OAuth tokens incluiam `id_token` separado | `token["userinfo"]` ja retorna dados parseados do ID token | Authlib 1.0+ | Nao precisa decodificar JWT manualmente |

## Open Questions

1. **Authlib nao esta instalado**
   - What we know: `pip show authlib` nao retornou resultado. NAO esta em requirements.txt.
   - What's unclear: Nada, precisa instalar.
   - Recommendation: Primeiro passo do plano deve ser `pip install authlib` e adicionar ao requirements.txt.

2. **Rota `/` precisa mudar de comportamento**
   - What we know: Atualmente `/` serve o dashboard (dashboard_index). Apos auth, `/` precisa servir dashboard para logados e landing page para nao-logados (Phase 13).
   - What's unclear: Nesta phase (11), a landing page ainda nao existe (e Phase 13). O que `/` mostra para nao-logados?
   - Recommendation: Nesta phase, manter `/` como dashboard. O AuthMiddleware redireciona nao-logados para `/` mas como `/` e publica (excecao no middleware), precisa de uma pagina minima. Opcao: mostrar pagina simples com botao "Entrar com Google" como placeholder ate Phase 13. OU: nao marcar `/` como rota publica e sim ter uma `/landing` separada. A decisao D-05 diz excecao para `/`, entao `/` deve ser a pagina publica.

3. **Proxy headers no Render**
   - What we know: Render envia `X-Forwarded-Proto: https`. Uvicorn/Gunicorn precisa confiar nesses headers para `request.url_for()` gerar URLs HTTPS.
   - What's unclear: Se o Gunicorn atual ja tem `--forwarded-allow-ips` configurado.
   - Recommendation: Verificar `render.yaml` ou Procfile. Se nao tiver, adicionar `--forwarded-allow-ips="*"`.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.3.5 |
| Config file | Nenhum arquivo pytest.ini. Configuracao implicita. |
| Quick run command | `python -m pytest tests/ -x -q` |
| Full suite command | `python -m pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUTH-01 | Login redireciona para Google e callback cria sessao | integration | `python -m pytest tests/test_auth.py::test_login_redirect -x` | Wave 0 |
| AUTH-01 | Callback com token valido cria User e seta sessao | integration | `python -m pytest tests/test_auth.py::test_callback_creates_user -x` | Wave 0 |
| AUTH-01 | Callback com usuario existente reutiliza User | unit | `python -m pytest tests/test_auth.py::test_callback_existing_user -x` | Wave 0 |
| AUTH-02 | Sessao persiste (client com cookie faz request autenticada) | integration | `python -m pytest tests/test_auth.py::test_session_persists -x` | Wave 0 |
| AUTH-03 | Logout limpa sessao e redireciona para / | integration | `python -m pytest tests/test_auth.py::test_logout -x` | Wave 0 |
| AUTH-04 | Template renderiza nome e foto do usuario | integration | `python -m pytest tests/test_auth.py::test_header_shows_user_info -x` | Wave 0 |
| AUTH-04 | Usuario sem foto mostra iniciais | integration | `python -m pytest tests/test_auth.py::test_header_shows_initials -x` | Wave 0 |
| AUTH-05 | Callback com erro redireciona para / com flash | integration | `python -m pytest tests/test_auth.py::test_callback_error_shows_flash -x` | Wave 0 |
| AUTH-05 | Rota protegida sem sessao redireciona para / com flash | integration | `python -m pytest tests/test_auth.py::test_unauthenticated_redirect -x` | Wave 0 |
| REGRESSION | 188 testes existentes continuam passando com auth fixtures | regression | `python -m pytest tests/ -x -q` | Existente (conftest.py precisa update) |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/ -x -q`
- **Per wave merge:** `python -m pytest tests/ -v`
- **Phase gate:** Full suite green antes de `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_auth.py` - cobre AUTH-01 a AUTH-05 (9 testes novos)
- [ ] `tests/conftest.py` - adicionar fixtures `test_user` e `authenticated_client`
- [ ] `pip install authlib` + atualizar requirements.txt

## Sources

### Primary (HIGH confidence)
- [Authlib blog - FastAPI Google Login](https://blog.authlib.org/2020/fastapi-google-login) - Pattern oficial de integracao, verificado funcional
- [Starlette SessionMiddleware source](https://github.com/encode/starlette/blob/master/starlette/middleware/sessions.py) - Parametros, defaults, comportamento de max_age
- Inspecao do codebase: `app/config.py`, `app/database.py`, `app/models.py`, `main.py`, `app/routes/dashboard.py`, `tests/conftest.py`, `app/templates/base.html`, `requirements.txt` (verificado 2026-03-28)

### Secondary (MEDIUM confidence)
- [Google OAuth 2.0 with FastAPI (Feb 2026)](https://manabpokhrel7.medium.com/secure-google-oauth-2-0-integration-with-fastapi-a-comprehensive-guide-2cdb77dcd1e1) - Guia recente, confirma o pattern do Authlib
- [Starlette middleware docs](https://starlette.dev/middleware/) - Configuracao de SessionMiddleware
- `.planning/research/STACK.md` - Pesquisa de milestone (Authlib 1.6.x, decisoes de stack)
- `.planning/research/ARCHITECTURE.md` - Padroes de autenticacao e estrutura
- `.planning/research/PITFALLS.md` - Riscos identificados (188 testes, consent screen, max_age)

### Tertiary (LOW confidence)
- Nenhum item de baixa confianca nesta pesquisa.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Authlib e SessionMiddleware sao as ferramentas oficiais, versoes verificadas no ambiente
- Architecture: HIGH - Pattern confirmado por docs oficiais e codebase existente inspecionado
- Pitfalls: HIGH - Baseado em inspecao direta do codebase (188 testes, conftest.py sem auth, max_age default)

**Research date:** 2026-03-28
**Valid until:** 2026-04-28 (stack estavel, sem mudancas previstas)
