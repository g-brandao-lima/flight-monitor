"""Garantia de que o preco retornado por search_flights e POR PESSOA.

Bug historico: ate Phase 16, polling usava adults=1 fixo, entao price era por pessoa
por acaso. Phase 16 passou a propagar group.passengers. Como SerpAPI/Google Flights
retornam preco TOTAL (adults * per_person), o valor salvo em snapshot.price virou
total para grupos com pax > 1 mas continuava exibido como "por pessoa".

Este teste previne regressao.
"""
from unittest.mock import MagicMock, patch


@patch("app.services.serpapi_client.GoogleSearch")
@patch("app.services.serpapi_client.settings")
def test_serpapi_divides_total_price_by_adults(mock_settings, mock_search_cls):
    from app.services.serpapi_client import SerpApiClient

    mock_settings.serpapi_api_key = "x"
    mock_instance = MagicMock()
    mock_instance.get_dict.return_value = {
        "best_flights": [{"price": 6000, "flights": [{"airline": "LATAM"}]}],
    }
    mock_search_cls.return_value = mock_instance

    client = SerpApiClient()

    flights_1, _ = client.search_flights_with_insights(
        "GRU", "LIS", "2026-09-15", "2026-09-25", adults=1
    )
    assert flights_1[0]["price"] == 6000

    mock_instance.get_dict.return_value = {
        "best_flights": [{"price": 6000, "flights": [{"airline": "LATAM"}]}],
    }
    flights_2, _ = client.search_flights_with_insights(
        "GRU", "LIS", "2026-09-15", "2026-09-25", adults=2
    )
    assert flights_2[0]["price"] == 3000

    flights_3, _ = client.search_flights_with_insights(
        "GRU", "LIS", "2026-09-15", "2026-09-25", adults=3
    )
    assert flights_3[0]["price"] == 2000


@patch("app.services.flight_search._FF_AVAILABLE", True)
@patch("app.services.flight_search.get_flights_from_filter")
@patch("app.services.flight_search.TFSData")
@patch("app.services.flight_search.Passengers")
@patch("app.services.flight_search.FlightData")
def test_fast_flights_divides_total_price_by_adults(
    _fd_mock, _pax_mock, _tfs_mock, mock_get_flights
):
    from app.services.flight_search import search_flights

    mock_flight = MagicMock()
    mock_flight.price = "R$5000"
    mock_flight.name = "GOL"
    mock_result = MagicMock()
    mock_result.flights = [mock_flight]
    mock_get_flights.return_value = mock_result

    flights_1, _, _ = search_flights(
        "GRU", "LIS", "2026-09-15", "2026-09-25", use_cache=False, adults=1
    )
    assert flights_1[0]["price"] == 5000

    flights_2, _, _ = search_flights(
        "GRU", "LIS", "2026-09-15", "2026-09-25", use_cache=False, adults=2
    )
    assert flights_2[0]["price"] == 2500
