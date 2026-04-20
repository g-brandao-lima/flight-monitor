import datetime
from collections import defaultdict
from datetime import timedelta

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.models import RouteGroup, FlightSnapshot, DetectedSignal
from app.services.quota_service import get_monthly_usage, get_remaining_quota, MONTHLY_QUOTA


def get_groups_with_summary(db: Session, user_id: int | None = None) -> list[dict]:
    """Return route groups with cheapest snapshot and most urgent recent signal.

    When user_id is provided, only returns groups belonging to that user.
    """
    query = db.query(RouteGroup)
    if user_id is not None:
        query = query.filter(RouteGroup.user_id == user_id)
    groups = query.all()
    result = []

    for group in groups:
        # Find most recent collected_at for this group
        latest_collected = (
            db.query(func.max(FlightSnapshot.collected_at))
            .filter(FlightSnapshot.route_group_id == group.id)
            .scalar()
        )

        cheapest_snapshot = None
        if latest_collected is not None:
            cycle_start = latest_collected - timedelta(hours=6)
            cheapest_snapshot = (
                db.query(FlightSnapshot)
                .filter(
                    FlightSnapshot.route_group_id == group.id,
                    FlightSnapshot.collected_at >= cycle_start,
                    FlightSnapshot.origin.in_(group.origins),
                    FlightSnapshot.destination.in_(group.destinations),
                    FlightSnapshot.price > 0,
                )
                .order_by(FlightSnapshot.price.asc())
                .first()
            )

        # Find most urgent signal in the last 12 hours
        cutoff = datetime.datetime.utcnow() - timedelta(hours=12)
        urgency_order = case(
            (DetectedSignal.urgency == "MAXIMA", 3),
            (DetectedSignal.urgency == "ALTA", 2),
            (DetectedSignal.urgency == "MEDIA", 1),
            else_=0,
        )
        signal = (
            db.query(DetectedSignal)
            .filter(
                DetectedSignal.route_group_id == group.id,
                DetectedSignal.detected_at >= cutoff,
            )
            .order_by(urgency_order.desc())
            .first()
        )

        # Price trend: compare current cheapest with previous cycle
        price_trend = None
        if cheapest_snapshot is not None and latest_collected is not None:
            prev_cycle_end = cycle_start
            prev_cycle_start = prev_cycle_end - timedelta(hours=26)
            prev_cheapest = (
                db.query(func.min(FlightSnapshot.price))
                .filter(
                    FlightSnapshot.route_group_id == group.id,
                    FlightSnapshot.collected_at >= prev_cycle_start,
                    FlightSnapshot.collected_at < prev_cycle_end,
                    FlightSnapshot.origin.in_(group.origins),
                    FlightSnapshot.destination.in_(group.destinations),
                )
                .scalar()
            )
            if prev_cheapest and prev_cheapest > 0:
                change_pct = ((cheapest_snapshot.price - prev_cheapest) / prev_cheapest) * 100
                price_trend = {
                    "previous": prev_cheapest,
                    "change_pct": round(change_pct, 1),
                    "direction": "down" if change_pct < -1 else "up" if change_pct > 1 else "stable",
                }

        # Best day of week (from historical data) - dialect-agnostic
        best_day = None
        day_snaps = (
            db.query(FlightSnapshot.departure_date, FlightSnapshot.price)
            .filter(
                FlightSnapshot.route_group_id == group.id,
                FlightSnapshot.origin.in_(group.origins),
                FlightSnapshot.destination.in_(group.destinations),
                FlightSnapshot.departure_date.isnot(None),
            )
            .all()
        )
        if day_snaps:
            day_prices_map = defaultdict(list)
            for snap in day_snaps:
                dow = snap.departure_date.weekday()  # 0=Monday
                day_prices_map[dow].append(snap.price)
            day_names = ["Segunda", "Terca", "Quarta", "Quinta", "Sexta", "Sabado", "Domingo"]
            candidates = [
                (dow, sum(prices) / len(prices))
                for dow, prices in day_prices_map.items()
                if len(prices) >= 3
            ]
            if candidates:
                candidates.sort(key=lambda x: x[1])
                best_dow, best_avg = candidates[0]
                best_day = {"name": day_names[best_dow], "avg_price": round(best_avg, 0)}

        # Direct vs connection price comparison
        price_comparison = None
        if latest_collected is not None:
            cycle_start_comp = latest_collected - timedelta(hours=6)
            direct_price = (
                db.query(func.min(FlightSnapshot.price))
                .filter(
                    FlightSnapshot.route_group_id == group.id,
                    FlightSnapshot.collected_at >= cycle_start_comp,
                    FlightSnapshot.origin.in_(group.origins),
                    FlightSnapshot.destination.in_(group.destinations),
                )
                .scalar()
            )
            if direct_price and cheapest_snapshot:
                all_min = cheapest_snapshot.price
                if direct_price > all_min * 1.1:
                    price_comparison = {
                        "direct": direct_price,
                        "cheapest": all_min,
                        "savings": round(direct_price - all_min, 0),
                    }

        # Historical best price ever
        best_ever = None
        if cheapest_snapshot is not None:
            historical_min = (
                db.query(func.min(FlightSnapshot.price))
                .filter(
                    FlightSnapshot.route_group_id == group.id,
                    FlightSnapshot.origin.in_(group.origins),
                    FlightSnapshot.destination.in_(group.destinations),
                )
                .scalar()
            )
            if historical_min and historical_min < cheapest_snapshot.price:
                best_ever = round(historical_min, 0)

        # Collection count - dialect-agnostic (Python-side grouping)
        collected_times = (
            db.query(FlightSnapshot.collected_at)
            .filter(FlightSnapshot.route_group_id == group.id)
            .all()
        )
        collection_count = len(set(
            ct[0].strftime("%Y-%m-%d %H") for ct in collected_times if ct[0]
        ))

        # Sparkline data (last 30 days, one price per day - minimum do dia)
        sparkline = []
        price_badge = None
        if collection_count >= 2:
            cutoff_30d = datetime.datetime.utcnow() - timedelta(days=30)
            spark_snaps = (
                db.query(FlightSnapshot.price, FlightSnapshot.collected_at)
                .filter(
                    FlightSnapshot.route_group_id == group.id,
                    FlightSnapshot.origin.in_(group.origins),
                    FlightSnapshot.destination.in_(group.destinations),
                    FlightSnapshot.collected_at >= cutoff_30d,
                )
                .order_by(FlightSnapshot.collected_at.asc())
                .all()
            )
            # Agrupa por dia, pega menor preco de cada dia
            by_day: dict = {}
            for s in spark_snaps:
                if not s.collected_at:
                    continue
                day_key = s.collected_at.strftime("%Y-%m-%d")
                if day_key not in by_day or s.price < by_day[day_key]:
                    by_day[day_key] = s.price
            sparkline = [by_day[k] for k in sorted(by_day.keys())]

            # Badge factual: preco atual vs sparkline de 30d
            if cheapest_snapshot and sparkline and len(sparkline) >= 3:
                current_price = cheapest_snapshot.price
                spark_min = min(sparkline)
                spark_avg = sum(sparkline) / len(sparkline)
                if current_price <= spark_min * 1.01:
                    price_badge = {"label": "Menor preço em 30 dias", "tone": "good"}
                elif current_price <= spark_avg * 0.95:
                    pct = round((spark_avg - current_price) / spark_avg * 100)
                    price_badge = {"label": f"{pct}% abaixo da média 30d", "tone": "good"}
                elif current_price >= spark_avg * 1.10:
                    pct = round((current_price - spark_avg) / spark_avg * 100)
                    price_badge = {"label": f"{pct}% acima da média 30d", "tone": "bad"}

        savings = _compute_savings_since_creation(db, group, cheapest_snapshot)

        result.append({
            "group": group,
            "cheapest_snapshot": cheapest_snapshot,
            "signal": signal,
            "price_trend": price_trend,
            "best_day": best_day,
            "price_comparison": price_comparison,
            "best_ever": best_ever,
            "collection_count": collection_count,
            "sparkline": sparkline,
            "price_badge": price_badge,
            "savings": savings,
        })

    # Sort by cheapest price (groups with data first, then by price ascending)
    result.sort(key=lambda x: x["cheapest_snapshot"].price if x["cheapest_snapshot"] else float("inf"))
    return result


