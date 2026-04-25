"""Testes RED para short-circuit de polling quando quota SerpAPI esgota.

Cobre:
- run_polling_cycle nao chama SerpAPI quando quota=0.
- run_polling_cycle retorna dict de stats.
- manual_polling redireciona com flash polling_sem_quota quando quota=0.
- TOP_BR_ROUTES inclui as 8 rotas BR-internacional do spec.
- Warning de quota nao mente sobre fast-flights e cita cache Travelpayouts.
"""
import datetime
import logging
from unittest.mock import patch

import pytest

from app.models import ApiUsage, RouteGroup
from app.services import polling_service
from app.services.quota_service import MONTHLY_QUOTA


def _exhaust_quota(db) -> None:
    """Insere ApiUsage com search_count = MONTHLY_QUOTA pro mes corrente."""
    ym = datetime.datetime.utcnow().strftime("%Y-%m")
    record = ApiUsage(year_month=ym, search_count=MONTHLY_QUOTA)
    db.add(record)
    db.commit()


def _make_active_group(db, user) -> RouteGroup:
    today = datetime.date.today()
    group = RouteGroup(
        user_id=user.id,
        name="Test Group",
        origins=["GRU"],
        destinations=["GIG"],
        duration_days=7,
        travel_start=today + datetime.timedelta(days=30),
        travel_end=today + datetime.timedelta(days=60),
        passengers=1,
        max_stops=None,
        mode="normal",
        is_active=True,
    )
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


@pytest.mark.unit
def test_run_polling_cycle_with_quota_zero_skips_serpapi(db, test_user, monkeypatch):
    # Arrange
    _exhaust_quota(db)
    _make_active_group(db, test_user)

    monkeypatch.setattr(polling_service, "SessionLocal", lambda: db)

    serpapi_mock = patch(
        "app.services.serpapi_client.search_flights"
    ).start()
    try:
        # Act
        polling_service.run_polling_cycle(user_id=test_user.id)
        # Assert
        assert serpapi_mock.call_count == 0, (
            "SerpAPI nao deveria ser chamada quando quota mensal esta zerada"
        )
    finally:
        patch.stopall()


@pytest.mark.unit
def test_run_polling_cycle_returns_stats_dict(db, test_user, monkeypatch):
    # Arrange
    monkeypatch.setattr(polling_service, "SessionLocal", lambda: db)

    # Act
    result = polling_service.run_polling_cycle(user_id=test_user.id)

    # Assert
    assert isinstance(result, dict), "run_polling_cycle deveria retornar dict de stats"
    for key in (
        "processed_groups",
        "snapshots_created",
        "snapshots_skipped_quota",
        "snapshots_skipped_no_data",
    ):
        assert key in result, f"chave esperada {key!r} ausente em {result!r}"


@pytest.mark.unit
def test_manual_polling_flash_when_quota_zero(authenticated_client, db):
    # Arrange
    _exhaust_quota(db)

    # Act
    response = authenticated_client.post(
        "/polling/manual", follow_redirects=False
    )

    # Assert
    assert response.status_code == 303
    assert "msg=polling_sem_quota" in response.headers.get("location", "")


@pytest.mark.unit
def test_travelpayouts_cron_includes_international_routes():
    # Arrange / Act
    from app.services.route_cache_service import TOP_BR_ROUTES

    # Assert
    expected = {
        ("GRU", "SCL"),
        ("GIG", "SCL"),
        ("BSB", "SCL"),
        ("GRU", "EZE"),
        ("GIG", "EZE"),
        ("GRU", "LIM"),
        ("GRU", "BOG"),
        ("GRU", "MEX"),
    }
    missing = expected - set(TOP_BR_ROUTES)
    assert not missing, f"rotas BR-internacional ausentes do cron: {missing}"


@pytest.mark.unit
def test_quota_exhausted_warning_message_no_fast_flights(
    db, test_user, monkeypatch, caplog
):
    # Arrange
    _exhaust_quota(db)
    monkeypatch.setattr(polling_service, "SessionLocal", lambda: db)

    # Act
    with caplog.at_level(logging.WARNING, logger="app.services.polling_service"):
        polling_service.run_polling_cycle(user_id=test_user.id)

    # Assert
    messages = " ".join(record.getMessage() for record in caplog.records)
    assert "fast-flights" not in messages, (
        "warning de quota nao deve mencionar fast-flights (removido em v2.3)"
    )
    assert "cache Travelpayouts" in messages, (
        "warning deveria citar cache Travelpayouts como caminho real"
    )
