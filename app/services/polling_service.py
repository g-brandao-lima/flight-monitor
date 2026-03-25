import logging
from datetime import date, timedelta

from app.database import SessionLocal
from app.models import RouteGroup
from app.services.amadeus_client import AmadeusClient, classify_price
from app.services.snapshot_service import save_flight_snapshot

logger = logging.getLogger(__name__)


def run_polling_cycle():
    """Executa um ciclo de polling para todos os grupos ativos."""
    client = AmadeusClient()
    if not client.is_configured:
        logger.warning("Amadeus not configured. Skipping polling cycle.")
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
    """Gera pares (departure_date, return_date) a cada 3 dias dentro do periodo."""
    pairs = []
    current = travel_start
    while current + timedelta(days=duration_days) <= travel_end:
        pairs.append((current, current + timedelta(days=duration_days)))
        current += timedelta(days=3)
    if not pairs and travel_start + timedelta(days=duration_days) <= travel_end + timedelta(
        days=duration_days
    ):
        pairs.append((travel_start, travel_start + timedelta(days=duration_days)))
    return pairs


def _poll_group(db, client: AmadeusClient, group: RouteGroup):
    """Polling de um grupo: gera combinacoes, busca ofertas, captura availability e metrics, persiste."""
    origins = group.origins
    destinations = group.destinations
    date_pairs = _generate_date_pairs(
        group.travel_start, group.travel_end, group.duration_days
    )

    for origin in origins:
        for destination in destinations:
            for dep_date, ret_date in date_pairs:
                try:
                    offers = client.search_cheapest_offers(
                        origin=origin,
                        destination=destination,
                        departure_date=dep_date.isoformat(),
                        return_date=ret_date.isoformat(),
                        max_results=5,
                    )
                except Exception as e:
                    logger.error(
                        f"Offers search failed for {origin}->{destination} {dep_date}: {e}"
                    )
                    continue

                for offer in offers:
                    _process_offer(
                        db, client, group, origin, destination, dep_date, ret_date, offer
                    )


def _process_offer(db, client, group, origin, destination, dep_date, ret_date, offer):
    """Processa uma oferta: busca availability, price metrics e persiste snapshot."""
    price = float(offer["price"]["grandTotal"])
    airline = offer.get("validatingAirlineCodes", ["??"])[0]

    try:
        avail_data = client.get_availability(
            origin, destination, dep_date.isoformat(), ret_date.isoformat()
        )
    except Exception as e:
        logger.error(f"Availability failed for {origin}->{destination}: {e}")
        avail_data = []

    booking_classes = _extract_booking_classes(avail_data)

    metrics_data = client.get_price_metrics(origin, destination, dep_date.isoformat())
    price_metrics = {}
    classification = None
    if metrics_data and len(metrics_data) > 0 and "priceMetrics" in metrics_data[0]:
        raw_metrics = metrics_data[0]["priceMetrics"]
        quartiles = {m["quartileRanking"]: float(m["amount"]) for m in raw_metrics}
        price_metrics = {
            "price_min": quartiles.get("MINIMUM"),
            "price_first_quartile": quartiles.get("FIRST"),
            "price_median": quartiles.get("MEDIUM"),
            "price_third_quartile": quartiles.get("THIRD"),
            "price_max": quartiles.get("MAXIMUM"),
        }
        classification = classify_price(price, raw_metrics)

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
        "booking_classes": booking_classes,
        **price_metrics,
    }
    save_flight_snapshot(db, snapshot_data)


def _extract_booking_classes(avail_data: list) -> list[dict]:
    """Extrai booking classes de todos os segmentos do availability response."""
    classes = []
    directions = ["OUTBOUND", "INBOUND"]
    for i, flight in enumerate(avail_data):
        direction = directions[i] if i < len(directions) else f"SEGMENT_{i}"
        for segment in flight.get("segments", []):
            for ac in segment.get("availabilityClasses", []):
                classes.append(
                    {
                        "class_code": ac["class"],
                        "seats_available": ac["numberOfBookableSeats"],
                        "segment_direction": direction,
                    }
                )
    return classes