def _compute_savings_since_creation(
    db: Session, group: RouteGroup, current_snapshot: FlightSnapshot | None
) -> dict | None:
    """Simulador "se tivesse comprado ao criar o grupo" (Phase 31).

    Retorna dict {initial_price, current_price, delta, direction, days} ou None.

    direction = 'saved': preco atual < inicial, espera valeu a pena
    direction = 'lost': preco atual > inicial, teria pago menos comprando na criacao
    direction = 'even': diferenca < 1%
    """
    if current_snapshot is None or group.created_at is None:
        return None

    window_end = group.created_at + datetime.timedelta(days=2)
    initial_snap = (
        db.query(FlightSnapshot)
        .filter(
            FlightSnapshot.route_group_id == group.id,
            FlightSnapshot.collected_at >= group.created_at,
            FlightSnapshot.collected_at < window_end,
        )
        .order_by(FlightSnapshot.price.asc())
        .first()
    )
    if initial_snap is None or initial_snap.price <= 0:
        return None

    initial_price = initial_snap.price
    current_price = current_snapshot.price
    delta = current_price - initial_price
    pct = abs(delta) / initial_price * 100 if initial_price else 0

    direction = "even"
    if pct >= 1:
        direction = "saved" if delta < 0 else "lost"

    days_monitoring = (datetime.datetime.utcnow() - group.created_at).days

    return {
        "initial_price": initial_price,
        "current_price": current_price,
        "delta": abs(delta),
        "direction": direction,
        "pct": round(pct, 1),
        "days_monitoring": days_monitoring,
    }


