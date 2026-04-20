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
            "adults": max(1, int(adults)),
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

        # SerpAPI/Google Flights retorna preco TOTAL para todos os adults do request.
        # Normalizamos aqui para PRECO POR PESSOA, que e a semantica usada em todo
        # o resto do sistema (snapshot.price e por pessoa). Sem isso, grupos com
        # passengers > 1 mostram preco dobrado/triplicado como "por pessoa".
        pax = max(1, int(params.get("adults", 1)))

        normalized = []
        for flight in all_flights:
            if "price" not in flight:
                continue

            airline = "??"
            segments = flight.get("flights", [])
            if segments:
                airline = segments[0].get("airline", "??")

            normalized.append({
                "price": flight["price"] / pax,
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
