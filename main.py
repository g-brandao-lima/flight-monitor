import sys

sys.stdout.reconfigure(encoding="utf-8")

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.auth.middleware import AuthMiddleware
from app.config import settings

logger = logging.getLogger(__name__)
_TEMPLATES_DIR = Path(__file__).resolve().parent / "app" / "templates"
_templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Schema gerenciado pelo Alembic (alembic upgrade head)
    from app.scheduler import init_scheduler, shutdown_scheduler

    init_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(title="Flight Monitor", lifespan=lifespan)

# Middlewares (Starlette LIFO: SessionMiddleware adicionado primeiro, executa primeiro)
is_production = not settings.database_url.startswith("sqlite")
app.add_middleware(AuthMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret_key,
    max_age=365 * 24 * 60 * 60,
    https_only=is_production,
    same_site="lax",
)

from app.auth.routes import router as auth_router
from app.routes.route_groups import router as route_groups_router
from app.routes.alerts import router as alerts_router
from app.routes.dashboard import router as dashboard_router

app.include_router(auth_router)
app.include_router(route_groups_router, prefix="/api/v1")
app.include_router(alerts_router, prefix="/api/v1")
app.include_router(dashboard_router)


@app.head("/")
async def health_check():
    """Endpoint HEAD para UptimeRobot keep-alive."""
    return HTMLResponse(content="", status_code=200)


FIELD_LABELS = {
    "name": "Nome do grupo",
    "origins": "Origens",
    "destinations": "Destinos",
    "duration_days": "Duração (dias)",
    "travel_start": "Data de início",
    "travel_end": "Data de fim",
    "passengers": "Passageiros",
    "max_stops": "Paradas máximas",
    "target_price": "Preço alvo",
    "mode": "Modo",
}

ERROR_MESSAGES = {
    404: ("Página não encontrada.", "O endereço que você acessou não existe."),
}
DEFAULT_ERROR = ("Algo deu errado no servidor.", "Tente novamente em alguns instantes.")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Convert FastAPI 422 JSON into a user-friendly redirect with error message."""
    errors = exc.errors()
    field_msgs = []
    for err in errors:
        loc = err.get("loc", [])
        field = loc[-1] if loc else "campo"
        label = FIELD_LABELS.get(field, field)
        field_msgs.append(f"{label}: valor inválido")
    error_text = "; ".join(field_msgs) if field_msgs else "Preencha todos os campos corretamente."

    referer = request.headers.get("referer", "/")
    if "/groups/create" in str(request.url) or "/groups/create" in referer:
        from app.routes.dashboard import get_all_airports
        return HTMLResponse(
            content=_templates.get_template("dashboard/create.html").render(
                request=request,
                error=error_text,
                form_data={},
                airports=get_all_airports(),
                user=None,
            ),
            status_code=422,
        )
    return HTMLResponse(
        content=_templates.get_template("error.html").render(
            request=request, message="Dados inválidos", detail=error_text
        ),
        status_code=422,
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.error("HTTPException %s at %s: %s", exc.status_code, request.url, exc.detail)
    message, detail = ERROR_MESSAGES.get(exc.status_code, DEFAULT_ERROR)
    return HTMLResponse(
        content=_templates.get_template("error.html").render(
            request=request, message=message, detail=detail
        ),
        status_code=exc.status_code,
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception at %s: %s", request.url, exc, exc_info=True)
    message, detail = DEFAULT_ERROR
    return HTMLResponse(
        content=_templates.get_template("error.html").render(
            request=request, message=message, detail=detail
        ),
        status_code=500,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
