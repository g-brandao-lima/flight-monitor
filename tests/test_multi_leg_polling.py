"""Testes RED de branch multi no polling (MULTI-04).

Sinal PRECO ABAIXO DO HISTORICO opera sobre total_price de snapshots multi.
"""
from datetime import date, datetime, timedelta

import pytest


def test_signal_on_total_price(db, multi_leg_group_factory):
    """MULTI-04: detect_signals dispara PRECO ABAIXO DO HISTORICO sobre total."""
    try:
        from app.services import signal_service
    except ImportError:
        pytest.fail("signal_service nao disponivel")

    from app.models import FlightSnapshot

    group = multi_leg_group_factory(num_legs=2)

    # Cria 10 snapshots historicos com precos 5000-6000
    base_time = datetime.utcnow() - timedelta(days=30)
    for i in range(10):
        snap = FlightSnapshot(
            route_group_id=group.id,
            origin="GRU",
            destination="FCO",
            departure_date=date(2026, 6, 1),
            return_date=date(2026, 6, 20),
            price=5000.0 + i * 100,
            currency="BRL",
            airline="MULTI",
            source="multi_leg",
            details={"total_price": 5000.0 + i * 100, "legs": []},
            collected_at=base_time + timedelta(days=i),
        )
        db.add(snap)
    db.commit()

    # Novo snapshot bem abaixo do historico
    new_snap = FlightSnapshot(
        route_group_id=group.id,
        origin="GRU",
        destination="FCO",
        departure_date=date(2026, 6, 1),
        return_date=date(2026, 6, 20),
        price=4000.0,
        currency="BRL",
        airline="MULTI",
        source="multi_leg",
        details={"total_price": 4000.0, "legs": []},
    )
    db.add(new_snap)
    db.commit()
    db.refresh(new_snap)

    # Act
    signals = signal_service.detect_signals(db, new_snap)

    # Assert: algum sinal de preco baixo foi disparado
    assert signals, "esperado pelo menos 1 sinal sobre total_price multi"
    types = {s.signal_type if hasattr(s, "signal_type") else s.get("signal_type") for s in signals}
    assert any("PRECO" in str(t) or "HISTORICO" in str(t) for t in types), (
        f"esperado sinal PRECO ABAIXO DO HISTORICO, got {types}"
    )
