import datetime
from datetime import timedelta

from app.models import FlightSnapshot, RouteGroup
from scripts.backtest_predictions import (
    HIT_THRESHOLD_PCT,
    evaluate_snapshot,
    format_report,
    run_backtest,
)


def _snap(
    group_id: int,
    price: float,
    collected_at: datetime.datetime,
    departure_date: datetime.date,
    origin: str = "GRU",
    destination: str = "LIS",
) -> FlightSnapshot:
    return FlightSnapshot(
        route_group_id=group_id,
        origin=origin,
        destination=destination,
        departure_date=departure_date,
        return_date=departure_date + timedelta(days=10),
        price=price,
        currency="BRL",
        airline="LA",
        collected_at=collected_at,
    )


def test_evaluate_snapshot_compre_hit_quando_preco_sobe():
    base = datetime.datetime(2026, 1, 1, 12, 0)
    snap = _snap(1, 900.0, base, base.date() + timedelta(days=60))
    past = [1000.0] * 20  # mediana 1000, preco 900 = -10%, janela 60d = COMPRE
    future = [1000.0] * 10  # preco real subiu 11%, COMPRE foi certo

    rec, verdict = evaluate_snapshot(snap, past, future)

    assert rec.action == "COMPRE"
    assert verdict == "hit"


def test_evaluate_snapshot_compre_miss_quando_preco_cai():
    base = datetime.datetime(2026, 1, 1, 12, 0)
    snap = _snap(1, 900.0, base, base.date() + timedelta(days=60))
    past = [1000.0] * 20
    future = [800.0] * 10  # preco caiu, COMPRE errou

    rec, verdict = evaluate_snapshot(snap, past, future)

    assert rec.action == "COMPRE"
    assert verdict == "miss"


def test_evaluate_snapshot_monitorar_e_neutro():
    base = datetime.datetime(2026, 1, 1, 12, 0)
    snap = _snap(1, 1000.0, base, base.date() + timedelta(days=60))
    past = [1000.0] * 20
    future = [1200.0] * 10

    rec, verdict = evaluate_snapshot(snap, past, future)

    assert rec.action == "MONITORAR"
    assert verdict == "neutro"


def test_run_backtest_agrega_por_acao(db):
    group = RouteGroup(
        name="Backtest group",
        origins=["GRU"],
        destinations=["LIS"],
        duration_days=10,
        travel_start=datetime.date.today() + timedelta(days=400),
        travel_end=datetime.date.today() + timedelta(days=410),
        is_active=True,
    )
    db.add(group)
    db.commit()
    db.refresh(group)

    now = datetime.datetime.utcnow()
    target_collected = now - timedelta(days=60)
    departure = target_collected.date() + timedelta(days=60)

    # Historico passado (anterior ao alvo) com preco alto
    for i in range(20):
        db.add(_snap(
            group.id,
            price=1000.0,
            collected_at=target_collected - timedelta(days=i + 1),
            departure_date=departure,
        ))

    # Snapshot alvo: preco baixo + janela otima -> COMPRE
    db.add(_snap(
        group.id,
        price=850.0,
        collected_at=target_collected,
        departure_date=departure,
    ))

    # Futuro (subiu): confirma hit
    for i in range(5):
        db.add(_snap(
            group.id,
            price=1000.0,
            collected_at=target_collected + timedelta(days=i + 1),
            departure_date=departure,
        ))
    db.commit()

    result = run_backtest(db)

    assert result["total"] >= 1
    compre_stats = result["by_action"].get("COMPRE", {})
    assert compre_stats.get("total", 0) >= 1
    assert compre_stats.get("hit", 0) >= 1


def test_format_report_inclui_cabecalho_e_classes():
    result = {
        "total": 10,
        "by_action": {
            "COMPRE": {"total": 4, "hit": 3, "miss": 1, "neutro": 0},
            "AGUARDE": {"total": 2, "hit": 1, "miss": 1, "neutro": 0},
            "MONITORAR": {"total": 4, "hit": 0, "miss": 0, "neutro": 4},
        },
    }

    report = format_report(result)

    assert "Phase 34 Backtest" in report
    assert "COMPRE" in report
    assert "AGUARDE" in report
    assert "MONITORAR" in report
    assert "10" in report


def test_hit_threshold_esta_em_5_pct():
    assert HIT_THRESHOLD_PCT == 5.0
