"""Simulador de economia desde a criacao do grupo (Phase 31)."""
import datetime
from datetime import date

from app.models import FlightSnapshot, RouteGroup
from app.services.dashboard_service import get_groups_with_summary


def _make_group_at(db, user_id, created_days_ago: int):
    created_at = datetime.datetime.utcnow() - datetime.timedelta(days=created_days_ago)
    rg = RouteGroup(
        user_id=user_id,
        name="Test",
        origins=["GRU"],
        destinations=["LIS"],
        duration_days=7,
        travel_start=date(2026, 7, 1),
        travel_end=date(2026, 7, 31),
        is_active=True,
        created_at=created_at,
    )
    db.add(rg)
    db.commit()
    db.refresh(rg)
    return rg


def _snap_at(db, rg, price, collected_days_ago):
    s = FlightSnapshot(
        route_group_id=rg.id,
        origin="GRU",
        destination="LIS",
        departure_date=date(2026, 7, 10),
        return_date=date(2026, 7, 17),
        price=price,
        currency="BRL",
        airline="LATAM",
        collected_at=datetime.datetime.utcnow() - datetime.timedelta(days=collected_days_ago),
    )
    db.add(s)
    db.commit()


def test_savings_saved_when_price_dropped(db, test_user):
    rg = _make_group_at(db, test_user.id, created_days_ago=10)
    _snap_at(db, rg, 4000.0, collected_days_ago=10)  # inicial
    _snap_at(db, rg, 3200.0, collected_days_ago=0)   # atual

    groups = get_groups_with_summary(db, user_id=test_user.id)
    s = groups[0]["savings"]
    assert s is not None
    assert s["direction"] == "saved"
    assert s["delta"] == 800.0


def test_savings_lost_when_price_rose(db, test_user):
    rg = _make_group_at(db, test_user.id, created_days_ago=10)
    _snap_at(db, rg, 3000.0, collected_days_ago=10)  # inicial
    _snap_at(db, rg, 3600.0, collected_days_ago=0)   # atual maior

    groups = get_groups_with_summary(db, user_id=test_user.id)
    s = groups[0]["savings"]
    assert s is not None
    assert s["direction"] == "lost"
    assert s["delta"] == 600.0


def test_savings_even_when_price_stable(db, test_user):
    rg = _make_group_at(db, test_user.id, created_days_ago=10)
    _snap_at(db, rg, 3000.0, collected_days_ago=10)
    _snap_at(db, rg, 3005.0, collected_days_ago=0)

    groups = get_groups_with_summary(db, user_id=test_user.id)
    s = groups[0]["savings"]
    assert s is not None
    assert s["direction"] == "even"


def test_savings_none_without_initial_snapshot(db, test_user):
    rg = _make_group_at(db, test_user.id, created_days_ago=10)
    _snap_at(db, rg, 3500.0, collected_days_ago=0)  # so snapshot atual

    groups = get_groups_with_summary(db, user_id=test_user.id)
    assert groups[0]["savings"] is None
