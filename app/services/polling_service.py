import logging
from datetime import date, timedelta

from sqlalchemy.orm import joinedload

from app.config import settings
from app.database import SessionLocal
from app.models import RouteGroup
from app.services.alert_service import compose_consolidated_email, send_email, should_alert
from app.services import flight_cache
from app.services.flight_search import search_flights
from app.services.quota_service import increment_usage, get_remaining_quota, MONTHLY_QUOTA
from app.services.serpapi_client import classify_price
from app.services.signal_service import detect_signals
from app.services.snapshot_service import (
    get_historical_price_range,
    is_duplicate_snapshot,
    save_flight_snapshot,
)

logger = logging.getLogger(__name__)

DATE_STEP_DAYS = 7


def run_polling_cycle(user_id: int | None = None):
    """Executa um ciclo de polling.

    Se user_id for informado, processa apenas os grupos daquele usuario.
    Caso contrario, processa todos os grupos ativos (usado pelo scheduler).
    """
    db = SessionLocal()
    try:
        remaining = get_remaining_quota(db)
        if remaining <= 0:
            logger.warning(
                "SerpAPI monthly quota exhausted (%d searches). "
                "Apenas rotas do cache Travelpayouts serao processadas.",
                MONTHLY_QUOTA,
            )

        query = (
            db.query(RouteGroup)
            .options(joinedload(RouteGroup.user))
            .filter(RouteGroup.is_active == True)
        )
        if user_id is not None:
            query = query.filter(RouteGroup.user_id == user_id)
        groups = query.all()

        logger.info(f"Polling {len(groups)} active groups (user_id={user_id})")
        for group in groups:
            try:
                _poll_group(db, group)
            except Exception as e:
                logger.error(
                    f"Polling failed for group {group.id} ({group.name}): {e}"
                )
                continue
    finally:
        db.close()


def _generate_date_pairs(
    travel_start: date, travel_end: date, duration_days: int, mode: str = "normal"
) -> list[tuple[date, date]]:
    """Gera pares (departure_date, return_date) dentro do período.

    Normal: a cada 7 dias (busca precisa)
    Exploração: a cada 30 dias (varredura ampla, economiza API)

    Sempre inclui o último par possível para não perder datas no final.
    """
    step = 30 if mode == "exploracao" else DATE_STEP_DAYS
    pairs = []
    current = travel_start
    while current + timedelta(days=duration_days) <= travel_end:
        pairs.append((current, current + timedelta(days=duration_days)))
        current += timedelta(days=step)

    if not pairs:
        if travel_start + timedelta(days=duration_days) <= travel_end + timedelta(days=duration_days):
            pairs.append((travel_start, travel_start + timedelta(days=duration_days)))
    else:
        # Garantir cobertura do final: se o último par não cobre o fim do período,
        # adicionar um par final ancorado no travel_end
        last_dep = pairs[-1][0]
        last_possible_dep = travel_end - timedelta(days=duration_days)
        if last_dep < last_possible_dep:
            pairs.append((last_possible_dep, travel_end))

    return pairs


