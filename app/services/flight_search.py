import logging
import re

from app.services import flight_cache
from app.services.serpapi_client import SerpApiClient

logger = logging.getLogger(__name__)

try:
    from fast_flights import FlightData, Passengers, get_flights_from_filter
    from fast_flights.flights_impl import TFSData
    _FF_AVAILABLE = True
except ImportError:
    logger.warning("fast-flights nao instalado; usando apenas SerpAPI")
    _FF_AVAILABLE = False


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
    """Busca voos com cache in-memory (30 min TTL).

    Retorna (flights, insights_or_none, source).
    source reflete a origem real (inclui resultados reusados do cache).
    Para saber se foi cache hit, use `search_flights_ex`.
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

    Usar quando o caller precisa distinguir cache hit de chamada real,
    por exemplo para contabilizar quota SerpAPI corretamente.
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

    try:
        flights = _search_fast_flights(
            origin, destination, departure_date, return_date, max_results, max_stops, pax
        )
        if use_cache:
            flight_cache.put(cache_key, (flights, None, "fast_flights"))
        return flights, None, "fast_flights", False
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
        adults=pax,
    )
    if use_cache:
        flight_cache.put(cache_key, (flights, insights, "serpapi"))
    return flights, insights, "serpapi", False


def _search_fast_flights(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str,
    max_results: int,
    max_stops: int | None,
    adults: int,
) -> list[dict]:
    if not _FF_AVAILABLE:
        raise RuntimeError("fast-flights nao esta instalado")

    # Sempre adults=1 na chamada real. Google Flights retorna preco inconsistente
    # para N adults (total em rotas internacionais, por pessoa em domesticas).
    # Com adults=1 garantimos que snapshot.price e sempre PRECO POR PESSOA.
    # Template multiplica por pax no display de 'total da viagem'.
    tfs = TFSData.from_interface(
        flight_data=[
            FlightData(date=departure_date, from_airport=origin, to_airport=destination),
            FlightData(date=return_date, from_airport=destination, to_airport=origin),
        ],
        trip="round-trip",
        passengers=Passengers(adults=1),
        seat="economy",
        max_stops=max_stops,
    )
    result = get_flights_from_filter(tfs, currency="BRL")

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
    # Remove currency symbols, spaces, etc.
    cleaned = re.sub(r"[^\d.,]", "", price_str)
    # Brazilian format: "1.234,56" → dot=thousands, comma=decimal
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    # "1.234" with no comma: dot is thousands separator (BRL), not decimal
    elif "." in cleaned and cleaned.count(".") == 1:
        parts = cleaned.split(".")
        if len(parts[1]) == 3:
            cleaned = cleaned.replace(".", "")
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return None