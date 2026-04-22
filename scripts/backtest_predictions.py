"""Backtest retrospectivo da engine de recomendacao (Phase 34).

Pra cada FlightSnapshot entre 30 e 180 dias atras:
  1. Reconstroi a "historia disponivel naquele momento" (snapshots anteriores)
  2. Chama predict_action com esses dados
  3. Compara com o preco real 30 dias depois
     - COMPRE: acerto se preco subiu >=5% nos 30 dias seguintes
     - AGUARDE: acerto se preco caiu >=5% dentro do deadline
     - MONITORAR: neutro

Uso:
    DATABASE_URL=postgresql://... python scripts/backtest_predictions.py
"""
import datetime
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.database import SessionLocal  # noqa: E402
from app.models import FlightSnapshot  # noqa: E402
from app.services.price_prediction_service import (  # noqa: E402
    Recommendation,
    predict_action,
)

WINDOW_START_DAYS = 30
WINDOW_END_DAYS = 180
FUTURE_WINDOW_DAYS = 30
HIT_THRESHOLD_PCT = 5.0


def evaluate_snapshot(
    snapshot: FlightSnapshot,
    past_prices: list[float],
    future_prices: list[float],
) -> tuple[Recommendation, str]:
    """Retorna (recomendacao, classificacao) pra um snapshot historico.

    classificacao: "hit", "miss" ou "neutro".
    """
    median = statistics.median(past_prices) if past_prices else None
    stddev = statistics.pstdev(past_prices) if len(past_prices) >= 2 else None
    days_to_departure = (snapshot.departure_date - snapshot.collected_at.date()).days

    rec = predict_action(
        current_price=snapshot.price,
        median_90d=median,
        stddev_90d=stddev,
        days_to_departure=days_to_departure,
        snapshot_count=len(past_prices),
        departure_date=snapshot.departure_date,
    )

    if not future_prices:
        return rec, "neutro"

    future_median = statistics.median(future_prices)
    delta_pct = (future_median - snapshot.price) / snapshot.price * 100

    if rec.action == "COMPRE":
        verdict = "hit" if delta_pct >= HIT_THRESHOLD_PCT else "miss"
    elif rec.action == "AGUARDE":
        verdict = "hit" if delta_pct <= -HIT_THRESHOLD_PCT else "miss"
    else:
        verdict = "neutro"

    return rec, verdict


def run_backtest(db) -> dict:
    now = datetime.datetime.utcnow()
    start_cutoff = now - datetime.timedelta(days=WINDOW_END_DAYS)
    end_cutoff = now - datetime.timedelta(days=WINDOW_START_DAYS)

    target_snaps = (
        db.query(FlightSnapshot)
        .filter(
            FlightSnapshot.collected_at >= start_cutoff,
            FlightSnapshot.collected_at <= end_cutoff,
            FlightSnapshot.price > 0,
        )
        .all()
    )

    stats = defaultdict(lambda: {"total": 0, "hit": 0, "miss": 0, "neutro": 0})

    for snap in target_snaps:
        past = [
            row[0]
            for row in db.query(FlightSnapshot.price)
            .filter(
                FlightSnapshot.origin == snap.origin,
                FlightSnapshot.destination == snap.destination,
                FlightSnapshot.collected_at < snap.collected_at,
                FlightSnapshot.collected_at >= snap.collected_at - datetime.timedelta(days=90),
                FlightSnapshot.price > 0,
            )
            .all()
        ]
        future = [
            row[0]
            for row in db.query(FlightSnapshot.price)
            .filter(
                FlightSnapshot.origin == snap.origin,
                FlightSnapshot.destination == snap.destination,
                FlightSnapshot.collected_at > snap.collected_at,
                FlightSnapshot.collected_at <= snap.collected_at
                + datetime.timedelta(days=FUTURE_WINDOW_DAYS),
                FlightSnapshot.price > 0,
            )
            .all()
        ]

        rec, verdict = evaluate_snapshot(snap, past, future)
        stats[rec.action]["total"] += 1
        stats[rec.action][verdict] += 1

    return {
        "total": len(target_snaps),
        "by_action": dict(stats),
    }


def format_report(result: dict) -> str:
    lines = []
    today = datetime.date.today().isoformat()
    lines.append(f"Phase 34 Backtest - {today}")
    lines.append(f"Periodo analisado: {WINDOW_START_DAYS}-{WINDOW_END_DAYS} dias")
    lines.append(f"Total snapshots avaliados: {result['total']}")
    lines.append("")

    for action in ("COMPRE", "AGUARDE", "MONITORAR"):
        stats = result["by_action"].get(action, {"total": 0, "hit": 0, "miss": 0, "neutro": 0})
        total = stats["total"]
        if action == "MONITORAR":
            lines.append(f"MONITORAR:  {total:>5} casos  | neutro (n/a)")
            continue
        hits = stats["hit"]
        misses = stats["miss"]
        evaluated = hits + misses
        if evaluated == 0:
            lines.append(f"{action}:     {total:>5} casos  | sem janela futura p/ avaliar")
            continue
        rate = hits / evaluated * 100
        flag = "ok" if rate >= 60 else "abaixo da meta 60%"
        lines.append(
            f"{action:<10} {total:>5} casos  | {hits} acertos ({rate:.1f}%) {flag}"
        )

    return "\n".join(lines)


def main() -> int:
    db = SessionLocal()
    try:
        result = run_backtest(db)
    finally:
        db.close()
    print(format_report(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
