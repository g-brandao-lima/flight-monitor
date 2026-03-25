import sys

sys.stdout.reconfigure(encoding="utf-8")

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.database import Base, engine

logger = logging.getLogger(__name__)
_TEMPLATES_DIR = Path(__file__).resolve().parent / "app" / "templates"
_templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    from app.scheduler import init_scheduler, shutdown_scheduler

    init_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(title="Flight Monitor", lifespan=lifespan)

from app.routes.route_groups import router as route_groups_router
from app.routes.alerts import router as alerts_router
from app.routes.dashboard import router as dashboard_router

app.include_router(route_groups_router, prefix="/api/v1")
app.include_router(alerts_router, prefix="/api/v1")
app.include_router(dashboard_router)


ERROR_MESSAGES = {
    404: ("Pagina nao encontrada.", "O endereco que voce acessou nao existe."),
}
DEFAULT_ERROR = ("Algo deu errado no servidor.", "Tente novamente em alguns instantes.")


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
