import datetime
from datetime import date

from app.models import RouteGroup, FlightSnapshot, BookingClassSnapshot
from app.services.snapshot_service import save_flight_snapshot


def _create_route_group(db):
    """Helper: cria um RouteGroup auxiliar para FK."""
    rg = RouteGroup(
        name="Test Route",
        origins=["GRU"],
        destinations=["GIG"],
        duration_days=7,
        travel_start=date(2026, 5, 1),
        travel_end=date(2026, 5, 31),
        is_active=True,
    )
    db.add(rg)
    db.commit()
    db.refresh(rg)
    return rg


def test_flight_snapshot_persisted(db):
    """FlightSnapshot persiste no banco com todos os campos preenchidos."""
    rg = _create_route_group(db)

    snapshot = FlightSnapshot(
        route_group_id=rg.id,
        origin="GRU",
        destination="GIG",
        departure_date=date(2026, 5, 1),
        return_date=date(2026, 5, 8),
        price=450.0,
        currency="BRL",
        airline="LA",
        collected_at=datetime.datetime(2026, 5, 1, 12, 0, 0),
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)

    loaded = db.get(FlightSnapshot, snapshot.id)
    assert loaded is not None
    assert loaded.route_group_id == rg.id
    assert loaded.origin == "GRU"
    assert loaded.destination == "GIG"
    assert loaded.departure_date == date(2026, 5, 1)
    assert loaded.return_date == date(2026, 5, 8)
    assert loaded.price == 450.0
    assert loaded.currency == "BRL"
    assert loaded.airline == "LA"
    assert loaded.collected_at is not None


def test_snapshot_has_booking_classes(db):
    """FlightSnapshot carrega BookingClassSnapshot via relationship."""
    rg = _create_route_group(db)

    snapshot = FlightSnapshot(
        route_group_id=rg.id,
        origin="GRU",
        destination="GIG",
        departure_date=date(2026, 5, 1),
        return_date=date(2026, 5, 8),
        price=450.0,
        currency="BRL",
        airline="LA",
        booking_classes=[
            BookingClassSnapshot(class_code="Y", seats_available=9, segment_direction="OUTBOUND"),
            BookingClassSnapshot(class_code="B", seats_available=4, segment_direction="OUTBOUND"),
            BookingClassSnapshot(class_code="M", seats_available=3, segment_direction="OUTBOUND"),
        ],
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)

    assert len(snapshot.booking_classes) == 3
    codes = {bc.class_code for bc in snapshot.booking_classes}
    assert codes == {"Y", "B", "M"}


def test_snapshot_with_price_metrics(db):
    """FlightSnapshot persiste campos nullable de price metrics."""
    rg = _create_route_group(db)

    snapshot = FlightSnapshot(
        route_group_id=rg.id,
        origin="GRU",
        destination="GIG",
        departure_date=date(2026, 5, 1),
        return_date=date(2026, 5, 8),
        price=450.0,
        currency="BRL",
        airline="LA",
        price_min=150.0,
        price_first_quartile=250.0,
        price_median=400.0,
        price_third_quartile=600.0,
        price_max=900.0,
        price_classification="LOW",
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)

    loaded = db.get(FlightSnapshot, snapshot.id)
    assert loaded.price_min == 150.0
    assert loaded.price_first_quartile == 250.0
    assert loaded.price_median == 400.0
    assert loaded.price_third_quartile == 600.0
    assert loaded.price_max == 900.0
    assert loaded.price_classification == "LOW"


def test_snapshot_price_metrics_nullable(db):
    """FlightSnapshot persiste sem price metrics (todos None)."""
    rg = _create_route_group(db)

    snapshot = FlightSnapshot(
        route_group_id=rg.id,
        origin="GRU",
        destination="GIG",
        departure_date=date(2026, 5, 1),
        return_date=date(2026, 5, 8),
        price=450.0,
        currency="BRL",
        airline="LA",
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)

    loaded = db.get(FlightSnapshot, snapshot.id)
    assert loaded.price_min is None
    assert loaded.price_first_quartile is None
    assert loaded.price_median is None
    assert loaded.price_third_quartile is None
    assert loaded.price_max is None
    assert loaded.price_classification is None


def test_save_flight_snapshot_function(db):
    """save_flight_snapshot cria FlightSnapshot + BookingClassSnapshot no banco."""
    rg = _create_route_group(db)

    snapshot_data = {
        "route_group_id": rg.id,
        "origin": "GRU",
        "destination": "GIG",
        "departure_date": date(2026, 5, 1),
        "return_date": date(2026, 5, 8),
        "price": 450.0,
        "currency": "BRL",
        "airline": "LA",
        "price_min": 150.0,
        "price_first_quartile": 250.0,
        "price_median": 400.0,
        "price_third_quartile": 600.0,
        "price_max": 900.0,
        "price_classification": "LOW",
        "booking_classes": [
            {"class_code": "Y", "seats_available": 9, "segment_direction": "OUTBOUND"},
            {"class_code": "B", "seats_available": 4, "segment_direction": "OUTBOUND"},
            {"class_code": "M", "seats_available": 3, "segment_direction": "OUTBOUND"},
        ],
    }

    result = save_flight_snapshot(db, snapshot_data)

    assert result.id is not None
    assert result.origin == "GRU"
    assert result.price == 450.0
    assert len(result.booking_classes) == 3

    from_db = db.get(FlightSnapshot, result.id)
    assert from_db is not None
    assert len(from_db.booking_classes) == 3


def test_config_has_gmail_fields():
    """Settings tem gmail_* e NAO tem telegram_*."""
    from app.config import Settings

    fields = Settings.model_fields
    assert "gmail_sender" in fields
    assert "gmail_app_password" in fields
    assert "gmail_recipient" in fields
    assert "telegram_bot_token" not in fields
    assert "telegram_chat_id" not in fields
