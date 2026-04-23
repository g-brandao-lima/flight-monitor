import datetime

from sqlalchemy.orm import Session
from app.models import FlightSnapshot


def get_historical_price_context(
    db: Session,
    origin: str,
    destination: str,
    days: int = 90,
    min_samples: int = 10,
) -> dict | None:
    """Estatisticas historicas de preco da rota nos ultimos `days` dias.

    Retorna dict com `avg`, `min`, `max`, `count` ou None se samples < min_samples.
    Usado para enriquecer alertas com contexto ("X% abaixo da media dos ultimos 90 dias").
    """
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=days)
    rows = (
        db.query(FlightSnapshot.price)
        .filter(
            FlightSnapshot.origin == origin,
            FlightSnapshot.destination == destination,
            FlightSnapshot.collected_at >= cutoff,
        )
        .all()
    )
    prices = [r[0] for r in rows if r[0] is not None]
    if len(prices) < min_samples:
        return None
    return {
        "avg": sum(prices) / len(prices),
        "min": min(prices),
        "max": max(prices),
        "count": len(prices),
        "days": days,
    }


def get_historical_price_range(
    db: Session,
    origin: str,
    destination: str,
    min_samples: int = 5,
    n_snapshots: int = 30,
) -> list[float] | None:
    """Calcula o intervalo tipico de precos [p25, p75] com base no historico salvo.

    Retorna None se houver menos de min_samples snapshots para a rota.
    """
    rows = (
        db.query(FlightSnapshot.price)
        .filter(
            FlightSnapshot.origin == origin,
            FlightSnapshot.destination == destination,
        )
        .order_by(FlightSnapshot.collected_at.desc())
        .limit(n_snapshots)
        .all()
    )
    values = sorted(row[0] for row in rows)
    if len(values) < min_samples:
        return None

    p25_idx = int(len(values) * 0.25)
    p75_idx = min(int(len(values) * 0.75), len(values) - 1)
    return [values[p25_idx], values[p75_idx]]


def is_duplicate_snapshot(
    db: Session,
    route_group_id: int,
    origin: str,
    destination: str,
    departure_date: datetime.date,
    return_date: datetime.date,
    price: float,
    airline: str,
) -> bool:
    """Verifica se ja existe snapshot identico coletado na ultima hora.

    Pitfall 2 (Phase 36): snapshots multi (airline=MULTI) usam janela de 6h
    e dispensam match de origin/destination direto (cadeia pode variar),
    confiando em (route_group_id, total, departure_date, return_date) para
    evitar falsos positivos entre combinacoes diferentes.
    """
    if airline == "MULTI":
        cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=6)
        existing = (
            db.query(FlightSnapshot)
            .filter(
                FlightSnapshot.route_group_id == route_group_id,
                FlightSnapshot.airline == "MULTI",
                FlightSnapshot.price == price,
                FlightSnapshot.departure_date == departure_date,
                FlightSnapshot.return_date == return_date,
                FlightSnapshot.collected_at >= cutoff,
            )
            .first()
        )
        return existing is not None

    cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=1)
    existing = (
        db.query(FlightSnapshot)
        .filter(
            FlightSnapshot.route_group_id == route_group_id,
            FlightSnapshot.origin == origin,
            FlightSnapshot.destination == destination,
            FlightSnapshot.departure_date == departure_date,
            FlightSnapshot.return_date == return_date,
            FlightSnapshot.price == price,
            FlightSnapshot.airline == airline,
            FlightSnapshot.collected_at >= cutoff,
        )
        .first()
    )
    return existing is not None


def save_flight_snapshot(db: Session, data: dict) -> FlightSnapshot:
    """Persiste um FlightSnapshot."""
    data.pop("booking_classes", None)  # compat: argumento legado ignorado
    snapshot = FlightSnapshot(**data)
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot
