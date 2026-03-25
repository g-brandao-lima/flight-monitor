from sqlalchemy.orm import Session
from app.models import FlightSnapshot, BookingClassSnapshot


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
