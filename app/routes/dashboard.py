import re
import datetime
from collections import defaultdict
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from app.templates_config import get_templates
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from fastapi.responses import JSONResponse

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models import DetectedSignal, RouteGroup, RouteGroupLeg, User
from app.schemas import RouteGroupMultiCreate
from app.rate_limit import (
    limiter,
    LIMIT_AUTOCOMPLETE,
    LIMIT_POLLING,
    LIMIT_WRITE,
)
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
from app.services.popular_routes import POPULAR_ROUTES, get_by_slug, default_dates
from app.services.public_route_service import (
    get_featured_route_for_hero,
    get_hero_routes,
    get_top_public_routes,
    has_enough_data,
)

router = APIRouter(tags=["dashboard"])
_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = get_templates(str(_TEMPLATES_DIR))

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
        popular_public_routes = get_top_public_routes(db, limit=5)
        featured_route = get_featured_route_for_hero(db)
        hero_routes = get_hero_routes(db, limit=6)
        return templates.TemplateResponse(
            request=request,
            name="landing.html",
            context={
                "user": None,
                "flash_message": flash_message,
                "popular_public_routes": popular_public_routes,
                "featured_route": featured_route,
                "hero_routes": hero_routes,
                "format_price_brl": format_price_brl,
            },
        )

    user_id = user.id
    groups = get_groups_with_summary(db, user_id=user_id)
    summary = get_dashboard_summary(db, user_id=user_id)
    activity = get_recent_activity(db, user_id=user_id)
    flash_message = FLASH_MESSAGES.get(msg) if msg else None
    price_mode = request.cookies.get("price_mode", "per_person")
    if price_mode not in ("per_person", "total"):
        price_mode = "per_person"

    for item in groups:
        snap = item.get("cheapest_snapshot") if isinstance(item, dict) else None
        if snap and has_enough_data(db, snap.origin, snap.destination):
            item["public_route_slug"] = f"{snap.origin}-{snap.destination}"
        else:
            item["public_route_slug"] = None

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
            "price_mode": price_mode,
            "popular_routes": POPULAR_ROUTES,
        },
    )


