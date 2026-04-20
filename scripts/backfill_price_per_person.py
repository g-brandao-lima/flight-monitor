"""Backfill one-shot: divide precos inflados pelo numero de passageiros.

Contexto: Phase 16 (commit ea7cf5b, deploy 14:30 UTC 2026-04-20) passou a enviar
`adults=N` nas requests SerpAPI/fast-flights. Como essas APIs retornam preco TOTAL
da compra (per_person * N), os snapshots de grupos com passengers > 1 ficaram
com `price` inflado. Display no dashboard mostra "por pessoa" um valor que e total.

Este script corrige os snapshots afetados:
- Afetados: snapshots criados apos 2026-04-20 14:00 UTC (deploy completo as 14:30)
- De grupos com passengers > 1
- Divide price + price_min + price_first_quartile + price_median + price_third_quartile + price_max
  pelo numero de passageiros do grupo

Executar uma unica vez. Idempotencia: adiciona flag no snapshot? Nao, confiar em
cutoff de data. Rodar uma vez so (commit do fix ja evita novos snapshots errados).

Uso:
    DATABASE_URL=postgresql+psycopg://... python scripts/backfill_price_per_person.py --dry-run
    DATABASE_URL=postgresql+psycopg://... python scripts/backfill_price_per_person.py --apply
"""
import argparse
import datetime
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.database import SessionLocal  # noqa: E402
from app.models import FlightSnapshot, RouteGroup  # noqa: E402


CUTOFF = datetime.datetime(2026, 4, 20, 14, 0, 0)  # UTC; deploy Phase 16


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Aplica mudancas (sem isso, dry-run)")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        groups = (
            db.query(RouteGroup)
            .filter(RouteGroup.passengers > 1)
            .all()
        )
        print(f"Grupos com passengers > 1: {len(groups)}")

        total_updated = 0
        for g in groups:
            snaps = (
                db.query(FlightSnapshot)
                .filter(
                    FlightSnapshot.route_group_id == g.id,
                    FlightSnapshot.collected_at >= CUTOFF,
                )
                .all()
            )
            if not snaps:
                print(f"  Grupo {g.id} ({g.name}, pax={g.passengers}): 0 snapshots afetados")
                continue

            print(f"  Grupo {g.id} ({g.name}, pax={g.passengers}): {len(snaps)} snapshots afetados")
            pax = g.passengers
            for s in snaps:
                before = s.price
                s.price = s.price / pax
                if s.price_min is not None:
                    s.price_min = s.price_min / pax
                if s.price_first_quartile is not None:
                    s.price_first_quartile = s.price_first_quartile / pax
                if s.price_median is not None:
                    s.price_median = s.price_median / pax
                if s.price_third_quartile is not None:
                    s.price_third_quartile = s.price_third_quartile / pax
                if s.price_max is not None:
                    s.price_max = s.price_max / pax
                if args.apply:
                    db.add(s)
                total_updated += 1
                print(f"    snap {s.id}: {before:.2f} -> {s.price:.2f}")

        if args.apply:
            db.commit()
            print(f"\nOK. {total_updated} snapshots atualizados.")
        else:
            db.rollback()
            print(f"\nDRY-RUN. {total_updated} snapshots seriam atualizados. Rode com --apply para commitar.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