def get_price_history(db: Session, group_id: int, user_id: int | None = None, days: int = 14) -> dict:
    """Return price history labels and prices for the cheapest route of a group.

    When user_id is provided, verifies the group belongs to that user.
    """
    cutoff = datetime.datetime.utcnow() - timedelta(days=days)

    query = db.query(RouteGroup).filter(RouteGroup.id == group_id)
    if user_id is not None:
        query = query.filter(RouteGroup.user_id == user_id)
    group = query.first()
    if group is None:
        return {"labels": [], "prices": [], "route": ""}

    # Find the cheapest route (origin, destination) by average price
    cheapest_route = (
        db.query(FlightSnapshot.origin, FlightSnapshot.destination)
        .filter(
            FlightSnapshot.route_group_id == group_id,
            FlightSnapshot.collected_at >= cutoff,
            FlightSnapshot.origin.in_(group.origins),
            FlightSnapshot.destination.in_(group.destinations),
        )
        .group_by(FlightSnapshot.origin, FlightSnapshot.destination)
        .order_by(func.min(FlightSnapshot.price).asc())
        .first()
    )

    if cheapest_route is None:
        return {"labels": [], "prices": [], "route": ""}

    origin, destination = cheapest_route

    snapshots = (
        db.query(FlightSnapshot)
        .filter(
            FlightSnapshot.route_group_id == group_id,
            FlightSnapshot.origin == origin,
            FlightSnapshot.destination == destination,
            FlightSnapshot.collected_at >= cutoff,
        )
        .order_by(FlightSnapshot.collected_at.asc())
        .all()
    )

    labels = [s.collected_at.strftime("%d/%m %Hh") for s in snapshots]
    prices = [s.price for s in snapshots]

    return {
        "labels": labels,
        "prices": prices,
        "route": f"{origin} -> {destination}",
    }


