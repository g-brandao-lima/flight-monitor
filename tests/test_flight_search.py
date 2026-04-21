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

FF_MOCK_TARGET = "app.services.flight_search.get_flights_from_filter"


# ---------------------------------------------------------------------------
# _parse_price
# ---------------------------------------------------------------------------


def test_parse_price_brl_string():
    from app.services.flight_search import _parse_price

    assert _parse_price("R$690") == 690.0


def test_parse_price_brl_with_dot_thousands():
    from app.services.flight_search import _parse_price

    assert _parse_price("R$1.599") == 1599.0


def test_parse_price_brl_full_format():
    from app.services.flight_search import _parse_price

    assert _parse_price("R$1.599,00") == 1599.0


def test_parse_price_brl_with_decimal_comma():
    from app.services.flight_search import _parse_price

    assert _parse_price("R$823,50") == 823.5


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
# search_flights — SerpAPI only (Phase 31.9 removed fast-flights)
# ---------------------------------------------------------------------------


@patch("app.services.flight_search.SerpApiClient")
def test_search_uses_serpapi(mock_cls):
    from app.services.flight_search import search_flights

    mock_client = MagicMock()
    mock_client.search_flights_with_insights.return_value = (
        MOCK_SERPAPI_FLIGHTS,
        MOCK_SERPAPI_INSIGHTS,
    )
    mock_cls.return_value = mock_client

    flights, insights, source = search_flights(
        "GRU", "GIG", "2026-05-01", "2026-05-08", use_cache=False
    )

    assert source == "serpapi"
    assert insights == MOCK_SERPAPI_INSIGHTS
    assert flights[0]["price"] == 480.0


@patch("app.services.flight_search.SerpApiClient")
def test_search_propagates_error_when_serpapi_fails(mock_cls):
    from app.services.flight_search import search_flights

    mock_client = MagicMock()
    mock_client.search_flights_with_insights.side_effect = Exception("SerpAPI quota")
    mock_cls.return_value = mock_client

    with pytest.raises(Exception):
        search_flights("GRU", "GIG", "2026-05-01", "2026-05-08", use_cache=False)


# HYG-03 — fast-flights removido (Phase 31.9)

def test_flight_search_nao_importa_fast_flights():
    """HYG-03: fast-flights foi removido do orchestrator."""
    from pathlib import Path
    source = Path("app/services/flight_search.py").read_text(encoding="utf-8")
    assert "fast_flights" not in source
    assert "FlightData" not in source
    assert "TFSData" not in source


def test_flight_search_nao_expoe_helpers_fast_flights():
    """HYG-03: funcoes auxiliares de fast-flights foram removidas."""
    import app.services.flight_search as fs
    assert not hasattr(fs, "_search_fast_flights")
    assert not hasattr(fs, "_FF_AVAILABLE")
