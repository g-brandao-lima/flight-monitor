"""Hero carousel na landing (quick 260423-1fg).

Cobre service get_hero_routes, injecao de contexto na rota / e markup do template.
"""
import datetime
from datetime import timedelta

import pytest

from app.models import RouteCache
from app.services import public_route_service


def _seed_route_cache(
    db,
    origin: str,
    destination: str,
    min_price: float,
    cached_at: datetime.datetime,
    departure_date: datetime.date | None = None,
    return_date: datetime.date | None = None,
) -> RouteCache:
    row = RouteCache(
        origin=origin,
        destination=destination,
        departure_date=departure_date or datetime.date(2026, 9, 1),
        return_date=return_date or datetime.date(2026, 9, 15),
        min_price=min_price,
        currency="BRL",
        cached_at=cached_at,
        source="travelpayouts",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


# ----------------------- Task 1: service -----------------------


def test_get_hero_routes_returns_top_6_by_cached_at_desc(db):
    now = datetime.datetime.utcnow()
    pairs = [
        ("GRU", "SDU"), ("CGH", "BSB"), ("GIG", "REC"),
        ("SSA", "FOR"), ("POA", "CWB"), ("BEL", "MAO"),
        ("GRU", "LIS"), ("GRU", "MIA"),
    ]
    for i, (o, d) in enumerate(pairs):
        _seed_route_cache(db, o, d, 1000.0, now - timedelta(hours=i))

    result = public_route_service.get_hero_routes(db, limit=6)

    assert len(result) == 6
    returned_pairs = [(r["origin"], r["destination"]) for r in result]
    # Mais recentes primeiro
    assert returned_pairs == pairs[:6]


def test_get_hero_routes_filters_price_gt_zero(db):
    now = datetime.datetime.utcnow()
    _seed_route_cache(db, "GRU", "AAA", 0.0, now - timedelta(hours=1))
    _seed_route_cache(db, "GRU", "BBB", 0, now - timedelta(hours=2))
    _seed_route_cache(db, "GRU", "CCC", -5.0, now - timedelta(hours=3))
    _seed_route_cache(db, "GRU", "DDD", 1500.0, now - timedelta(hours=4))
    _seed_route_cache(db, "GRU", "EEE", 2000.0, now - timedelta(hours=5))

    result = public_route_service.get_hero_routes(db, limit=6)

    assert len(result) == 2
    destinations = {r["destination"] for r in result}
    assert destinations == {"DDD", "EEE"}


def test_get_hero_routes_empty_returns_empty_list(db):
    result = public_route_service.get_hero_routes(db, limit=6)
    assert result == []
    assert isinstance(result, list)


def test_get_hero_routes_respects_limit(db):
    now = datetime.datetime.utcnow()
    for i in range(10):
        _seed_route_cache(db, "GRU", f"D{i:02d}"[:3], 1000.0 + i, now - timedelta(hours=i))

    result = public_route_service.get_hero_routes(db, limit=3)

    assert len(result) == 3


def test_get_hero_routes_shape(db):
    now = datetime.datetime.utcnow()
    _seed_route_cache(
        db, "GRU", "SDU", 1499.0, now,
        departure_date=datetime.date(2026, 10, 1),
        return_date=datetime.date(2026, 10, 10),
    )

    result = public_route_service.get_hero_routes(db, limit=6)

    assert len(result) == 1
    item = result[0]
    expected_keys = {
        "origin", "destination", "origin_city", "destination_city",
        "min_price", "departure_date", "return_date", "cached_at",
    }
    assert set(item.keys()) == expected_keys
    assert item["origin"] == "GRU"
    assert item["destination"] == "SDU"
    assert item["min_price"] == 1499.0
    assert item["departure_date"] == datetime.date(2026, 10, 1)
    assert item["return_date"] == datetime.date(2026, 10, 10)
    assert isinstance(item["origin_city"], str) and item["origin_city"]
    assert isinstance(item["destination_city"], str) and item["destination_city"]


# ----------------------- Task 2: landing handler injection -----------------------


def test_landing_injects_hero_routes_context(unauthenticated_client, db):
    now = datetime.datetime.utcnow()
    _seed_route_cache(db, "GRU", "SDU", 1200.0, now - timedelta(hours=1))
    _seed_route_cache(db, "CGH", "BSB", 1400.0, now - timedelta(hours=2))
    _seed_route_cache(db, "GIG", "REC", 1600.0, now - timedelta(hours=3))

    r = unauthenticated_client.get("/")

    assert r.status_code == 200
    assert "hero-carousel" in r.text
    assert "GRU" in r.text
    assert "SDU" in r.text
    assert "CGH" in r.text
    assert "BSB" in r.text
    assert "GIG" in r.text
    assert "REC" in r.text


def test_landing_falls_back_when_route_cache_empty(unauthenticated_client, db):
    r = unauthenticated_client.get("/")

    assert r.status_code == 200
    # Seja fallback featured_route ou card exemplo hardcoded, pagina deve renderizar
    # sem quebrar e sem laços vazios no hero.
    assert "hero-carousel-fallback" in r.text or "landing-preview" in r.text


# ----------------------- Task 3: template markup -----------------------


def test_landing_renders_six_carousel_slides(unauthenticated_client, db):
    now = datetime.datetime.utcnow()
    origins = ["GRU", "CGH", "BSB", "GIG", "REC", "SSA"]
    dests = ["SDU", "BSB", "REC", "SSA", "FOR", "MAO"]
    for i, (o, d) in enumerate(zip(origins, dests)):
        _seed_route_cache(db, o, d, 1000.0 + i * 50, now - timedelta(hours=i))

    r = unauthenticated_client.get("/")

    assert r.status_code == 200
    assert r.text.count('class="landing-preview landing-preview-link hero-carousel-slide') == 6
    for code in origins + dests:
        assert code in r.text
    assert "hero-carousel-prev" in r.text
    assert "hero-carousel-next" in r.text
    assert "hero-carousel-dots" in r.text
    assert "data-hero-carousel" in r.text


def test_landing_hero_carousel_has_accessible_controls(unauthenticated_client, db):
    now = datetime.datetime.utcnow()
    _seed_route_cache(db, "GRU", "SDU", 1200.0, now - timedelta(hours=1))
    _seed_route_cache(db, "CGH", "BSB", 1400.0, now - timedelta(hours=2))

    r = unauthenticated_client.get("/")

    assert r.status_code == 200
    assert 'aria-label="Proxima rota"' in r.text
    assert 'aria-label="Rota anterior"' in r.text
    assert 'role="region"' in r.text
    assert 'aria-roledescription="carrossel"' in r.text