def get_dashboard_summary(db: Session, user_id: int | None = None) -> dict:
    """Return summary metrics for the dashboard: active count, cheapest price, next polling.

    When user_id is provided, counts and prices are scoped to that user.
    """
    count_query = (
        db.query(func.count())
        .select_from(RouteGroup)
        .where(RouteGroup.is_active == True)  # noqa: E712
    )
    if user_id is not None:
        count_query = count_query.where(RouteGroup.user_id == user_id)
    active_count = count_query.scalar()

    # Find cheapest price across all active groups' latest snapshots
    cheapest_price = None
    cheapest_group_name = None
    groups_query = db.query(RouteGroup).filter(RouteGroup.is_active == True)  # noqa: E712
    if user_id is not None:
        groups_query = groups_query.filter(RouteGroup.user_id == user_id)
    active_groups = groups_query.all()
    for group in active_groups:
        latest_collected = (
            db.query(func.max(FlightSnapshot.collected_at))
            .filter(FlightSnapshot.route_group_id == group.id)
            .scalar()
        )
        if latest_collected is not None:
            cycle_start = latest_collected - timedelta(hours=6)
            min_price = (
                db.query(func.min(FlightSnapshot.price))
                .filter(
                    FlightSnapshot.route_group_id == group.id,
                    FlightSnapshot.collected_at >= cycle_start,
                    FlightSnapshot.origin.in_(group.origins),
                    FlightSnapshot.destination.in_(group.destinations),
                    FlightSnapshot.price > 0,
                )
                .scalar()
            )
            if min_price is not None:
                if cheapest_price is None or min_price < cheapest_price:
                    cheapest_price = min_price
                    cheapest_group_name = group.name

    # BRT timezone (UTC-3, João Pessoa / Brasília)
    brt_offset = timedelta(hours=-3)

    # Next polling from scheduler (picks the earliest of all jobs)
    try:
        from app.scheduler import scheduler
        next_times = []
        for job_id in ("polling_morning", "polling_afternoon"):
            job = scheduler.get_job(job_id)
            if job and job.next_run_time:
                next_times.append(job.next_run_time)
        if next_times:
            earliest = min(next_times)
            next_brt = earliest + brt_offset
            next_polling = next_brt.strftime("%H:%M")
        else:
            next_polling = "04:00 e 16:00"
    except Exception:
        next_polling = "04:00 e 16:00"

    # Last collection time (converted to BRT)
    last_collected = (
        db.query(func.max(FlightSnapshot.collected_at))
        .scalar()
    )
    last_collection_str = None
    if last_collected:
        last_brt = last_collected + brt_offset
        last_collection_str = last_brt.strftime("%d/%m %H:%M")

    return {
        "active_count": active_count,
        "cheapest_price": cheapest_price,
        "cheapest_group_name": cheapest_group_name,
        "next_polling": next_polling,
        "last_collection": last_collection_str,
        "api_usage": get_monthly_usage(db),
        "api_remaining": get_remaining_quota(db),
        "api_quota": MONTHLY_QUOTA,
    }


