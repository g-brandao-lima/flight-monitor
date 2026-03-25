import re
import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from fastapi.responses import JSONResponse

from app.database import get_db
from app.models import RouteGroup
from app.services.dashboard_service import (
    get_groups_with_summary,
    get_price_history,
    format_price_brl,
)
from app.services.airport_service import is_valid_code, get_all_airports, search_airports

router = APIRouter(tags=["dashboard"])
_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

IATA_PATTERN = re.compile(r"^[A-Z]{3}$")
MAX_ACTIVE_GROUPS = 10


def _parse_iata_list(raw: str) -> list[str]:
    """Split comma-separated IATA codes, strip whitespace, uppercase."""
    codes = [c.strip().upper() for c in raw.split(",") if c.strip()]
    return codes


def _validate_iata_codes(codes: list[str]) -> str | None:
    """Return error message if any code is invalid, else None."""
    for code in codes:
        if not IATA_PATTERN.match(code):
            return f"Codigo IATA invalido: {code}. Deve ter 3 letras maiusculas."
        if not is_valid_code(code):
            return f"Aeroporto nao encontrado: {code}. Verifique o codigo IATA."
    return None


def _count_active_groups(db: Session, exclude_id: int | None = None) -> int:
    query = select(func.count()).select_from(RouteGroup).where(
        RouteGroup.is_active == True  # noqa: E712
    )
    if exclude_id is not None:
        query = query.where(RouteGroup.id != exclude_id)
    return db.scalar(query)


def _validate_form(
    name: str,
    origins_raw: str,
    destinations_raw: str,
    duration_days: int,
) -> tuple[list[str], list[str], str | None]:
    """Validate form fields. Returns (origins, destinations, error)."""
    if not name.strip():
        return [], [], "Nome do grupo e obrigatorio."

    origins = _parse_iata_list(origins_raw)
    if not origins:
        return [], [], "Pelo menos uma origem e obrigatoria."
    error = _validate_iata_codes(origins)
    if error:
        return [], [], error

    destinations = _parse_iata_list(destinations_raw)
    if not destinations:
        return [], [], "Pelo menos um destino e obrigatorio."
    error = _validate_iata_codes(destinations)
    if error:
        return [], [], error

    if duration_days < 1:
        return [], [], "Duracao deve ser pelo menos 1 dia."

    return origins, destinations, None


FLASH_MESSAGES = {
    "grupo_criado": "Grupo criado com sucesso!",
    "grupo_atualizado": "Grupo atualizado com sucesso!",
    "grupo_ativado": "Grupo ativado com sucesso!",
    "grupo_desativado": "Grupo desativado com sucesso!",
}


@router.get("/", response_class=HTMLResponse)
def dashboard_index(request: Request, msg: str | None = None, db: Session = Depends(get_db)):
    groups = get_groups_with_summary(db)
    flash_message = FLASH_MESSAGES.get(msg) if msg else None
    return templates.TemplateResponse(
        request=request,
        name="dashboard/index.html",
        context={
            "groups": groups,
            "format_price_brl": format_price_brl,
            "flash_message": flash_message,
        },
    )


@router.get("/api/airports/search")
def api_search_airports(q: str = ""):
    """Endpoint de busca de aeroportos para autocomplete."""
    if len(q) < 2:
        return JSONResponse([])
    results = search_airports(q, limit=8)
    return JSONResponse(results)


@router.get("/groups/create", response_class=HTMLResponse)
def create_group_page(request: Request):
    airports = get_all_airports()
    return templates.TemplateResponse(
        request=request,
        name="dashboard/create.html",
        context={"airports": airports},
    )


