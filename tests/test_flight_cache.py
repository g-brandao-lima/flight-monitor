"""Cache in-memory de search_flights (Phase 20)."""
from unittest.mock import patch, MagicMock

import pytest

from app.services import flight_cache
from app.services.flight_search import search_flights, search_flights_ex


@pytest.fixture(autouse=True)
def _reset_cache():
    flight_cache.clear()
    yield
    flight_cache.clear()


def test_cache_stores_and_returns_value():
    key = flight_cache.make_key("GRU", "LIS", "2026-06-01", "2026-06-15", None, 1)
    flight_cache.put(key, (["flight1"], {"insight": 1}, "serpapi"))

    assert flight_cache.get(key) == (["flight1"], {"insight": 1}, "serpapi")


def test_cache_miss_returns_none():
    key = flight_cache.make_key("XXX", "YYY", "2099-01-01", "2099-01-08", None, 1)
    assert flight_cache.get(key) is None


def test_cache_respects_ttl_expiry():
    key = flight_cache.make_key("GRU", "LIS", "2026-06-01", "2026-06-15", None, 1)
    flight_cache.put(key, (["flight1"], None, "serpapi"))

    assert flight_cache.get(key, ttl_seconds=0) is None


def test_cache_key_differs_by_passengers():
    key_1pax = flight_cache.make_key("GRU", "LIS", "2026-06-01", "2026-06-15", None, 1)
    key_2pax = flight_cache.make_key("GRU", "LIS", "2026-06-01", "2026-06-15", None, 2)
    assert key_1pax != key_2pax


@patch("app.services.flight_search.SerpApiClient")
def test_search_flights_hits_cache_on_second_call(mock_cls):
    mock_client = MagicMock()
    mock_client.search_flights_with_insights.return_value = (
        [{"price": 3000.0, "airline": "LATAM"}],
        None,
    )
    mock_cls.return_value = mock_client

    f1, i1, s1, cache_hit_1 = search_flights_ex(
        "GRU", "LIS", "2026-06-01", "2026-06-15", adults=1
    )
    assert cache_hit_1 is False
    assert mock_client.search_flights_with_insights.call_count == 1

    f2, i2, s2, cache_hit_2 = search_flights_ex(
        "GRU", "LIS", "2026-06-01", "2026-06-15", adults=1
    )
    assert cache_hit_2 is True
    assert mock_client.search_flights_with_insights.call_count == 1
    assert f2 == f1


@patch("app.services.flight_search.SerpApiClient")
def test_cache_bypass_with_use_cache_false(mock_cls):
    mock_client = MagicMock()
    mock_client.search_flights_with_insights.return_value = (
        [{"price": 3000.0, "airline": "LATAM"}],
        None,
    )
    mock_cls.return_value = mock_client

    search_flights("GRU", "LIS", "2026-06-01", "2026-06-15")
    search_flights("GRU", "LIS", "2026-06-01", "2026-06-15", use_cache=False)

    assert mock_client.search_flights_with_insights.call_count == 2
