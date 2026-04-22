from datetime import date, timedelta

import pytest

from app.services.price_prediction_service import (
    HIGH_PRICE_PCT,
    LOW_PRICE_PCT,
    MIN_SNAPSHOTS,
    OPTIMAL_WINDOW_MAX,
    OPTIMAL_WINDOW_MIN,
    Recommendation,
    predict_action,
)


def _dep_in(days: int) -> date:
    return date.today() + timedelta(days=days)


def test_compre_preco_baixo_janela_otima():
    dep = _dep_in(60)
    rec = predict_action(
        current_price=900.0,
        median_90d=1000.0,
        stddev_90d=50.0,
        days_to_departure=60,
        snapshot_count=40,
        departure_date=dep,
    )
    assert rec.action == "COMPRE"
    assert "abaixo" in rec.reason.lower()
    assert rec.deadline is not None


def test_compre_ultima_chance_perto_do_voo():
    dep = _dep_in(20)
    rec = predict_action(
        current_price=1000.0,
        median_90d=1000.0,
        stddev_90d=50.0,
        days_to_departure=20,
        snapshot_count=40,
        departure_date=dep,
    )
    assert rec.action == "COMPRE"
    assert "ltima" in rec.reason.lower() or "chance" in rec.reason.lower()


def test_aguarde_janela_ainda_nao_chegou():
    dep = _dep_in(120)
    rec = predict_action(
        current_price=1000.0,
        median_90d=1000.0,
        stddev_90d=50.0,
        days_to_departure=120,
        snapshot_count=40,
        departure_date=dep,
    )
    assert rec.action == "AGUARDE"
    assert rec.deadline == dep - timedelta(days=OPTIMAL_WINDOW_MAX)


def test_monitorar_preco_caro():
    dep = _dep_in(60)
    rec = predict_action(
        current_price=1200.0,
        median_90d=1000.0,
        stddev_90d=50.0,
        days_to_departure=60,
        snapshot_count=40,
        departure_date=dep,
    )
    assert rec.action == "MONITORAR"
    assert "acima" in rec.reason.lower()


def test_monitorar_preco_normal():
    dep = _dep_in(60)
    rec = predict_action(
        current_price=1000.0,
        median_90d=1000.0,
        stddev_90d=50.0,
        days_to_departure=60,
        snapshot_count=40,
        departure_date=dep,
    )
    assert rec.action == "MONITORAR"
    assert rec.deadline is None


def test_monitorar_dados_insuficientes():
    dep = _dep_in(60)
    rec = predict_action(
        current_price=900.0,
        median_90d=1000.0,
        stddev_90d=50.0,
        days_to_departure=60,
        snapshot_count=5,
        departure_date=dep,
    )
    assert rec.action == "MONITORAR"
    assert "hist" in rec.reason.lower() or "leituras" in rec.reason.lower()


def test_confidence_baixa_com_pouco_historico():
    dep = _dep_in(60)
    rec = predict_action(
        current_price=900.0,
        median_90d=1000.0,
        stddev_90d=50.0,
        days_to_departure=60,
        snapshot_count=MIN_SNAPSHOTS,
        departure_date=dep,
    )
    assert 0 < rec.confidence < 0.5


def test_confidence_alta_com_historico_robusto():
    dep = _dep_in(60)
    rec = predict_action(
        current_price=900.0,
        median_90d=1000.0,
        stddev_90d=30.0,
        days_to_departure=60,
        snapshot_count=120,
        departure_date=dep,
    )
    assert rec.confidence >= 0.8


def test_deadline_compre_calculado_corretamente():
    dep = _dep_in(60)
    rec = predict_action(
        current_price=850.0,
        median_90d=1000.0,
        stddev_90d=50.0,
        days_to_departure=60,
        snapshot_count=40,
        departure_date=dep,
    )
    assert rec.action == "COMPRE"
    assert rec.deadline == dep - timedelta(days=OPTIMAL_WINDOW_MIN)


def test_deadline_aguarde_calculado_corretamente():
    dep = _dep_in(150)
    rec = predict_action(
        current_price=1000.0,
        median_90d=1000.0,
        stddev_90d=50.0,
        days_to_departure=150,
        snapshot_count=40,
        departure_date=dep,
    )
    assert rec.action == "AGUARDE"
    assert rec.deadline == dep - timedelta(days=OPTIMAL_WINDOW_MAX)


def test_volatilidade_alta_reduz_confidence():
    dep = _dep_in(60)
    rec_estavel = predict_action(
        current_price=900.0,
        median_90d=1000.0,
        stddev_90d=20.0,
        days_to_departure=60,
        snapshot_count=60,
        departure_date=dep,
    )
    rec_volatil = predict_action(
        current_price=900.0,
        median_90d=1000.0,
        stddev_90d=400.0,
        days_to_departure=60,
        snapshot_count=60,
        departure_date=dep,
    )
    assert rec_volatil.confidence < rec_estavel.confidence


def test_recommendation_e_frozen_dataclass():
    dep = _dep_in(60)
    rec = predict_action(
        current_price=900.0,
        median_90d=1000.0,
        stddev_90d=50.0,
        days_to_departure=60,
        snapshot_count=40,
        departure_date=dep,
    )
    assert isinstance(rec, Recommendation)
    with pytest.raises(Exception):
        rec.action = "OUTRO"  # type: ignore[misc]


def test_median_none_retorna_monitorar_sem_dados():
    dep = _dep_in(60)
    rec = predict_action(
        current_price=900.0,
        median_90d=None,
        stddev_90d=None,
        days_to_departure=60,
        snapshot_count=40,
        departure_date=dep,
    )
    assert rec.action == "MONITORAR"