def get_recent_activity(db: Session, user_id: int | None = None, limit: int = 8) -> list[dict]:
    """Return recent signals and snapshots as activity feed items.

    When user_id is provided, only returns activity for that user's groups.
    """
    items = []

    # Recent signals (last 48h)
    cutoff = datetime.datetime.utcnow() - timedelta(hours=48)
    signals_query = (
        db.query(DetectedSignal)
        .filter(DetectedSignal.detected_at >= cutoff)
    )
    if user_id is not None:
        signals_query = signals_query.join(
            RouteGroup, DetectedSignal.route_group_id == RouteGroup.id
        ).filter(RouteGroup.user_id == user_id)
    signals = (
        signals_query
        .order_by(DetectedSignal.detected_at.desc())
        .limit(limit)
        .all()
    )

    brt = timedelta(hours=-3)
    for s in signals:
        items.append({
            "type": "signal",
            "icon": "alert",
            "text": f"{s.signal_type.replace('_', ' ').title()}: {s.origin} → {s.destination}",
            "detail": f"R$ {s.price_at_detection:,.0f}".replace(",", "."),
            "time": s.detected_at + brt if s.detected_at else s.detected_at,
            "urgency": s.urgency,
        })

    # Latest polling snapshot count per group
    activity_groups_query = db.query(RouteGroup).filter(RouteGroup.is_active == True)
    if user_id is not None:
        activity_groups_query = activity_groups_query.filter(RouteGroup.user_id == user_id)
    groups = activity_groups_query.all()
    for group in groups:
        latest = (
            db.query(func.max(FlightSnapshot.collected_at))
            .filter(FlightSnapshot.route_group_id == group.id)
            .scalar()
        )
        if latest and latest >= cutoff:
            cycle_start = latest - timedelta(hours=6)
            count = (
                db.query(func.count())
                .select_from(FlightSnapshot)
                .filter(
                    FlightSnapshot.route_group_id == group.id,
                    FlightSnapshot.collected_at >= cycle_start,
                )
                .scalar()
            )
            items.append({
                "type": "polling",
                "icon": "sync",
                "text": f"Coleta: {group.name}",
                "detail": f"{count} voos encontrados",
                "time": latest + brt if latest else latest,
                "urgency": None,
            })

    # Sort by time descending and limit
    items.sort(key=lambda x: x["time"], reverse=True)
    return items[:limit]


def format_date_br(d: datetime.date | None) -> str:
    """Format a date as dd/mm/aaaa Brazilian format."""
    if d is None:
        return ""
    return d.strftime("%d/%m/%Y")


def format_price_brl(price: float) -> str:
    """Format a float price as Brazilian Real string: R$ X.XXX,XX."""
    formatted = f"R$ {price:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return formatted


def booking_urls(
    origin: str,
    destination: str,
    departure_date,
    return_date,
    passengers: int = 1,
) -> dict:
    """Gera URLs de deep link para sites de busca de voos.

    Retorna dict com URLs prontas para Google Flights, Decolar e Skyscanner.
    Todos abrem com resultados de voos ja carregados.

    Ordem visual recomendada no template:
    1. google_flights (fonte real do preco mostrado no card)
    2. decolar (OTA mais usada no Brasil)
    3. skyscanner (meta-search mais conhecido)
    """
    dep_iso = departure_date.strftime("%Y-%m-%d") if hasattr(departure_date, 'strftime') else str(departure_date)
    ret_iso = return_date.strftime("%Y-%m-%d") if hasattr(return_date, 'strftime') else str(return_date)
    dep_sky = departure_date.strftime("%y%m%d") if hasattr(departure_date, 'strftime') else ""
    ret_sky = return_date.strftime("%y%m%d") if hasattr(return_date, 'strftime') else ""
    pax = max(1, passengers)

    return {
        "google_flights": (
            f"https://www.google.com/travel/flights?"
            f"q=Flights%20from%20{origin}%20to%20{destination}%20"
            f"on%20{dep_iso}%20returning%20{ret_iso}"
            f"&hl=pt-BR&curr=BRL"
        ),
        "decolar": (
            f"https://www.decolar.com/shop/flights/results/roundtrip/"
            f"{origin}/{destination}/{dep_iso}/{ret_iso}/{pax}/0/0/NA/NA?from=SB"
        ),
        "skyscanner": (
            f"https://www.skyscanner.com.br/transport/flights/"
            f"{origin.lower()}/{destination.lower()}/{dep_sky}/{ret_sky}/"
            f"?adultsv2={pax}&cabinclass=economy"
        ),
    }
