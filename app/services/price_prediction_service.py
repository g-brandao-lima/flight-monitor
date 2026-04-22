"""Engine deterministica de recomendacao COMPRE/AGUARDE/MONITORAR (Phase 34).

Sem ML. Regras baseadas em janela temporal otima + delta vs mediana 90d +
volatilidade. Pura e sem I/O pra ser trivialmente testavel e reutilizavel no
dashboard, email e backtest.
"""

import datetime
import statistics
from dataclasses import dataclass
from datetime import date, timedelta
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.models import FlightSnapshot, RouteGroup

Action = Literal["COMPRE", "AGUARDE", "MONITORAR"]

OPTIMAL_WINDOW_MIN = 35
OPTIMAL_WINDOW_MAX = 95
LOW_PRICE_PCT = -10.0
HIGH_PRICE_PCT = 10.0
MIN_SNAPSHOTS = 15

_CONFIDENCE_SATURATION = 60


@dataclass(frozen=True)
class Recommendation:
    action: Action
    reason: str
    confidence: float
    deadline: date | None


def _compute_confidence(snapshot_count: int, median: float | None, stddev: float | None) -> float:
    base = min(snapshot_count / _CONFIDENCE_SATURATION, 1.0)
    if not median or not stddev or median <= 0:
        return round(base, 2)
    volatility = min(stddev / median, 0.5)
    return round(max(0.0, base * (1.0 - volatility)), 2)


def predict_action(
    current_price: float,
    median_90d: float | None,
    stddev_90d: float | None,
    days_to_departure: int,
    snapshot_count: int,
    departure_date: date,
) -> Recommendation:
    """Classifica o momento atual de compra pra uma rota.

    Ver spec completa em .planning/phases/34-price-prediction/34-SPEC.md secao 5.
    """
    confidence = _compute_confidence(snapshot_count, median_90d, stddev_90d)

    if snapshot_count < MIN_SNAPSHOTS or median_90d is None or median_90d <= 0:
        return Recommendation(
            action="MONITORAR",
            reason="Ainda reunindo historico (menos de 15 leituras).",
            confidence=confidence,
            deadline=None,
        )

    low_threshold = median_90d * (1 + LOW_PRICE_PCT / 100)
    high_threshold = median_90d * (1 + HIGH_PRICE_PCT / 100)
    in_optimal_window = OPTIMAL_WINDOW_MIN <= days_to_departure <= OPTIMAL_WINDOW_MAX

    if current_price <= low_threshold and in_optimal_window:
        pct_below = round((median_90d - current_price) / median_90d * 100)
        return Recommendation(
            action="COMPRE",
            reason=f"Preco {pct_below}% abaixo da media e dentro da janela otima.",
            confidence=confidence,
            deadline=departure_date - timedelta(days=OPTIMAL_WINDOW_MIN),
        )

    if days_to_departure > OPTIMAL_WINDOW_MAX:
        days_until_window = days_to_departure - OPTIMAL_WINDOW_MAX
        return Recommendation(
            action="AGUARDE",
            reason=f"Janela otima comeca em {days_until_window} dias. Sem urgencia ainda.",
            confidence=confidence,
            deadline=departure_date - timedelta(days=OPTIMAL_WINDOW_MAX),
        )

    if days_to_departure < OPTIMAL_WINDOW_MIN and current_price <= median_90d:
        return Recommendation(
            action="COMPRE",
            reason="Ultima janela antes da partida. Preco ainda razoavel.",
            confidence=confidence,
            deadline=departure_date,
        )

    if current_price >= high_threshold:
        pct_above = round((current_price - median_90d) / median_90d * 100)
        return Recommendation(
            action="MONITORAR",
            reason=f"Preco {pct_above}% acima da media. Aguardando queda.",
            confidence=confidence,
            deadline=None,
        )

    return Recommendation(
        action="MONITORAR",
        reason="Preco em linha com o historico. Sem mudanca significativa.",
        confidence=confidence,
        deadline=None,
    )


def build_recommendation_for_group(
    db: "Session",
    group: "RouteGroup",
    cheapest_snapshot: "FlightSnapshot | None",
) -> Recommendation | None:
    """Calcula mediana/desvio 90d a partir do banco e chama predict_action.

    Retorna None se nao houver cheapest_snapshot ou departure_date.
    """
    if cheapest_snapshot is None or cheapest_snapshot.departure_date is None:
        return None

    from app.models import FlightSnapshot

    cutoff = datetime.datetime.utcnow() - timedelta(days=90)
    prices = [
        row[0]
        for row in db.query(FlightSnapshot.price)
        .filter(
            FlightSnapshot.route_group_id == group.id,
            FlightSnapshot.origin.in_(group.origins),
            FlightSnapshot.destination.in_(group.destinations),
            FlightSnapshot.collected_at >= cutoff,
            FlightSnapshot.price > 0,
        )
        .all()
        if row[0] is not None
    ]

    median = statistics.median(prices) if prices else None
    stddev = statistics.pstdev(prices) if len(prices) >= 2 else None
    days_to_departure = (cheapest_snapshot.departure_date - date.today()).days

    return predict_action(
        current_price=cheapest_snapshot.price,
        median_90d=median,
        stddev_90d=stddev,
        days_to_departure=days_to_departure,
        snapshot_count=len(prices),
        departure_date=cheapest_snapshot.departure_date,
    )
