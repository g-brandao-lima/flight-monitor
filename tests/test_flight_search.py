"""Tests for flight_search — dual-source (fast-flights + SerpAPI fallback)."""
import datetime
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MOCK_FF_RESULT = MagicMock()
MOCK_FF_RESULT.flights = [
    MagicMock(name="LATAM", price="R$450", stops=0, is_best=True),
    MagicMock(name="Gol", price="R$550", stops=1, is_best=False),
    MagicMock(name="LATAM", price="R$680", stops=0, is_best=False),
]
# Fix MagicMock .name attribute (it's special in MagicMock)
MOCK_FF_RESULT.flights[0].configure_mock(name="LATAM")
MOCK_FF_RESULT.flights[1].configure_mock(name="Gol")
MOCK_FF_RESULT.flights[2].configure_mock(name="LATAM")
MOCK_FF_RESULT.flights[0].price = "R$450"
MOCK_FF_RESULT.flights[1].price = "R$550"
MOCK_FF_RESULT.flights[2].price = "R$680"

MOCK_SERPAPI_FLIGHTS = [
    {"price": 480.0, "airline": "LATAM", "flights": [], "type": "Round trip"},
]
MOCK_SERPAPI_INSIGHTS = {
    "lowest_price": 400,
    "typical_price_range": [400, 700],
}


# ---------------------------------------------------------------------------
# _parse_price
# ---------------------------------------------------------------------------


def test_parse_price_brl_string():
    from app.services.flight_search import _parse_price

    assert _parse_price("R$690") == 690.0


def test_parse_price_with_comma():
    from app.services.flight_search import _parse_price

    assert _parse_price("R$1,234") == 1234.0


def test_parse_price_already_clean():
    from app.services.flight_search import _parse_price

    assert _parse_price("890") == 890.0


def test_parse_price_returns_none_on_empty():
    from app.services.flight_search import _parse_price

    assert _parse_price("") is None
    assert _parse_price(None) is None


def test_parse_price_returns_none_on_non_numeric():
    from app.services.flight_search import _parse_price

    assert _parse_price("sem preco") is None


# ---------------------------------------------------------------------------
# search_flights — source routing
# ---------------------------------------------------------------------------


@patch("app.services.flight_search.get_flights")
def test_search_uses_fast_flights_when_available(mock_gf):
    from app.services.flight_search import search_flights

    mock_result = MagicMock()
    flight = MagicMock()
    flight.price = "R$450"
    flight.configure_mock(name="LATAM")
    mock_result.flights = [flight]
    mock_gf.return_value = mock_result

    flights, insights, source = search_flights(
        "GRU", "GIG", "2026-05-01", "2026-05-08"
    )

    assert source == "fast_flights"
    assert insights is None
    assert len(flights) >= 1
    assert flights[0]["price"] == 450.0
    assert flights[0]["airline"] == "LATAM"


@patch("app.services.flight_search.SerpApiClient")
@patch("app.services.flight_search.get_flights")
def test_search_falls_back_to_serpapi_on_fast_flights_failure(mock_gf, mock_cls):
    from app.services.flight_search import search_flights

    mock_gf.side_effect = RuntimeError("protobuf schema changed")

    mock_client = MagicMock()
    mock_client.search_flights_with_insights.return_value = (
        MOCK_SERPAPI_FLIGHTS,
        MOCK_SERPAPI_INSIGHTS,
    )
    mock_cls.return_value = mock_client

    flights, insights, source = search_flights(
        "GRU", "GIG", "2026-05-01", "2026-05-08"
    )

    assert source == "serpapi"
    assert insights == MOCK_SERPAPI_INSIGHTS
    assert flights[0]["price"] == 480.0


@patch("app.services.flight_search.SerpApiClient")
@patch("app.services.flight_search.get_flights")
def test_search_propagates_error_when_both_fail(mock_gf, mock_cls):
    from app.services.flight_search import search_flights

    mock_gf.side_effect = RuntimeError("fast-flights down")
    mock_client = MagicMock()
    mock_client.search_flights_with_insights.side_effect = Exception("SerpAPI quota")
    mock_cls.return_value = mock_client

    with pytest.raises(Exception):
        search_flights("GRU", "GIG", "2026-05-01", "2026-05-08")


@patch("app.services.flight_search.get_flights")
def test_search_raises_when_fast_flights_returns_empty(mock_gf):
    """fast-flights sem resultados e tratado como falha → tenta SerpAPI."""
    from app.services.flight_search import search_flights

    mock_result = MagicMock()
    mock_result.flights = []
    mock_gf.return_value = mock_result

    with patch("app.services.flight_search.SerpApiClient") as mock_cls:
        mock_client = MagicMock()
        mock_client.search_flights_with_insights.return_value = (
            MOCK_SERPAPI_FLIGHTS,
            MOCK_SERPAPI_INSIGHTS,
        )
        mock_cls.return_value = mock_client

        flights, insights, source = search_flights(
            "GRU", "GIG", "2026-05-01", "2026-05-08"
        )

    assert source == "serpapi"


@patch("app.services.flight_search.get_flights")
def test_search_respects_max_results(mock_gf):
    from app.services.flight_search import search_flights

    mock_result = MagicMock()
    flights_raw = []
    for i in range(10):
        f = MagicMock()
        f.price = f"R${500 + i * 10}"
        f.configure_mock(name="LATAM")
        flights_raw.append(f)
    mock_result.flights = flights_raw
    mock_gf.return_value = mock_result

    flights, _, _ = search_flights(
        "GRU", "GIG", "2026-05-01", "2026-05-08", max_results=3
    )

    assert len(flights) == 3


@patch("app.services.flight_search.get_flights")
def test_search_returns_sorted_by_price(mock_gf):
    from app.services.flight_search import search_flights

    mock_result = MagicMock()
    f1, f2, f3 = MagicMock(), MagicMock(), MagicMock()
    f1.price = "R$700"
    f1.configure_mock(name="GOL")
    f2.price = "R$450"
    f2.configure_mock(name="LATAM")
    f3.price = "R$580"
    f3.configure_mock(name="AZUL")
    mock_result.flights = [f1, f2, f3]
    mock_gf.return_value = mock_result

    flights, _, _ = search_flights("GRU", "GIG", "2026-05-01", "2026-05-08")

    prices = [f["price"] for f in flights]
    assert prices == sorted(prices)


@patch("app.services.flight_search.get_flights")
def test_search_passes_max_stops_to_fast_flights(mock_gf):
    from app.services.flight_search import search_flights

    mock_result = MagicMock()
    f = MagicMock()
    f.price = "R$500"
    f.configure_mock(name="LATAM")
    mock_result.flights = [f]
    mock_gf.return_value = mock_result

    search_flights("GRU", "GIG", "2026-05-01", "2026-05-08", max_stops=0)

    call_kwargs = mock_gf.call_args.kwargs
    assert call_kwargs.get("max_stops") == 0


@patch("app.services.flight_search.get_flights")
def test_search_normalized_dict_has_required_keys(mock_gf):
    from app.services.flight_search import search_flights

    mock_result = MagicMock()
    f = MagicMock()
    f.price = "R$500"
    f.configure_mock(name="LATAM")
    mock_result.flights = [f]
    mock_gf.return_value = mock_result

    flights, _, _ = search_flights("GRU", "GIG", "2026-05-01", "2026-05-08")

    assert "price" in flights[0]
    assert "airline" in flights[0]
    assert isinstance(flights[0]["price"], float)