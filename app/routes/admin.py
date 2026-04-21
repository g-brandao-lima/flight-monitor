"""Rotas administrativas do Orbita.

Acessivel somente pelo email configurado em ADMIN_EMAIL. Usa 404 para
nao-admins (evita enumeracao). Phase 24.
"""
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import get_admin_user
from app.config import settings
from app.database import get_db
from app.models import User
from app.services.admin_stats_service import (
    get_cache_hit_rate_7d,
    get_cache_info,
    get_quota_stats,
    get_source_distribution,
    get_travelpayouts_quota_info,
)
from app.templates_config import get_templates

router = APIRouter(prefix="/admin", tags=["admin"])
_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = get_templates(str(_TEMPLATES_DIR))


@router.get("/stats", response_class=HTMLResponse)
def admin_stats(
    request: Request,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    quota = get_quota_stats(db)
    sources = get_source_distribution(db, days=7)
    cache = get_cache_info()
    cache_hit_rate_7d = get_cache_hit_rate_7d(db)
    travelpayouts_quota = get_travelpayouts_quota_info(db)
    sentry_url = (
        "https://sentry.io/organizations/gbl-analise-e-desenvolvimento/issues/"
        "?project=4511252692271104&environment=production"
    )
    return templates.TemplateResponse(
        request=request,
        name="admin/stats.html",
        context={
            "user": admin,
            "quota": quota,
            "sources": sources,
            "cache": cache,
            "cache_hit_rate_7d": cache_hit_rate_7d,
            "travelpayouts_quota": travelpayouts_quota,
            "sentry_url": sentry_url,
            "sentry_enabled": bool(settings.sentry_dsn),
        },
    )
