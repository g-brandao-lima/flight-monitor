import logging

from serpapi import GoogleSearch

from app.config import settings

logger = logging.getLogger(__name__)


class SerpApiClient:
    """Wrapper de alto nivel para a SerpAPI Google Flights."""

    def __init__(self):
        self._api_key = settings.serpapi_api_key

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    def search_flights_with_insights(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: str,
        max_results: int = 5,
        max_stops: int | None = None,
        adults: int = 1,
    ) -> tuple[list[dict], dict | None]:
        """Busca voos + price insights numa unica chamada API.

        Retorna (flights_sorted, price_insights_or_none).
        Economiza 50% das chamadas vs buscar separado.

        Nota sobre adults: o parametro e ACEITO mas internamente sempre usamos
        adults=1. Motivo: Google Flights retorna preco inconsistente para N
        adults (total em rotas internacionais, por pessoa em domesticas), o
        que polui os dados. Com adults=1 sempre, price e sempre por pessoa.
        Template multiplica por pax no display de 'total da viagem'.
        """
        params = {
            "engine": "google_flights",
            "departure_id": origin,
            "arrival_id": destination,
            "outbound_date": departure_date,
            "return_date": return_date,
            "currency": "BRL",
            "gl": "br",
            "hl": "pt",
            "adults": 1,
            "api_key": self._api_key,
        }
        if max_stops is not None:
            params["stops"] = max_stops

        search = GoogleSearch(params)
        data = search.get_dict()

        # Extrair voos
        best = data.get("best_flights", [])
        other = data.get("other_flights", [])
        all_flights = best + other

        normalized = []
        for flight in all_flights:
            if "price" not in flight:
                continue

            airline = "??"
            segments = flight.get("flights", [])
            if segments:
                airline = segments[0].get("airline", "??")

            normalized.append({
                "price": flight["price"],
                "airline": airline,
                "flights": segments,
                "type": flight.get("type", "Round trip"),
            })

        normalized.sort(key=lambda x: x["price"])
        flights = normalized[:max_results]

        # Extrair insights da mesma resposta
        insights = data.get("price_insights") or None

        return flights, insights


def classify_price(price: float, typical_range: list | None) -> str | None:
    """Classifica preco como LOW/MEDIUM/HIGH baseado no typical_price_range do Google Flights."""
    if not typical_range or len(typical_range) < 2:
        return None

    low_bound = typical_range[0]
    high_bound = typical_range[1]

    if price < low_bound:
        return "LOW"
    if price <= high_bound:
        return "MEDIUM"
    return "HIGH"