@router.post("/groups/create-from-template")
@limiter.limit(LIMIT_WRITE)
def create_group_from_template(
    request: Request,
    template: str = Form(...),
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    """Cria grupo a partir de template popular (Phase 28).

    Usado pelo estado vazio do dashboard. Datas default sao calculadas
    dinamicamente (partida daqui 60d, janela 60d).
    """
    if user is None:
        return RedirectResponse(url="/?msg=login_required", status_code=303)
    route = get_by_slug(template)
    if route is None:
        return RedirectResponse(url="/groups/create", status_code=303)

    from app.models import RouteGroup
    from app.services.route_group_service import check_active_group_limit

    check_active_group_limit(db, user_id=user.id)
    start, end = default_dates(route.duration_days)
    group = RouteGroup(
        user_id=user.id,
        name=route.name,
        origins=[route.origin],
        destinations=[route.destination],
        duration_days=route.duration_days,
        travel_start=start,
        travel_end=end,
        passengers=1,
        is_active=True,
    )
    db.add(group)
    db.commit()
    db.refresh(group)
    return RedirectResponse(url=f"/groups/{group.id}/edit?msg=grupo_criado", status_code=303)


PRICE_MODE_COOKIE_MAX_AGE = 60 * 60 * 24 * 365  # 1 ano


@router.post("/preferences/price-mode")
def set_price_mode(mode: str = Form(...)):
    """Persiste preferencia de exibicao de preco em cookie (Phase 25)."""
    if mode not in ("per_person", "total"):
        mode = "per_person"
    response = RedirectResponse(url="/", status_code=303)
    from app.config import settings as _settings
    is_production = not _settings.database_url.startswith("sqlite")
    response.set_cookie(
        key="price_mode",
        value=mode,
        max_age=PRICE_MODE_COOKIE_MAX_AGE,
        httponly=True,
        secure=is_production,
        samesite="lax",
    )
    return response


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
@limiter.limit(LIMIT_AUTOCOMPLETE)
def api_search_airports(request: Request, q: str = ""):
    """Endpoint de busca de aeroportos para autocomplete."""
    if len(q) < 2:
        return JSONResponse([])
    results = search_airports(q, limit=8)
    return JSONResponse(results)


LEG_FIELD_PATTERN = re.compile(r"legs\[(\d+)\]\[(\w+)\]")


def _parse_legs_from_form(form_items) -> list[dict]:
    """Parse form data into list of leg dicts sorted by form index.

    Accepts any iterable of (key, value) pairs. Returns list of dicts with
    normalized fields: order, origin, destination, window_start (date),
    window_end (date), min_stay_days (int), max_stay_days (int | None),
    max_stops (int | None).
    """
    legs_raw: dict[int, dict[str, str]] = defaultdict(dict)
    for key, value in form_items:
        match = LEG_FIELD_PATTERN.match(key)
        if not match:
            continue
        idx, field = int(match.group(1)), match.group(2)
        legs_raw[idx][field] = value

    legs_list: list[dict] = []
    for position, idx in enumerate(sorted(legs_raw.keys()), start=1):
        raw = legs_raw[idx]
        if not raw.get("origin"):
            continue

        def _to_int(val: str | None) -> int | None:
            if val is None or val == "":
                return None
            return int(val)

        def _to_date(val: str) -> datetime.date:
            return datetime.date.fromisoformat(val)

        leg = {
            "order": _to_int(raw.get("order")) or position,
            "origin": (raw.get("origin") or "").strip().upper(),
            "destination": (raw.get("destination") or "").strip().upper(),
            "window_start": _to_date(raw["window_start"]),
            "window_end": _to_date(raw["window_end"]),
            "min_stay_days": _to_int(raw.get("min_stay_days")) or 1,
            "max_stay_days": _to_int(raw.get("max_stay_days")),
            "max_stops": _to_int(raw.get("max_stops")),
        }
        legs_list.append(leg)
    return legs_list


@router.post("/groups", response_class=HTMLResponse)
@limiter.limit(LIMIT_WRITE)
async def create_group_dispatch(
    request: Request,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    """Dispatch POST /groups by mode.

    mode=multi_leg: parse legs[] and create RouteGroup with legs.
    Any other mode: delegate to existing /groups/create handler flow.
    """
    form = await request.form()
    mode = form.get("mode", "roundtrip")

    if mode != "multi_leg":
        return RedirectResponse(url="/groups/create", status_code=303)

    # Parse legs and build payload for Pydantic validation
    try:
        legs_list = _parse_legs_from_form(form.multi_items())
    except (ValueError, KeyError) as exc:
        return templates.TemplateResponse(
            request=request,
            name="dashboard/create.html",
            context={
                "error": f"Dados invalidos no formulario multi-trecho: {exc}",
                "airports": get_all_airports(),
                "user": user,
            },
            status_code=400,
        )

    name = (form.get("name") or "").strip()
    passengers_raw = form.get("passengers", "1")
    target_price_raw = form.get("target_price", "")

    try:
        passengers = max(1, min(9, int(passengers_raw or "1")))
    except ValueError:
        passengers = 1
    target_price = float(target_price_raw) if target_price_raw.strip() else None

    try:
        payload = RouteGroupMultiCreate(
            name=name,
            passengers=passengers,
            target_price=target_price,
            legs=legs_list,
        )
    except ValidationError as exc:
        first = exc.errors()[0]
        msg = first.get("msg", "Dados invalidos.")
        if msg.startswith("Value error, "):
            msg = msg[len("Value error, "):]
        return templates.TemplateResponse(
            request=request,
            name="dashboard/create.html",
            context={
                "error": msg,
                "airports": get_all_airports(),
                "user": user,
            },
            status_code=400,
        )

    active_count = _count_active_groups(db, user_id=user.id if user else None)
    if active_count >= MAX_ACTIVE_GROUPS:
        return templates.TemplateResponse(
            request=request,
            name="dashboard/create.html",
            context={
                "error": f"Limite de {MAX_ACTIVE_GROUPS} grupos ativos atingido.",
                "airports": get_all_airports(),
                "user": user,
            },
            status_code=400,
        )

    sorted_legs = sorted(payload.legs, key=lambda l: l.order)
    first_leg = sorted_legs[0]
    last_leg = sorted_legs[-1]

    group = RouteGroup(
        user_id=user.id if user else None,
        name=payload.name,
        origins=[first_leg.origin],
        destinations=[last_leg.destination],
        duration_days=max(1, (last_leg.window_end - first_leg.window_start).days),
        travel_start=first_leg.window_start,
        travel_end=last_leg.window_end,
        mode="multi_leg",
        passengers=payload.passengers,
        target_price=payload.target_price,
        is_active=True,
    )
    db.add(group)
    db.flush()

    for leg_in in sorted_legs:
        db.add(
            RouteGroupLeg(
                route_group_id=group.id,
                order=leg_in.order,
                origin=leg_in.origin,
                destination=leg_in.destination,
                window_start=leg_in.window_start,
                window_end=leg_in.window_end,
                min_stay_days=leg_in.min_stay_days,
                max_stay_days=leg_in.max_stay_days,
                max_stops=leg_in.max_stops,
            )
        )
    db.commit()
    return RedirectResponse(
        url="/?msg=grupo_multi_criado",
        status_code=303,
    )


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
@limiter.limit(LIMIT_WRITE)
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

    # Phase 36 D-18: breakdown trecho-a-trecho para grupos multi_leg
    multi_context = {}
    if group.mode == "multi_leg":
        from app.services.dashboard_service import _build_multi_leg_item, format_price_brl as _fp
        multi_item = _build_multi_leg_item(db, group)
        multi_context = {
            "legs_chain": multi_item.get("legs_chain"),
            "legs_breakdown": multi_item.get("legs_breakdown"),
            "total_price": multi_item.get("total_price"),
            "format_price_brl": _fp,
        }

    return templates.TemplateResponse(
        request=request,
        name="dashboard/detail.html",
        context={"group": group, "chart_data": chart_data, "format_date_br": format_date_br, "user": user, **multi_context},
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
@limiter.limit(LIMIT_WRITE)
async def edit_group_form(
    request: Request,
    group_id: int,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    form = await request.form()
    group = db.query(RouteGroup).filter(RouteGroup.id == group_id).first()
    if group is None:
        raise HTTPException(status_code=404, detail="Grupo nao encontrado")
    if user and group.user_id != user.id:
        raise HTTPException(status_code=404, detail="Grupo nao encontrado")

    mode = form.get("mode", "normal")

    if mode == "multi_leg":
        try:
            legs_list = _parse_legs_from_form(form.multi_items())
        except (ValueError, KeyError) as exc:
            return templates.TemplateResponse(
                request=request,
                name="dashboard/edit.html",
                context={
                    "group": group,
                    "error": f"Dados invalidos: {exc}",
                    "airports": get_all_airports(),
                    "user": user,
                },
                status_code=400,
            )
        name_val = (form.get("name") or "").strip()
        try:
            passengers_val = max(1, min(9, int(form.get("passengers", "1") or "1")))
        except ValueError:
            passengers_val = 1
        target_price_raw = form.get("target_price", "")
        target_price_val = (
            float(target_price_raw) if target_price_raw and target_price_raw.strip() else None
        )
        try:
            payload = RouteGroupMultiCreate(
                name=name_val,
                passengers=passengers_val,
                target_price=target_price_val,
                legs=legs_list,
            )
        except ValidationError as exc:
            first = exc.errors()[0]
            msg = first.get("msg", "Dados invalidos.")
            if msg.startswith("Value error, "):
                msg = msg[len("Value error, "):]
            return templates.TemplateResponse(
                request=request,
                name="dashboard/edit.html",
                context={
                    "group": group,
                    "error": msg,
                    "airports": get_all_airports(),
                    "user": user,
                },
                status_code=400,
            )

        sorted_legs = sorted(payload.legs, key=lambda l: l.order)
        first_leg = sorted_legs[0]
        last_leg = sorted_legs[-1]
        group.name = payload.name
        group.mode = "multi_leg"
        group.passengers = payload.passengers
        group.target_price = payload.target_price
        group.origins = [first_leg.origin]
        group.destinations = [last_leg.destination]
        group.duration_days = max(1, (last_leg.window_end - first_leg.window_start).days)
        group.travel_start = first_leg.window_start
        group.travel_end = last_leg.window_end
        # Recriar legs (cascade delete-orphan cuida dos antigos)
        group.legs.clear()
        db.flush()
        for leg_in in sorted_legs:
            db.add(
                RouteGroupLeg(
                    route_group_id=group.id,
                    order=leg_in.order,
                    origin=leg_in.origin,
                    destination=leg_in.destination,
                    window_start=leg_in.window_start,
                    window_end=leg_in.window_end,
                    min_stay_days=leg_in.min_stay_days,
                    max_stay_days=leg_in.max_stay_days,
                    max_stops=leg_in.max_stops,
                )
            )
        db.commit()
        return RedirectResponse(url="/?msg=grupo_atualizado", status_code=303)

    # Fluxo roundtrip/legado preservado
    name = (form.get("name") or "").strip()
    origins = form.get("origins", "")
    destinations = form.get("destinations", "")
    try:
        duration_days = int(form.get("duration_days", "1") or "1")
    except ValueError:
        duration_days = 1
    travel_start_raw = form.get("travel_start", "")
    travel_end_raw = form.get("travel_end", "")
    travel_start = (
        datetime.date.fromisoformat(travel_start_raw) if travel_start_raw else None
    )
    travel_end = (
        datetime.date.fromisoformat(travel_end_raw) if travel_end_raw else None
    )
    try:
        passengers = int(form.get("passengers", "1") or "1")
    except ValueError:
        passengers = 1
    max_stops = form.get("max_stops", "")
    target_price = form.get("target_price", "")

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
@limiter.limit(LIMIT_WRITE)
def toggle_group(
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

    if not group.is_active:
        active_count = _count_active_groups(db, user_id=user.id if user else None, exclude_id=group_id)
        if active_count >= MAX_ACTIVE_GROUPS:
            return RedirectResponse(url="/", status_code=303)

    group.is_active = not group.is_active
    db.commit()
    status = "ativado" if group.is_active else "desativado"
    return RedirectResponse(url=f"/?msg=grupo_{status}", status_code=303)


FLASH_MESSAGES["grupo_excluido"] = "Grupo excluído com sucesso."


@router.post("/groups/{group_id}/delete")
@limiter.limit(LIMIT_WRITE)
def delete_group(
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

    from app.models import FlightSnapshot, DetectedSignal
    snapshot_ids = [s.id for s in db.query(FlightSnapshot.id).filter(FlightSnapshot.route_group_id == group_id).all()]
    if snapshot_ids:
        db.query(DetectedSignal).filter(DetectedSignal.flight_snapshot_id.in_(snapshot_ids)).delete(synchronize_session=False)
    db.query(FlightSnapshot).filter(FlightSnapshot.route_group_id == group_id).delete(synchronize_session=False)
    db.query(DetectedSignal).filter(DetectedSignal.route_group_id == group_id).delete(synchronize_session=False)
    db.delete(group)
    db.commit()
    return RedirectResponse(url="/?msg=grupo_excluido", status_code=303)


FLASH_MESSAGES["polling_ok"] = "Busca iniciada em segundo plano. Atualize a página em instantes."
FLASH_MESSAGES["polling_erro"] = "Erro na busca. Tente novamente."
FLASH_MESSAGES["polling_sem_quota"] = (
    "Cota mensal de busca esgotada. Renovada automaticamente no dia 1 do "
    "próximo mês. Rotas do cache continuam sendo atualizadas 4x ao dia."
)
FLASH_MESSAGES["polling_parcial_quota"] = (
    "Cota esgotada. Atualizadas apenas rotas do cache popular. "
    "Renovação no dia 1 do próximo mês."
)


def _run_polling_background(user_id: int | None = None) -> None:
    import logging
    _logger = logging.getLogger(__name__)
    try:
        from app.services.polling_service import run_polling_cycle
        run_polling_cycle(user_id=user_id)
        _logger.info("Background polling completed (user_id=%s)", user_id)
    except Exception as e:
        _logger.error("Background polling failed (user_id=%s): %s", user_id, e, exc_info=True)


@router.post("/polling/manual")
@limiter.limit(LIMIT_POLLING)
def manual_polling(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    """Dispara o ciclo de polling para os grupos do usuario em background.

    Se a quota mensal SerpAPI ja esgotou, redireciona com flash diferenciado
    sem agendar background (cache Travelpayouts continua sendo atualizado
    4x/dia pelo cron).
    """
    from app.services.quota_service import get_remaining_quota

    uid = user.id if user else None
    if get_remaining_quota(db) <= 0:
        return RedirectResponse(url="/?msg=polling_sem_quota", status_code=303)
    background_tasks.add_task(_run_polling_background, uid)
    return RedirectResponse(url="/?msg=polling_ok", status_code=303)