@router.post("/groups/create", response_class=HTMLResponse)
def create_group_form(
    request: Request,
    name: str = Form(""),
    origins: str = Form(""),
    destinations: str = Form(""),
    duration_days: int = Form(1),
    travel_start: datetime.date = Form(...),
    travel_end: datetime.date = Form(...),
    target_price: str = Form(""),
    db: Session = Depends(get_db),
):
    parsed_origins, parsed_destinations, error = _validate_form(
        name, origins, destinations, duration_days
    )

    if not error:
        active_count = _count_active_groups(db)
        if active_count >= MAX_ACTIVE_GROUPS:
            error = f"Limite de {MAX_ACTIVE_GROUPS} grupos ativos atingido."

    if error:
        form_data = {
            "name": name,
            "origins": origins,
            "destinations": destinations,
            "duration_days": duration_days,
            "travel_start": travel_start,
            "travel_end": travel_end,
            "target_price": target_price,
        }
        return templates.TemplateResponse(
            request=request,
            name="dashboard/create.html",
            context={"error": error, "form_data": form_data, "airports": get_all_airports()},
        )

    tp = float(target_price) if target_price.strip() else None
    group = RouteGroup(
        name=name.strip(),
        origins=parsed_origins,
        destinations=parsed_destinations,
        duration_days=duration_days,
        travel_start=travel_start,
        travel_end=travel_end,
        target_price=tp,
        is_active=True,
    )
    db.add(group)
    db.commit()
    return RedirectResponse(url="/?msg=grupo_criado", status_code=303)


@router.get("/groups/{group_id}", response_class=HTMLResponse)
def dashboard_detail(request: Request, group_id: int, db: Session = Depends(get_db)):
    group = db.query(RouteGroup).filter(RouteGroup.id == group_id).first()
    if group is None:
        return HTMLResponse(content="Grupo nao encontrado", status_code=404)

    chart_data = get_price_history(db, group_id)
    return templates.TemplateResponse(
        request=request,
        name="dashboard/detail.html",
        context={"group": group, "chart_data": chart_data},
    )


@router.get("/groups/{group_id}/edit", response_class=HTMLResponse)
def edit_group_page(
    request: Request, group_id: int, db: Session = Depends(get_db)
):
    group = db.query(RouteGroup).filter(RouteGroup.id == group_id).first()
    if group is None:
        return HTMLResponse(content="Grupo nao encontrado", status_code=404)
    return templates.TemplateResponse(
        request=request,
        name="dashboard/edit.html",
        context={"group": group, "airports": get_all_airports()},
    )


@router.post("/groups/{group_id}/edit", response_class=HTMLResponse)
def edit_group_form(
    request: Request,
    group_id: int,
    name: str = Form(""),
    origins: str = Form(""),
    destinations: str = Form(""),
    duration_days: int = Form(1),
    travel_start: datetime.date = Form(...),
    travel_end: datetime.date = Form(...),
    target_price: str = Form(""),
    db: Session = Depends(get_db),
):
    group = db.query(RouteGroup).filter(RouteGroup.id == group_id).first()
    if group is None:
        return HTMLResponse(content="Grupo nao encontrado", status_code=404)

    parsed_origins, parsed_destinations, error = _validate_form(
        name, origins, destinations, duration_days
    )

    if error:
        form_data = {
            "name": name,
            "origins": origins,
            "destinations": destinations,
            "duration_days": duration_days,
            "travel_start": travel_start,
            "travel_end": travel_end,
            "target_price": target_price,
        }
        return templates.TemplateResponse(
            request=request,
            name="dashboard/edit.html",
            context={"group": group, "error": error, "form_data": form_data, "airports": get_all_airports()},
        )

    tp = float(target_price) if target_price.strip() else None
    group.name = name.strip()
    group.origins = parsed_origins
    group.destinations = parsed_destinations
    group.duration_days = duration_days
    group.travel_start = travel_start
    group.travel_end = travel_end
    group.target_price = tp
    db.commit()
    return RedirectResponse(url="/?msg=grupo_atualizado", status_code=303)


@router.post("/groups/{group_id}/toggle")
def toggle_group(group_id: int, db: Session = Depends(get_db)):
    group = db.query(RouteGroup).filter(RouteGroup.id == group_id).first()
    if group is None:
        return HTMLResponse(content="Grupo nao encontrado", status_code=404)

    if not group.is_active:
        active_count = _count_active_groups(db, exclude_id=group_id)
        if active_count >= MAX_ACTIVE_GROUPS:
            return RedirectResponse(url="/", status_code=303)

    group.is_active = not group.is_active
    db.commit()
    status = "ativado" if group.is_active else "desativado"
    return RedirectResponse(url=f"/?msg=grupo_{status}", status_code=303)
