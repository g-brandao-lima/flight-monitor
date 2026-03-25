import logging

from amadeus import Client, ResponseError

from app.config import settings

logger = logging.getLogger(__name__)


class AmadeusClient:
    """Wrapper de alto nivel para o Amadeus SDK."""

    def __init__(self):
        if not settings.amadeus_client_id or not settings.amadeus_client_secret:
            self._client = None
            logger.warning("Amadeus credentials not configured. Client disabled.")
        else:
            self._client = Client(
                client_id=settings.amadeus_client_id,
                client_secret=settings.amadeus_client_secret,
            )

    @property
    def is_configured(self) -> bool:
        return self._client is not None

    def search_cheapest_offers(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: str,
        max_results: int = 5,
    ) -> list[dict]:
        """Busca as ofertas mais baratas ordenadas por preco crescente."""
        response = self._client.shopping.flight_offers_search.get(
            originLocationCode=origin,
            destinationLocationCode=destination,
            departureDate=departure_date,
            returnDate=return_date,
            adults=1,
            currencyCode="BRL",
            max=250,
        )
        offers = sorted(response.data, key=lambda x: float(x["price"]["grandTotal"]))
        return offers[:max_results]

    def get_availability(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: str,
    ) -> list[dict]:
        """Busca disponibilidade de booking classes para a rota."""
        body = {
            "originDestinations": [
                {
                    "id": "1",
                    "originLocationCode": origin,
                    "destinationLocationCode": destination,
                    "date": departure_date,
                },
                {
                    "id": "2",
                    "originLocationCode": destination,
                    "destinationLocationCode": origin,
                    "date": return_date,
                },
            ],
            "travelers": [{"id": "1", "travelerType": "ADULT"}],
            "sources": ["GDS"],
        }
        response = self._client.shopping.availability.flight_availabilities.post(body)
        return response.data

    def get_price_metrics(
        self,
        origin: str,
        destination: str,
        departure_date: str,
    ) -> list[dict] | None:
        """Busca metricas historicas de preco (quartis). Retorna None em caso de erro."""
        try:
            response = self._client.analytics.itinerary_price_metrics.get(
                originIataCode=origin,
                destinationIataCode=destination,
                departureDate=departure_date,
                currencyCode="BRL",
            )
            return response.data
        except ResponseError as e:
            logger.warning("Price metrics unavailable for %s-%s: %s", origin, destination, e)
            return None


def classify_price(price: float, metrics: list[dict]) -> str | None:
    """Classifica preco como LOW/MEDIUM/HIGH baseado em quartis historicos."""
    if not metrics:
        return None

    quartiles = {m["quartileRanking"]: float(m["amount"]) for m in metrics}
    first = quartiles.get("FIRST")
    medium = quartiles.get("MEDIUM")

    if first is None or medium is None:
        return None

    if price <= first:
        return "LOW"
    if price <= medium:
        return "MEDIUM"
    return "HIGH"
