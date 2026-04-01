import logging
import re

from fast_flights import FlightData, Passengers, get_flights

from app.services.serpapi_client import SerpApiClient

logger = logging.getLogger(__name__)


def search_flights(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str,
    max_results: int = 5,
    max_stops: int | None = None,
) -> tuple[list[dict], dict | None, str]:
    """Busca voos: tenta fast-flights primeiro, fallback para SerpAPI.

    Retorna (flights, insights_or_none, source).
    source e "fast_flights" ou "serpapi".
    """
    try:
        flights = _search_fast_flights(
            origin, destination, departure_date, return_date, max_results, max_stops
        )
        return flights, None, "fast_flights"
    except Exception as e:
        logger.warning("fast-flights falhou (%s), usando SerpAPI como fallback", e)

    client = SerpApiClient()
    flights, insights = client.search_flights_with_insights(
        origin=origin,
        destination=destination,
        departure_date=departure_date,
        return_date=return_date,
        max_results=max_results,
        max_stops=max_stops,
    )
    return flights, insights, "serpapi"


def _search_fast_flights(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str,
    max_results: int,
    max_stops: int | None,
) -> list[dict]:
    result = get_flights(
        flight_data=[
            FlightData(date=departure_date, from_airport=origin, to_airport=destination),
            FlightData(date=return_date, from_airport=destination, to_airport=origin),
        ],
        trip="round-trip",
        passengers=Passengers(adults=1),
        seat="economy",
        max_stops=max_stops,
    )

    if not result.flights:
        raise ValueError("fast-flights nao retornou resultados")

    normalized = []
    for flight in result.flights:
        price = _parse_price(flight.price)
        if price is None:
            continue
        normalized.append({
            "price": price,
            "airline": flight.name or "??",
            "flights": [],
            "type": "Round trip",
        })

    if not normalized:
        raise ValueError("fast-flights: nenhum voo com preco valido")

    normalized.sort(key=lambda x: x["price"])
    return normalized[:max_results]


def _parse_price(price_str: str | None) -> float | None:
    if not price_str:
        return None
    cleaned = re.sub(r"[^\d.]", "", price_str)
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return None