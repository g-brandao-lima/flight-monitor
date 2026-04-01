from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse
from fastapi import Request

PUBLIC_PATHS = frozenset({"/", "/auth/login", "/auth/callback", "/auth/logout"})
PUBLIC_PREFIXES = ("/auth/", "/static/", "/api/airports/")


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # HEAD / para UptimeRobot
        if request.method == "HEAD" and path == "/":
            return await call_next(request)

        # Rotas publicas
        if path in PUBLIC_PATHS or any(path.startswith(p) for p in PUBLIC_PREFIXES):
            return await call_next(request)

        # Verificar sessao
        user_id = request.session.get("user_id")
        if not user_id:
            return RedirectResponse(url="/?msg=login_required", status_code=303)

        return await call_next(request)