def _poll_group(db, group: RouteGroup):
    """Polling de um grupo: gera combinacoes e busca voos com fallback automatico.

    Tenta fast-flights primeiro; fallback para SerpAPI se falhar.
    Acumula todos os sinais e snapshots do ciclo e envia 1 email consolidado ao final.
    """
    if group.mode == "multi_leg":
        from app.services.multi_leg_service import search_multi_leg_prices

        snapshot = search_multi_leg_prices(db, group)
        if snapshot is None:
            logger.warning("multi_leg: sem precos para group %s", group.id)
            return
        try:
            signals = detect_signals(db, snapshot)
        except Exception as e:
            logger.error(
                "Signal detection failed for multi_leg snapshot %s: %s",
                getattr(snapshot, "id", "?"),
                e,
            )
            signals = []
        if signals and should_alert(group):
            try:
                recipient = (
                    group.user.email if group.user else settings.gmail_recipient
                )
                allowed = {settings.gmail_sender, settings.gmail_recipient}
                if recipient not in allowed:
                    logger.info(
                        "Skipping multi alert for group %s: recipient %s not allowed",
                        group.name,
                        recipient,
                    )
                    return
                msg = compose_consolidated_email(
                    signals,
                    [snapshot],
                    group,
                    recipient_email=recipient,
                    db=db,
                )
                send_email(msg)
                logger.info(
                    "Consolidated multi email sent for group %s: %d signals",
                    group.name,
                    len(signals),
                )
            except Exception as e:
                logger.error(
                    "Consolidated multi email failed for group %s: %s",
                    group.name,
                    e,
                )
        return

    origins = group.origins
    destinations = group.destinations
    date_pairs = _generate_date_pairs(
        group.travel_start, group.travel_end, group.duration_days, group.mode or "normal"
    )

    accumulated_signals = []
    accumulated_snapshots = []

    for origin in origins:
        for destination in destinations:
            for dep_date, ret_date in date_pairs:
                adults = group.passengers or 1
                cache_key = flight_cache.make_key(
                    origin, destination, dep_date.isoformat(),
                    ret_date.isoformat(), group.max_stops, adults,
                )
                was_cache_hit = flight_cache.get(cache_key) is not None

                try:
                    flights, insights, source = search_flights(
                        origin=origin,
                        destination=destination,
                        departure_date=dep_date.isoformat(),
                        return_date=ret_date.isoformat(),
                        max_results=5,
                        max_stops=group.max_stops,
                        adults=adults,
                    )
                except Exception as e:
                    logger.warning(
                        f"No flights found for {origin}->{destination} {dep_date}: {e}"
                    )
                    continue

                if source == "serpapi" and not was_cache_hit:
                    increment_usage(db)

                if not flights:
                    logger.info(f"No flights available for {origin}->{destination} {dep_date}")
                    continue

                for flight in flights:
                    result = _process_flight(
                        db, group, origin, destination, dep_date, ret_date,
                        flight, insights, source
                    )
                    if result is not None:
                        snapshot, signals = result
                        if snapshot is not None:
                            accumulated_snapshots.append(snapshot)
                        accumulated_signals.extend(signals)

    # Enviar email consolidado se houver sinais e grupo nao silenciado
    if accumulated_signals and should_alert(group):
        try:
            recipient = group.user.email if group.user else settings.gmail_recipient
            allowed = {settings.gmail_sender, settings.gmail_recipient}
            if recipient not in allowed:
                logger.info("Skipping alert email for group %s: recipient %s not in allowed list", group.name, recipient)
                return
            msg = compose_consolidated_email(
                accumulated_signals, accumulated_snapshots, group,
                recipient_email=recipient, db=db,
            )
            send_email(msg)
            logger.info(
                f"Consolidated email sent for group {group.name}: "
                f"{len(accumulated_signals)} signals, {len(accumulated_snapshots)} snapshots"
            )
        except Exception as e:
            logger.error(f"Consolidated email failed for group {group.name}: {e}")


def _process_flight(db, group, origin, destination, dep_date, ret_date, flight, insights, source=None):
    """Processa um voo: classifica preco, persiste snapshot e detecta sinais.

    Retorna tupla (snapshot, list[DetectedSignal]) ou None se duplicata.
    """
    price = float(flight["price"])
    if price <= 0:
        logger.debug("Skipping flight with invalid price %s", price)
        return None
    airline = flight.get("airline", "??")

    typical_range = None
    price_metrics = {}
    classification = None

    if insights:
        typical_range = insights.get("typical_price_range")
        classification = classify_price(price, typical_range)

        if typical_range and len(typical_range) >= 2:
            price_metrics = {
                "price_min": insights.get("lowest_price"),
                "price_first_quartile": typical_range[0],
                "price_median": (typical_range[0] + typical_range[1]) / 2,
                "price_third_quartile": typical_range[1],
                "price_max": None,
            }
    else:
        historical_range = get_historical_price_range(db, origin, destination)
        if historical_range:
            classification = classify_price(price, historical_range)
            price_metrics = {
                "price_first_quartile": historical_range[0],
                "price_third_quartile": historical_range[1],
                "price_median": (historical_range[0] + historical_range[1]) / 2,
                "price_min": None,
                "price_max": None,
            }

    if is_duplicate_snapshot(db, group.id, origin, destination, dep_date, ret_date, price, airline):
        logger.debug(
            f"Duplicate snapshot skipped: {origin}->{destination} {dep_date} "
            f"price={price} airline={airline}"
        )
        return None

    snapshot_data = {
        "route_group_id": group.id,
        "origin": origin,
        "destination": destination,
        "departure_date": dep_date,
        "return_date": ret_date,
        "price": price,
        "currency": "BRL",
        "airline": airline,
        "price_classification": classification,
        "source": source,
        **price_metrics,
    }
    snapshot = save_flight_snapshot(db, snapshot_data)
    detected = []
    try:
        detected = detect_signals(db, snapshot)
        for signal in detected:
            logger.info(
                f"Signal detected: {signal.signal_type} ({signal.urgency}) "
                f"for {signal.origin}->{signal.destination} {signal.departure_date}"
            )
    except Exception as e:
        logger.error(f"Signal detection failed for snapshot {getattr(snapshot, 'id', '?')}: {e}")
    return (snapshot, detected)
