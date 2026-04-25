"""Testes do route_cache_service (Phase 32 Plan 03)."""
import datetime
from unittest.mock import MagicMock

import pytest

from app.models import RouteCache
from app.services import route_cache_service


def _seed_cache(
    db,
    origin="GRU",
    destination="LIS",
    departure_date=datetime.date(2026, 9, 1),
    return_date=datetime.date(2026, 9, 15),
    min_price=2800.0,
    cached_at=None,
):
    if cached_at is None:
        cached_at = datetime.datetime.utcnow()
    entry = RouteCache(
        origin=origin,
        destination=destination,
        departure_date=departure_date,
        return_date=return_date,
        min_price=min_price,
        currency="BRL",
        cached_at=cached_at,
        source="travelpayouts",
    )
    db.add(entry)
    db.commit()
    return entry


def test_get_cached_price_hit_within_ttl(db):
    _seed_cache(db, cached_at=datetime.datetime.utcnow() - datetime.timedelta(hours=2))

    result = route_cache_service.get_cached_price(
        db, "GRU", "LIS", "2026-09-01", "2026-09-15", ttl_hours=6
    )

    assert result is not None
    assert result["min_price"] == 2800.0
    assert result["source"] == "travelpayouts_cached"


def test_get_cached_price_miss_when_stale(db):
    _seed_cache(db, cached_at=datetime.datetime.utcnow() - datetime.timedelta(hours=10))

    result = route_cache_service.get_cached_price(
        db, "GRU", "LIS", "2026-09-01", "2026-09-15", ttl_hours=6
    )

    assert result is None


def test_get_cached_price_miss_when_absent(db):
    result = route_cache_service.get_cached_price(
        db, "GRU", "LIS", "2026-09-01", "2026-09-15"
    )
    assert result is None


def test_get_cached_price_picks_cheapest_when_multiple(db):
    now = datetime.datetime.utcnow()
    _seed_cache(db, min_price=2800.0, cached_at=now)
    _seed_cache(db, min_price=2500.0, cached_at=now)

    result = route_cache_service.get_cached_price(
        db, "GRU", "LIS", "2026-09-01", "2026-09-15"
    )

    assert result["min_price"] == 2500.0


def test_refresh_top_routes_populates_cache(db):
    client = MagicMock()
    client.is_configured = True
    client.fetch_calendar.return_value = [
        {"origin": "GRU", "destination": "LIS", "departure_date": "2026-09-01",
         "return_date": "2026-09-15", "min_price": 2800.0, "currency": "BRL", "airline": "TP"},
        {"origin": "GRU", "destination": "LIS", "departure_date": "2026-09-02",
         "return_date": "2026-09-16", "min_price": 2900.0, "currency": "BRL", "airline": "LA"},
        {"origin": "GRU", "destination": "LIS", "departure_date": "2026-09-03",
         "return_date": "2026-09-17", "min_price": 3000.0, "currency": "BRL", "airline": "TP"},
    ]

    result = route_cache_service.refresh_top_routes(
        db, client, routes=[("GRU", "LIS")], months=["2026-09"]
    )

    assert result["skipped"] is False
    assert result["upserts"] == 3
    rows = db.query(RouteCache).filter(RouteCache.origin == "GRU").all()
    assert len(rows) == 3


def test_refresh_top_routes_updates_existing(db):
    client = MagicMock()
    client.is_configured = True
    client.fetch_calendar.return_value = [
        {"origin": "GRU", "destination": "LIS", "departure_date": "2026-09-01",
         "return_date": "2026-09-15", "min_price": 2800.0, "currency": "BRL", "airline": "TP"},
    ]

    route_cache_service.refresh_top_routes(
        db, client, routes=[("GRU", "LIS")], months=["2026-09"]
    )
    client.fetch_calendar.return_value = [
        {"origin": "GRU", "destination": "LIS", "departure_date": "2026-09-01",
         "return_date": "2026-09-15", "min_price": 2600.0, "currency": "BRL", "airline": "TP"},
    ]
    route_cache_service.refresh_top_routes(
        db, client, routes=[("GRU", "LIS")], months=["2026-09"]
    )

    rows = db.query(RouteCache).filter(RouteCache.origin == "GRU").all()
    assert len(rows) == 1
    assert rows[0].min_price == 2600.0


def test_refresh_top_routes_skips_when_client_not_configured(db):
    client = MagicMock()
    client.is_configured = False

    result = route_cache_service.refresh_top_routes(
        db, client, routes=[("GRU", "LIS")], months=["2026-09"]
    )

    assert result["skipped"] is True
    client.fetch_calendar.assert_not_called()


def test_next_n_months_returns_correct_count():
    months = route_cache_service._next_n_months(6)
    assert len(months) == 6
    for m in months:
        assert len(m) == 7
        assert m[4] == "-"


def test_top_br_routes_contains_key_routes():
    assert ("GRU", "LIS") in route_cache_service.TOP_BR_ROUTES
    assert ("GRU", "GIG") in route_cache_service.TOP_BR_ROUTES
    assert len(route_cache_service.TOP_BR_ROUTES) == 34
