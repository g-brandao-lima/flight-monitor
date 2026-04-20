"""Testes do painel admin /admin/stats (Phase 24)."""
import datetime
from datetime import date
from unittest.mock import patch

import pytest

from app.models import FlightSnapshot, RouteGroup


def _make_group(db, user_id: int) -> RouteGroup:
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


def _make_snap(db, rg, source="serpapi"):
    s = FlightSnapshot(
        route_group_id=rg.id,
        origin="GRU",
        destination="LIS",
        departure_date=date(2026, 7, 10),
        return_date=date(2026, 7, 17),
        price=3000.0,
        currency="BRL",
        airline="LATAM",
        source=source,
        collected_at=datetime.datetime.utcnow(),
    )
    db.add(s)
    db.commit()


@pytest.fixture
def set_admin_email(monkeypatch):
    def _set(email: str):
        from app.config import settings
        monkeypatch.setattr(settings, "admin_email", email)
    return _set


def test_admin_stats_returns_404_when_no_admin_email_configured(client, set_admin_email):
    """Sem ADMIN_EMAIL configurado, ninguem e admin."""
    set_admin_email("")
    response = client.get("/admin/stats", follow_redirects=False)
    assert response.status_code == 404


def test_admin_stats_returns_404_for_non_admin_user(client, set_admin_email):
    """Usuario logado que nao bate com ADMIN_EMAIL recebe 404 (nao 403)."""
    set_admin_email("outro@example.com")
    response = client.get("/admin/stats", follow_redirects=False)
    assert response.status_code == 404


def test_admin_stats_returns_200_for_admin(client, test_user, db, set_admin_email):
    """Usuario com email == ADMIN_EMAIL recebe o painel."""
    _make_group(db, test_user.id)
    set_admin_email(test_user.email)
    response = client.get("/admin/stats", follow_redirects=False)
    assert response.status_code == 200
    assert "Painel Admin" in response.text
    assert "Quota SerpAPI" in response.text


def test_admin_stats_shows_source_distribution(client, test_user, db, set_admin_email):
    """Quando ha snapshots, painel mostra distribuicao por fonte."""
    rg = _make_group(db, test_user.id)
    _make_snap(db, rg, source="serpapi")
    _make_snap(db, rg, source="serpapi")
    _make_snap(db, rg, source="fast_flights")
    set_admin_email(test_user.email)
    response = client.get("/admin/stats", follow_redirects=False)
    assert response.status_code == 200
    assert "Google Flights (API oficial)" in response.text
    assert "Google Flights (fallback)" in response.text


def test_admin_stats_shows_next_reset_date(client, test_user, set_admin_email):
    """Painel mostra data de reset da quota SerpAPI."""
    set_admin_email(test_user.email)
    response = client.get("/admin/stats", follow_redirects=False)
    assert response.status_code == 200
    assert "Reset em" in response.text


def test_unauthenticated_user_redirects_on_admin(unauthenticated_client):
    """Usuario nao logado e redirecionado pelo AuthMiddleware."""
    response = unauthenticated_client.get("/admin/stats", follow_redirects=False)
    assert response.status_code in (303, 401, 404)
