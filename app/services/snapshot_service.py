import datetime

from sqlalchemy.orm import Session
from app.models import FlightSnapshot, BookingClassSnapshot


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
    """Verifica se ja existe snapshot identico coletado na ultima hora."""
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
    """Persiste um FlightSnapshot com seus BookingClassSnapshots."""
    booking_classes_data = data.pop("booking_classes", [])

    snapshot = FlightSnapshot(**data)
    for bc_data in booking_classes_data:
        snapshot.booking_classes.append(BookingClassSnapshot(**bc_data))

    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot
