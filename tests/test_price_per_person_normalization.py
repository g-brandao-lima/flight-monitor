"""Garantia de que a busca sempre usa adults=1 (PER PERSON price).

Bug historico: ate Phase 16, adults=1 hardcoded -> price por pessoa correto.
Phase 16 passou a propagar group.passengers -> Google Flights retornou preco
TOTAL em rotas internacionais (REC-SCL etc) mas PREÇO POR PESSOA em domesticas
(CPV-CGH, REC-RAO etc). Comportamento inconsistente impossibilita normalizar
cegamente.

Solucao: sempre chamar API com adults=1. snapshot.price e sempre por pessoa.
Template multiplica por pax no display de 'total da viagem'.

Este teste previne regressao do Phase 16.
"""
from unittest.mock import MagicMock, patch


@patch("app.services.serpapi_client.GoogleSearch")
@patch("app.services.serpapi_client.settings")
def test_serpapi_always_calls_with_adults_1(mock_settings, mock_search_cls):
    """Mesmo quando caller pede adults=N, SerpAPI e chamado com adults=1."""
    from app.services.serpapi_client import SerpApiClient

    mock_settings.serpapi_api_key = "x"
    mock_instance = MagicMock()
    mock_instance.get_dict.return_value = {
        "best_flights": [{"price": 3000, "flights": [{"airline": "LATAM"}]}],
    }
    mock_search_cls.return_value = mock_instance

    client = SerpApiClient()

    client.search_flights_with_insights(
        "GRU", "LIS", "2026-09-15", "2026-09-25", adults=3
    )

    params_sent = mock_search_cls.call_args[0][0]
    assert params_sent["adults"] == 1, "Deve forcar adults=1 independente do parametro recebido"


@patch("app.services.serpapi_client.GoogleSearch")
@patch("app.services.serpapi_client.settings")
def test_serpapi_returns_price_as_is_no_division(mock_settings, mock_search_cls):
    """Price retornado nao e manipulado, vem direto da API."""
    from app.services.serpapi_client import SerpApiClient

    mock_settings.serpapi_api_key = "x"
    mock_instance = MagicMock()
    mock_instance.get_dict.return_value = {
        "best_flights": [{"price": 3000, "flights": [{"airline": "LATAM"}]}],
    }
    mock_search_cls.return_value = mock_instance

    client = SerpApiClient()
    flights, _ = client.search_flights_with_insights(
        "GRU", "LIS", "2026-09-15", "2026-09-25", adults=2
    )
    assert flights[0]["price"] == 3000, "Preco deve vir intacto da API"


@patch("app.services.flight_search._FF_AVAILABLE", True)
@patch("app.services.flight_search.get_flights_from_filter")
@patch("app.services.flight_search.TFSData")
@patch("app.services.flight_search.Passengers")
@patch("app.services.flight_search.FlightData")
def test_fast_flights_always_uses_adults_1(
    _fd_mock, mock_pax, _tfs_mock, mock_get_flights
):
    """Mesmo com caller pedindo adults=N, fast-flights e chamado com adults=1."""
    from app.services.flight_search import search_flights

    mock_flight = MagicMock()
    mock_flight.price = "R$2500"
    mock_flight.name = "GOL"
    mock_result = MagicMock()
    mock_result.flights = [mock_flight]
    mock_get_flights.return_value = mock_result

    search_flights(
        "GRU", "LIS", "2026-09-15", "2026-09-25", use_cache=False, adults=3
    )

    mock_pax.assert_called_once_with(adults=1)
