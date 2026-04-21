import logging
import re

from app.services import flight_cache
from app.services.serpapi_client import SerpApiClient

logger = logging.getLogger(__name__)


def search_flights(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str,
    max_results: int = 5,
    max_stops: int | None = None,
    adults: int = 1,
    use_cache: bool = True,
) -> tuple[list[dict], dict | None, str]:
    """Busca voos via SerpAPI com cache in-memory (30 min TTL).

    Retorna (flights, insights_or_none, source).
    Para saber se foi cache hit, use search_flights_ex.
    """
    flights, insights, source, _ = search_flights_ex(
        origin, destination, departure_date, return_date,
        max_results, max_stops, adults, use_cache,
    )
    return flights, insights, source


def search_flights_ex(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str,
    max_results: int = 5,
    max_stops: int | None = None,
    adults: int = 1,
    use_cache: bool = True,
) -> tuple[list[dict], dict | None, str, bool]:
    """Versao estendida: retorna (flights, insights, source, was_cache_hit).

    Fonte unica: SerpAPI. Cache in-memory evita chamadas duplicadas no mesmo
    ciclo de polling.
    """
    pax = max(1, int(adults))

    cache_key = flight_cache.make_key(
        origin, destination, departure_date, return_date, max_stops, pax
    )
    if use_cache:
        hit = flight_cache.get(cache_key)
        if hit is not None:
            flights_cached, insights_cached, orig_source = hit
            logger.info(
                "flight_cache HIT %s->%s %s (orig=%s)",
                origin, destination, departure_date, orig_source,
            )
            return flights_cached[:max_results], insights_cached, orig_source, True

    client = SerpApiClient()
    flights, insights = client.search_flights_with_insights(
        origin=origin,
        destination=destination,
        departure_date=departure_date,
        return_date=return_date,
        max_results=max_results,
        max_stops=max_stops,
        adults=pax,
    )
    if use_cache:
        flight_cache.put(cache_key, (flights, insights, "serpapi"))
    return flights, insights, "serpapi", False


def _parse_price(price_str: str | None) -> float | None:
    if not price_str:
        return None
    cleaned = re.sub(r"[^\d.,]", "", price_str)
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    elif "." in cleaned and cleaned.count(".") == 1:
        parts = cleaned.split(".")
        if len(parts[1]) == 3:
            cleaned = cleaned.replace(".", "")
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return None
