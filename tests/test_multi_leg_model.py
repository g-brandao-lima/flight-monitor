"""Testes de model e validacao temporal (MULTI-01, MULTI-02).

Phase 36 — Wave 0 RED tests. Cobrem:
- RouteGroupLeg cascade delete
- Unique constraint (route_group_id, order)
- Validacao temporal Pydantic (chain, min/max legs, stay)
- FlightSnapshot.details JSON storage
"""
from datetime import date, timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import FlightSnapshot, RouteGroup, RouteGroupLeg
from app.schemas import LegCreate, RouteGroupMultiCreate


def test_leg_cascade_delete(db, multi_leg_group_factory):
    # Arrange
    group = multi_leg_group_factory(num_legs=3)
    group_id = group.id
    assert db.query(RouteGroupLeg).filter_by(route_group_id=group_id).count() == 3

    # Act
    db.delete(group)
    db.commit()

    # Assert
    assert db.query(RouteGroupLeg).filter_by(route_group_id=group_id).count() == 0


def test_unique_order_constraint(db, multi_leg_group_factory):
    # Arrange
    group = multi_leg_group_factory(num_legs=2)

    # Act + Assert
    duplicate = RouteGroupLeg(
        route_group_id=group.id,
        order=1,  # ja existe
        origin="AAA",
        destination="BBB",
        window_start=date(2026, 7, 1),
        window_end=date(2026, 7, 10),
        min_stay_days=1,
    )
    db.add(duplicate)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_chain_validation_rejects_overlap():
    # Arrange: leg2 sai antes do window_end de leg1 + min_stay
    legs = [
        LegCreate(
            order=1,
            origin="GRU",
            destination="FCO",
            window_start=date(2026, 6, 1),
            window_end=date(2026, 6, 10),
            min_stay_days=5,
        ),
        LegCreate(
            order=2,
            origin="FCO",
            destination="MAD",
            window_start=date(2026, 6, 12),  # invalido: precisa ser >= 15/06
            window_end=date(2026, 6, 20),
            min_stay_days=1,
        ),
    ]

    # Act + Assert
    with pytest.raises(ValueError) as exc_info:
        RouteGroupMultiCreate(name="Invalido", legs=legs)
    assert "precisa sair em ou apos" in str(exc_info.value)


def test_min_max_legs():
    # Arrange leg valido reutilizavel
    def _leg(order: int, offset_days: int) -> LegCreate:
        return LegCreate(
            order=order,
            origin="GRU",
            destination="FCO",
            window_start=date(2026, 6, 1) + timedelta(days=offset_days),
            window_end=date(2026, 6, 8) + timedelta(days=offset_days),
            min_stay_days=1,
        )

    # 1 leg -> erro
    with pytest.raises(ValueError) as exc_info:
        RouteGroupMultiCreate(name="x", legs=[_leg(1, 0)])
    assert "entre 2 e 5 trechos" in str(exc_info.value)

    # 6 legs -> erro
    with pytest.raises(ValueError) as exc_info:
        RouteGroupMultiCreate(name="x", legs=[_leg(i + 1, i * 10) for i in range(6)])
    assert "entre 2 e 5 trechos" in str(exc_info.value)

    # 2 legs validos -> OK
    model = RouteGroupMultiCreate(name="x", legs=[_leg(1, 0), _leg(2, 20)])
    assert len(model.legs) == 2


def test_flight_snapshot_details_json(db, multi_leg_group_factory):
    # Arrange
    group = multi_leg_group_factory(num_legs=2)

    # Act
    snapshot = FlightSnapshot(
        route_group_id=group.id,
        origin="GRU",
        destination="FCO",
        departure_date=date(2026, 6, 1),
        return_date=date(2026, 7, 1),
        price=5000.0,
        currency="BRL",
        airline="MULTI",
        details={"total_price": 5000, "legs": [{"order": 1}]},
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)

    # Assert
    assert snapshot.details["total_price"] == 5000
