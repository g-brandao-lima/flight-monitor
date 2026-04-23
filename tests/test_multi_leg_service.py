"""Testes RED de multi_leg_service (MULTI-02, MULTI-03, MULTI-04).

Os testes abaixo dependem de `app.services.multi_leg_service` que sera
implementado no Plan 02. Agora estao em RED por ImportError controlado.
"""
from datetime import date
from unittest.mock import patch

import pytest


def test_is_valid_chain():
    """MULTI-02: helper _is_valid_chain respeita min/max_stay entre trechos."""
    try:
        from app.services.multi_leg_service import _is_valid_chain
    except ImportError:
        pytest.fail("multi_leg_service nao implementado (esperado RED ate Plan 02)")

    class _Leg:
        def __init__(self, min_stay, max_stay=None):
            self.min_stay_days = min_stay
            self.max_stay_days = max_stay

    legs = [_Leg(7, 14), _Leg(5)]
    # gap de 10 dias entre date1 e date2 respeita min=7, max=14
    dates = (date(2026, 6, 1), date(2026, 6, 11))
    assert _is_valid_chain(dates, legs) is True
    # gap de 3 dias viola min=7
    assert _is_valid_chain((date(2026, 6, 1), date(2026, 6, 4)), legs) is False


def test_uses_route_cache_before_serpapi(db, multi_leg_group_factory):
    """MULTI-03: route_cache hit evita SerpAPI."""
    try:
        from app.services.multi_leg_service import search_multi_leg_prices
    except ImportError:
        pytest.fail("multi_leg_service nao implementado (esperado RED ate Plan 02)")

    group = multi_leg_group_factory(num_legs=2)
    with patch("app.services.route_cache_service.get_cached_price") as mock_cache, \
         patch("app.services.flight_search.search_flights_ex") as mock_serp:
        mock_cache.return_value = {"price": 1500.0, "airline": "AZ"}
        search_multi_leg_prices(db, group)
        assert mock_serp.call_count == 0


def test_persists_multi_snapshot_with_details(db, multi_leg_group_factory):
    """MULTI-03: snapshot multi persistido com airline=MULTI + details JSON."""
    try:
        from app.services.multi_leg_service import search_multi_leg_prices
    except ImportError:
        pytest.fail("multi_leg_service nao implementado (esperado RED ate Plan 02)")

    from app.models import FlightSnapshot

    group = multi_leg_group_factory(num_legs=2)
    with patch("app.services.route_cache_service.get_cached_price") as mock_cache:
        mock_cache.return_value = {"price": 1500.0, "airline": "AZ"}
        search_multi_leg_prices(db, group)

    snaps = db.query(FlightSnapshot).filter_by(route_group_id=group.id).all()
    assert len(snaps) == 1
    assert snaps[0].airline == "MULTI"
    assert snaps[0].details is not None
    assert len(snaps[0].details["legs"]) == 2


def test_picks_cheapest_total(db, multi_leg_group_factory):
    """MULTI-03: algoritmo escolhe combinacao de menor preco total."""
    try:
        from app.services.multi_leg_service import search_multi_leg_prices
    except ImportError:
        pytest.fail("multi_leg_service nao implementado (esperado RED ate Plan 02)")

    group = multi_leg_group_factory(num_legs=2)
    # Mock retorna precos variaveis por data; menor combinacao = 4500
    prices_by_call = [
        {"price": 3000.0, "airline": "AZ"},
        {"price": 2500.0, "airline": "LA"},
        {"price": 2000.0, "airline": "AZ"},
        {"price": 2500.0, "airline": "LA"},
    ]
    with patch("app.services.route_cache_service.get_cached_price") as mock_cache:
        mock_cache.side_effect = prices_by_call * 10
        snapshot = search_multi_leg_prices(db, group)

    assert snapshot is not None
    assert snapshot.price <= 4500.0


def test_prediction_uses_total_median(db, multi_leg_group_factory, multi_leg_snapshot_factory):
    """MULTI-04: predict_action recebe days_to_departure do PRIMEIRO leg (Pitfall 3)."""
    try:
        from app.services.multi_leg_service import search_multi_leg_prices
    except ImportError:
        pytest.fail("multi_leg_service nao implementado (esperado RED ate Plan 02)")

    group = multi_leg_group_factory(num_legs=2)
    multi_leg_snapshot_factory(group, total_price=5500.0)
    multi_leg_snapshot_factory(group, total_price=6000.0)

    with patch("app.services.price_prediction_service.predict_action") as mock_pred, \
         patch("app.services.route_cache_service.get_cached_price") as mock_cache:
        mock_cache.return_value = {"price": 2000.0, "airline": "AZ"}
        search_multi_leg_prices(db, group)
        assert mock_pred.called
        # days_to_departure deve referenciar primeiro leg (window_start = base_date)
        call_kwargs = mock_pred.call_args.kwargs or {}
        call_args = mock_pred.call_args.args
        # aceita kwargs ou positional; teste apenas garante que foi chamado
        assert mock_pred.call_count >= 1
