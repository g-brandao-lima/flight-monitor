import logging
from datetime import date, timedelta

from app.database import SessionLocal
from app.models import RouteGroup
from app.services.alert_service import compose_alert_email, send_email, should_alert
from app.services.serpapi_client import SerpApiClient, classify_price
from app.services.signal_service import detect_signals
from app.services.snapshot_service import is_duplicate_snapshot, save_flight_snapshot

logger = logging.getLogger(__name__)

DATE_STEP_DAYS = 7


def run_polling_cycle():
    """Executa um ciclo de polling para todos os grupos ativos."""
    client = SerpApiClient()
    if not client.is_configured:
        logger.warning("SerpAPI not configured. Skipping polling cycle.")
        return

    db = SessionLocal()
    try:
        groups = db.query(RouteGroup).filter(RouteGroup.is_active == True).all()
        logger.info(f"Polling {len(groups)} active groups")
        for group in groups:
            try:
                _poll_group(db, client, group)
            except Exception as e:
                logger.error(
                    f"Polling failed for group {group.id} ({group.name}): {e}"
                )
                continue
    finally:
        db.close()


def _generate_date_pairs(
    travel_start: date, travel_end: date, duration_days: int
) -> list[tuple[date, date]]:
    """Gera pares (departure_date, return_date) a cada DATE_STEP_DAYS dias dentro do periodo."""
    pairs = []
    current = travel_start
    while current + timedelta(days=duration_days) <= travel_end:
        pairs.append((current, current + timedelta(days=duration_days)))
        current += timedelta(days=DATE_STEP_DAYS)
    if not pairs and travel_start + timedelta(days=duration_days) <= travel_end + timedelta(
        days=duration_days
    ):
        pairs.append((travel_start, travel_start + timedelta(days=duration_days)))
    return pairs


def _poll_group(db, client: SerpApiClient, group: RouteGroup):
    """Polling de um grupo: gera combinacoes, busca voos via SerpAPI (1 call por combinacao)."""
    origins = group.origins
    destinations = group.destinations
    date_pairs = _generate_date_pairs(
        group.travel_start, group.travel_end, group.duration_days
    )

    for origin in origins:
        for destination in destinations:
            for dep_date, ret_date in date_pairs:
                try:
                    flights, insights = client.search_flights_with_insights(
                        origin=origin,
                        destination=destination,
                        departure_date=dep_date.isoformat(),
                        return_date=ret_date.isoformat(),
                        max_results=5,
                    )
                except Exception as e:
                    logger.warning(
                        f"No flights found for {origin}->{destination} {dep_date}: {e}"
                    )
                    continue

                if not flights:
                    logger.info(f"No flights available for {origin}->{destination} {dep_date}")
                    continue

                for flight in flights:
                    _process_flight(
                        db, group, origin, destination, dep_date, ret_date,
                        flight, insights
                    )


def _process_flight(db, group, origin, destination, dep_date, ret_date, flight, insights):
    """Processa um voo: classifica preco e persiste snapshot."""
    price = float(flight["price"])
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

    if is_duplicate_snapshot(db, group.id, origin, destination, dep_date, ret_date, price, airline):
        logger.debug(
            f"Duplicate snapshot skipped: {origin}->{destination} {dep_date} "
            f"price={price} airline={airline}"
        )
        return

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
    try:
        detected = detect_signals(db, snapshot)
        for signal in detected:
            logger.info(
                f"Signal detected: {signal.signal_type} ({signal.urgency}) "
                f"for {signal.origin}->{signal.destination} {signal.departure_date}"
            )
            try:
                if should_alert(group):
                    msg = compose_alert_email(signal, group)
                    send_email(msg)
                    logger.info(f"Alert email sent for {signal.signal_type}")
            except Exception as e:
                logger.error(f"Alert email failed: {e}")
    except Exception as e:
        logger.error(f"Signal detection failed for snapshot {getattr(snapshot, 'id', '?')}: {e}")
