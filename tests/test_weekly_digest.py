"""Weekly digest service (Phase 29)."""
import datetime
from datetime import date

from app.models import FlightSnapshot, RouteGroup
from app.services.weekly_digest_service import build_user_digest, compose_digest_email


def _make_group(db, user_id, name="Test"):
    rg = RouteGroup(
        user_id=user_id,
        name=name,
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


def test_user_without_groups_returns_none(db, test_user):
    assert build_user_digest(db, test_user) is None


def test_user_with_group_but_no_snapshots_returns_none(db, test_user):
    _make_group(db, test_user.id)
    assert build_user_digest(db, test_user) is None


def test_digest_with_recent_snapshot_and_week_ago_computes_delta(db, test_user):
    rg = _make_group(db, test_user.id, name="Europa")
    _make_snap(db, rg, 4000.0, days_ago=7)
    _make_snap(db, rg, 3500.0, days_ago=0)

    digest = build_user_digest(db, test_user)
    assert digest is not None
    assert len(digest["items"]) == 1
    item = digest["items"][0]
    assert item["price_now"] == 3500.0
    assert item["price_week_ago"] == 4000.0
    assert item["delta_pct"] < 0
    assert item["direction"] == "down"


def test_digest_without_week_ago_sample_still_returns_item(db, test_user):
    rg = _make_group(db, test_user.id)
    _make_snap(db, rg, 3500.0, days_ago=0)

    digest = build_user_digest(db, test_user)
    assert digest is not None
    item = digest["items"][0]
    assert item["delta_pct"] is None
    assert item["direction"] == "stable"


def test_compose_digest_email_has_subject_and_html(db, test_user):
    rg = _make_group(db, test_user.id, name="Europa")
    _make_snap(db, rg, 3500.0, days_ago=0)
    digest = build_user_digest(db, test_user)

    msg = compose_digest_email(digest)
    assert "resumo semanal" in msg["Subject"].lower()
    assert msg["To"] == test_user.email

    parts = msg.get_payload()
    html_body = next(p for p in parts if p.get_content_type() == "text/html").get_payload(decode=True).decode()
    assert "Europa" in html_body
    assert "R$" in html_body
