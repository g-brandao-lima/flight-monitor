import re
import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from fastapi.responses import JSONResponse

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models import DetectedSignal, RouteGroup, User
from app.services.dashboard_service import (
    get_groups_with_summary,
    get_dashboard_summary,
    get_recent_activity,
    get_price_history,
    format_price_brl,
    format_date_br,
    booking_urls,
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


def _count_active_groups(db: Session, user_id: int | None = None, exclude_id: int | None = None) -> int:
    query = select(func.count()).select_from(RouteGroup).where(
        RouteGroup.is_active == True  # noqa: E712
    )
    if user_id is not None:
        query = query.where(RouteGroup.user_id == user_id)
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
    "login_required": "Faça login para acessar.",
    "login_erro": "Erro ao conectar com o Google. Tente novamente.",
    "login_cancelado": "Login cancelado.",
}


@router.get("/", response_class=HTMLResponse)
def dashboard_index(
    request: Request,
    msg: str | None = None,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    if user is None:
        flash_message = FLASH_MESSAGES.get(msg) if msg else None
        return templates.TemplateResponse(
            request=request,
            name="landing.html",
            context={"user": None, "flash_message": flash_message},
        )

    user_id = user.id
    groups = get_groups_with_summary(db, user_id=user_id)
    summary = get_dashboard_summary(db, user_id=user_id)
    activity = get_recent_activity(db, user_id=user_id)
    flash_message = FLASH_MESSAGES.get(msg) if msg else None
    return templates.TemplateResponse(
        request=request,
        name="dashboard/index.html",
        context={
            "groups": groups,
            "summary": summary,
            "activity": activity,
            "format_price_brl": format_price_brl,
            "format_date_br": format_date_br,
            "booking_urls": booking_urls,
            "flash_message": flash_message,
            "user": user,
        },
    )


@router.get("/alerts", response_class=HTMLResponse)
def alerts_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    """Pagina Meus Alertas: historico de sinais filtrado por usuario."""
    if user is None:
        return RedirectResponse(url="/?msg=login_required", status_code=303)
    signals = (
        db.query(DetectedSignal)
        .join(RouteGroup, DetectedSignal.route_group_id == RouteGroup.id)
        .filter(RouteGroup.user_id == user.id)
        .order_by(DetectedSignal.detected_at.desc())
        .limit(100)
        .all()
    )
    return templates.TemplateResponse(
        request=request,
        name="dashboard/alerts.html",
        context={
            "signals": signals,
            "user": user,
            "format_date_br": format_date_br,
            "format_price_brl": format_price_brl,
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
def create_group_page(
    request: Request,
    user: User | None = Depends(get_current_user),
):
    airports = get_all_airports()
    return templates.TemplateResponse(
        request=request,
        name="dashboard/create.html",
        context={"airports": airports, "user": user},
    )


@router.post("/groups/create", response_class=HTMLResponse)
def create_group_form(
    request: Request,
    name: str = Form(""),
    origins: str = Form(""),
    destinations: str = Form(""),
    duration_days: int = Form(1),
    travel_start: datetime.date | None = Form(None),
    travel_end: datetime.date | None = Form(None),
    mode: str = Form("normal"),
    passengers: int = Form(1),
    max_stops: str = Form(""),
    target_price: str = Form(""),
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    parsed_origins, parsed_destinations, error = _validate_form(
        name, origins, destinations, duration_days
    )

    if not error and not travel_start:
        error = "Data de início do período é obrigatória."
    if not error and not travel_end:
        error = "Data de fim do período é obrigatória."
    if not error and travel_start and travel_end and travel_end <= travel_start:
        error = "Data de fim deve ser posterior à data de início."

    if not error:
        active_count = _count_active_groups(db, user_id=user.id if user else None)
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
            "mode": mode,
            "passengers": passengers,
            "max_stops": max_stops,
            "target_price": target_price,
        }
        return templates.TemplateResponse(
            request=request,
            name="dashboard/create.html",
            context={"error": error, "form_data": form_data, "airports": get_all_airports(), "user": user},
        )

    tp = float(target_price) if target_price.strip() else None
    pax = max(1, min(9, passengers))
    stops = int(max_stops) if max_stops.strip() else None
    group_mode = mode if mode in ("normal", "exploracao") else "normal"
    group = RouteGroup(
        name=name.strip(),
        origins=parsed_origins,
        destinations=parsed_destinations,
        duration_days=duration_days,
        travel_start=travel_start,
        travel_end=travel_end,
        mode=group_mode,
        passengers=pax,
        max_stops=stops,
        target_price=tp,
        is_active=True,
        user_id=user.id if user else None,
    )
    db.add(group)
    db.commit()
    return RedirectResponse(url="/?msg=grupo_criado", status_code=303)


@router.get("/groups/{group_id}", response_class=HTMLResponse)
def dashboard_detail(
    request: Request,
    group_id: int,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    group = db.query(RouteGroup).filter(RouteGroup.id == group_id).first()
    if group is None:
        raise HTTPException(status_code=404, detail="Grupo nao encontrado")
    if user and group.user_id != user.id:
        raise HTTPException(status_code=404, detail="Grupo nao encontrado")

    chart_data = get_price_history(db, group_id, user_id=user.id if user else None)
    return templates.TemplateResponse(
        request=request,
        name="dashboard/detail.html",
        context={"group": group, "chart_data": chart_data, "format_date_br": format_date_br, "user": user},
    )


@router.get("/groups/{group_id}/edit", response_class=HTMLResponse)
def edit_group_page(
    request: Request,
    group_id: int,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    group = db.query(RouteGroup).filter(RouteGroup.id == group_id).first()
    if group is None:
        raise HTTPException(status_code=404, detail="Grupo nao encontrado")
    if user and group.user_id != user.id:
        raise HTTPException(status_code=404, detail="Grupo nao encontrado")
    return templates.TemplateResponse(
        request=request,
        name="dashboard/edit.html",
        context={"group": group, "airports": get_all_airports(), "user": user},
    )


@router.post("/groups/{group_id}/edit", response_class=HTMLResponse)
def edit_group_form(
    request: Request,
    group_id: int,
    name: str = Form(""),
    origins: str = Form(""),
    destinations: str = Form(""),
    duration_days: int = Form(1),
    travel_start: datetime.date | None = Form(None),
    travel_end: datetime.date | None = Form(None),
    mode: str = Form("normal"),
    passengers: int = Form(1),
    max_stops: str = Form(""),
    target_price: str = Form(""),
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    group = db.query(RouteGroup).filter(RouteGroup.id == group_id).first()
    if group is None:
        raise HTTPException(status_code=404, detail="Grupo nao encontrado")
    if user and group.user_id != user.id:
        raise HTTPException(status_code=404, detail="Grupo nao encontrado")

    parsed_origins, parsed_destinations, error = _validate_form(
        name, origins, destinations, duration_days
    )

    if not error and not travel_start:
        error = "Data de início do período é obrigatória."
    if not error and not travel_end:
        error = "Data de fim do período é obrigatória."
    if not error and travel_start and travel_end and travel_end <= travel_start:
        error = "Data de fim deve ser posterior à data de início."

    if error:
        form_data = {
            "name": name,
            "origins": origins,
            "destinations": destinations,
            "duration_days": duration_days,
            "travel_start": travel_start,
            "travel_end": travel_end,
            "mode": mode,
            "passengers": passengers,
            "max_stops": max_stops,
            "target_price": target_price,
        }
        return templates.TemplateResponse(
            request=request,
            name="dashboard/edit.html",
            context={"group": group, "error": error, "form_data": form_data, "airports": get_all_airports(), "user": user},
        )

    tp = float(target_price) if target_price.strip() else None
    pax = max(1, min(9, passengers))
    stops = int(max_stops) if max_stops.strip() else None
    group_mode = mode if mode in ("normal", "exploracao") else "normal"
    group.name = name.strip()
    group.origins = parsed_origins
    group.destinations = parsed_destinations
    group.duration_days = duration_days
    group.travel_start = travel_start
    group.travel_end = travel_end
    group.mode = group_mode
    group.passengers = pax
    group.max_stops = stops
    group.target_price = tp
    db.commit()
    return RedirectResponse(url="/?msg=grupo_atualizado", status_code=303)


@router.post("/groups/{group_id}/toggle")
def toggle_group(
    group_id: int,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    group = db.query(RouteGroup).filter(RouteGroup.id == group_id).first()
    if group is None:
        raise HTTPException(status_code=404, detail="Grupo nao encontrado")
    if user and group.user_id != user.id:
        raise HTTPException(status_code=404, detail="Grupo nao encontrado")

    if not group.is_active:
        active_count = _count_active_groups(db, user_id=user.id if user else None, exclude_id=group_id)
        if active_count >= MAX_ACTIVE_GROUPS:
            return RedirectResponse(url="/", status_code=303)

    group.is_active = not group.is_active
    db.commit()
    status = "ativado" if group.is_active else "desativado"
    return RedirectResponse(url=f"/?msg=grupo_{status}", status_code=303)


FLASH_MESSAGES["polling_ok"] = "Busca manual concluída!"
FLASH_MESSAGES["polling_erro"] = "Erro na busca. Tente novamente."


@router.post("/polling/manual")
def manual_polling():
    """Força um ciclo de polling manual."""
    try:
        from app.services.polling_service import run_polling_cycle
        run_polling_cycle()
        return RedirectResponse(url="/?msg=polling_ok", status_code=303)
    except Exception:
        return RedirectResponse(url="/?msg=polling_erro", status_code=303)
