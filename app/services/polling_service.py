import logging
from datetime import date, timedelta

from sqlalchemy.orm import joinedload

from app.config import settings
from app.database import SessionLocal
from app.models import RouteGroup
from app.services.alert_service import compose_consolidated_email, send_email, should_alert
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


def run_polling_cycle():
    """Executa um ciclo de polling para todos os grupos ativos."""
    db = SessionLocal()
    try:
        remaining = get_remaining_quota(db)
        if remaining <= 0:
            logger.warning(
                "SerpAPI monthly quota exhausted (%d searches). "
                "Tentando via fast-flights.",
                MONTHLY_QUOTA,
            )

        groups = (
            db.query(RouteGroup)
            .options(joinedload(RouteGroup.user))
            .filter(RouteGroup.is_active == True)
            .all()
        )
        logger.info(f"Polling {len(groups)} active groups")
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
    """
    step = 30 if mode == "exploracao" else DATE_STEP_DAYS
    pairs = []
    current = travel_start
    while current + timedelta(days=duration_days) <= travel_end:
        pairs.append((current, current + timedelta(days=duration_days)))
        current += timedelta(days=step)
    if not pairs and travel_start + timedelta(days=duration_days) <= travel_end + timedelta(
        days=duration_days
    ):
        pairs.append((travel_start, travel_start + timedelta(days=duration_days)))
    return pairs


def _poll_group(db, group: RouteGroup):
    """Polling de um grupo: gera combinacoes e busca voos com fallback automatico.

    Tenta fast-flights primeiro; fallback para SerpAPI se falhar.
    Acumula todos os sinais e snapshots do ciclo e envia 1 email consolidado ao final.
    """
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
                try:
                    flights, insights, source = search_flights(
                        origin=origin,
                        destination=destination,
                        departure_date=dep_date.isoformat(),
                        return_date=ret_date.isoformat(),
                        max_results=5,
                        max_stops=group.max_stops,
                    )
                except Exception as e:
                    logger.warning(
                        f"No flights found for {origin}->{destination} {dep_date}: {e}"
                    )
                    continue

                if source == "serpapi":
                    increment_usage(db)

                if not flights:
                    logger.info(f"No flights available for {origin}->{destination} {dep_date}")
                    continue

                for flight in flights:
                    result = _process_flight(
                        db, group, origin, destination, dep_date, ret_date,
                        flight, insights
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
            msg = compose_consolidated_email(
                accumulated_signals, accumulated_snapshots, group, recipient_email=recipient
            )
            send_email(msg)
            logger.info(
                f"Consolidated email sent for group {group.name}: "
                f"{len(accumulated_signals)} signals, {len(accumulated_snapshots)} snapshots"
            )
        except Exception as e:
            logger.error(f"Consolidated email failed for group {group.name}: {e}")


def _process_flight(db, group, origin, destination, dep_date, ret_date, flight, insights):
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
        "booking_classes": [],
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
