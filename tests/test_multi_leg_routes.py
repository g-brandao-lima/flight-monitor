"""Testes RED de rota POST /groups com legs[] (MULTI-01).

Dependem da extensao do handler em app/routes/route_groups.py no Plan 03.
"""
from datetime import date, timedelta

import pytest


def test_create_multi_leg_group_valid(client, db, test_user):
    """MULTI-01: POST /groups com mode=multi_leg e 2 legs cria grupo persistido."""
    from app.models import RouteGroup, RouteGroupLeg

    base = date(2026, 7, 1)
    form = {
        "mode": "multi_leg",
        "name": "Eurotrip",
        "passengers": "1",
        "legs[1][order]": "1",
        "legs[1][origin]": "GRU",
        "legs[1][destination]": "FCO",
        "legs[1][window_start]": base.isoformat(),
        "legs[1][window_end]": (base + timedelta(days=7)).isoformat(),
        "legs[1][min_stay_days]": "7",
        "legs[2][order]": "2",
        "legs[2][origin]": "FCO",
        "legs[2][destination]": "GRU",
        "legs[2][window_start]": (base + timedelta(days=20)).isoformat(),
        "legs[2][window_end]": (base + timedelta(days=27)).isoformat(),
        "legs[2][min_stay_days]": "1",
    }

    resp = client.post("/groups", data=form, follow_redirects=False)
    assert resp.status_code in (200, 201, 302, 303), (
        f"expected multi-leg POST success, got {resp.status_code}: {resp.text[:500]}"
    )
    group = db.query(RouteGroup).filter_by(name="Eurotrip").first()
    assert group is not None, "grupo multi nao foi persistido"
    assert group.mode == "multi_leg"
    legs = db.query(RouteGroupLeg).filter_by(route_group_id=group.id).all()
    assert len(legs) == 2


def test_create_multi_leg_group_invalid_chain(client, db):
    """MULTI-02: POST com encadeamento invalido retorna erro com copy pt-BR."""
    base = date(2026, 7, 1)
    form = {
        "mode": "multi_leg",
        "name": "Invalido",
        "passengers": "1",
        "legs[1][order]": "1",
        "legs[1][origin]": "GRU",
        "legs[1][destination]": "FCO",
        "legs[1][window_start]": base.isoformat(),
        "legs[1][window_end]": (base + timedelta(days=7)).isoformat(),
        "legs[1][min_stay_days]": "10",
        "legs[2][order]": "2",
        "legs[2][origin]": "FCO",
        "legs[2][destination]": "GRU",
        "legs[2][window_start]": (base + timedelta(days=8)).isoformat(),  # invalido
        "legs[2][window_end]": (base + timedelta(days=15)).isoformat(),
        "legs[2][min_stay_days]": "1",
    }

    resp = client.post("/groups", data=form, follow_redirects=False)
    # aceita 422 (Pydantic) ou 200/400 com erro renderizado
    body = resp.text if resp.status_code != 302 else ""
    assert (
        resp.status_code == 422
        or "precisa sair em ou apos" in body
    ), f"esperado erro de validacao temporal, got {resp.status_code}: {body[:500]}"
