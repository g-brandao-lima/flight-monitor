"""Badge factual de preco no card de grupo (Phase 27)."""
import datetime
from datetime import date

from app.models import FlightSnapshot, RouteGroup
from app.services.dashboard_service import get_groups_with_summary


def _make_group(db, user_id):
    rg = RouteGroup(
        user_id=user_id,
        name="G",
        origins=["GRU"],
        destinations=["LIS"],
        duration_days=7,
        travel_start=date(2026, 7, 1),
        travel_end=date(2026, 7, 31),
        is_active=True,
    )
    db.add(rg)
    db.commit()
    return rg


def _make_snap(db, rg, price, days_ago=0):
    s = FlightSnapshot(
        route_group_id=rg.id,
        origin="GRU",
        destination="LIS",
        departure_date=date(2026, 7, 10),
        return_date=date(2026, 7, 17),
        price=price,
        currency="BRL",
        airline="LATAM",
        collected_at=datetime.datetime.utcnow() - datetime.timedelta(days=days_ago),
    )
    db.add(s)
    db.commit()


def test_badge_menor_preco_em_30_dias(db, test_user):
    """Preco atual igual ao menor em 30d gera badge 'Menor preço em 30 dias'."""
    rg = _make_group(db, test_user.id)
    _make_snap(db, rg, 4000.0, days_ago=20)
    _make_snap(db, rg, 3800.0, days_ago=10)
    _make_snap(db, rg, 3500.0, days_ago=5)
    _make_snap(db, rg, 3200.0, days_ago=0)  # atual

    groups = get_groups_with_summary(db, user_id=test_user.id)
    badge = groups[0]["price_badge"]
    assert badge is not None
    assert "Menor" in badge["label"]
    assert badge["tone"] == "good"


def test_badge_abaixo_da_media(db, test_user):
    """Preco abaixo da media 30d gera badge % abaixo."""
    rg = _make_group(db, test_user.id)
    _make_snap(db, rg, 5000.0, days_ago=20)
    _make_snap(db, rg, 4800.0, days_ago=15)
    _make_snap(db, rg, 4600.0, days_ago=10)
    _make_snap(db, rg, 4000.0, days_ago=5)
    _make_snap(db, rg, 4100.0, days_ago=0)

    groups = get_groups_with_summary(db, user_id=test_user.id)
    badge = groups[0]["price_badge"]
    assert badge is not None
    assert "abaixo da média 30d" in badge["label"]
    assert badge["tone"] == "good"


def test_badge_acima_da_media(db, test_user):
    """Preco muito acima da media 30d gera badge bad."""
    rg = _make_group(db, test_user.id)
    _make_snap(db, rg, 3000.0, days_ago=20)
    _make_snap(db, rg, 3100.0, days_ago=15)
    _make_snap(db, rg, 3200.0, days_ago=10)
    _make_snap(db, rg, 3100.0, days_ago=5)
    _make_snap(db, rg, 4000.0, days_ago=0)

    groups = get_groups_with_summary(db, user_id=test_user.id)
    badge = groups[0]["price_badge"]
    assert badge is not None
    assert "acima da média 30d" in badge["label"]
    assert badge["tone"] == "bad"


def test_no_badge_with_few_samples(db, test_user):
    """Menos de 3 dias de dados nao gera badge."""
    rg = _make_group(db, test_user.id)
    _make_snap(db, rg, 3000.0, days_ago=0)
    _make_snap(db, rg, 3100.0, days_ago=0)

    groups = get_groups_with_summary(db, user_id=test_user.id)
    badge = groups[0]["price_badge"]
    assert badge is None
