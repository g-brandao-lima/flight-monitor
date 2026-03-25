import datetime
from unittest.mock import patch, MagicMock

from app.models import RouteGroup, FlightSnapshot
from app.services.snapshot_service import is_duplicate_snapshot


def _create_route_group(db, **overrides):
    """Helper to create a RouteGroup in the test database."""
    defaults = {
        "name": "Test Group",
        "origins": ["GRU"],
        "destinations": ["GIG"],
        "duration_days": 7,
        "travel_start": datetime.date(2026, 5, 1),
        "travel_end": datetime.date(2026, 5, 31),
        "target_price": None,
        "is_active": True,
    }
    defaults.update(overrides)
    group = RouteGroup(**defaults)
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


def _create_snapshot(db, route_group_id, collected_at=None, **overrides):
    """Helper to create a FlightSnapshot in the test database."""
    defaults = {
        "route_group_id": route_group_id,
        "origin": "GRU",
        "destination": "GIG",
        "departure_date": datetime.date(2026, 5, 1),
        "return_date": datetime.date(2026, 5, 8),
        "price": 450.0,
        "currency": "BRL",
        "airline": "LA",
    }
    defaults.update(overrides)
    snapshot = FlightSnapshot(**defaults)
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)

    if collected_at is not None:
        db.execute(
            FlightSnapshot.__table__.update()
            .where(FlightSnapshot.id == snapshot.id)
            .values(collected_at=collected_at)
        )
        db.commit()

    return snapshot


class TestIsDuplicateSnapshot:
    """Testes para a funcao is_duplicate_snapshot."""

    def test_duplicate_detected_when_identical_snapshot_recent(self, db):
        """Test 1: Retorna True quando snapshot identico existe com collected_at < 1 hora."""
        group = _create_route_group(db)
        recent_time = datetime.datetime.utcnow() - datetime.timedelta(minutes=30)
        _create_snapshot(db, group.id, collected_at=recent_time)

        result = is_duplicate_snapshot(
            db,
            route_group_id=group.id,
            origin="GRU",
            destination="GIG",
            departure_date=datetime.date(2026, 5, 1),
            return_date=datetime.date(2026, 5, 8),
            price=450.0,
            airline="LA",
        )
        assert result is True

    def test_no_duplicate_when_no_snapshot_exists(self, db):
        """Test 2: Retorna False quando nenhum snapshot existe."""
        group = _create_route_group(db)

        result = is_duplicate_snapshot(
            db,
            route_group_id=group.id,
            origin="GRU",
            destination="GIG",
            departure_date=datetime.date(2026, 5, 1),
            return_date=datetime.date(2026, 5, 8),
            price=450.0,
            airline="LA",
        )
        assert result is False

    def test_no_duplicate_when_snapshot_older_than_1_hour(self, db):
        """Test 3: Retorna False quando snapshot identico existe mas collected_at > 1 hora."""
        group = _create_route_group(db)
        old_time = datetime.datetime.utcnow() - datetime.timedelta(hours=2)
        _create_snapshot(db, group.id, collected_at=old_time)

        result = is_duplicate_snapshot(
            db,
            route_group_id=group.id,
            origin="GRU",
            destination="GIG",
            departure_date=datetime.date(2026, 5, 1),
            return_date=datetime.date(2026, 5, 8),
            price=450.0,
            airline="LA",
        )
        assert result is False

    def test_no_duplicate_when_price_different(self, db):
        """Test 4: Retorna False quando preco e diferente (mesmo voo, preco mudou)."""
        group = _create_route_group(db)
        recent_time = datetime.datetime.utcnow() - datetime.timedelta(minutes=30)
        _create_snapshot(db, group.id, collected_at=recent_time, price=450.0)

        result = is_duplicate_snapshot(
            db,
            route_group_id=group.id,
            origin="GRU",
            destination="GIG",
            departure_date=datetime.date(2026, 5, 1),
            return_date=datetime.date(2026, 5, 8),
            price=500.0,
            airline="LA",
        )
        assert result is False

    def test_no_duplicate_when_airline_different(self, db):
        """Test 5: Retorna False quando airline e diferente."""
        group = _create_route_group(db)
        recent_time = datetime.datetime.utcnow() - datetime.timedelta(minutes=30)
        _create_snapshot(db, group.id, collected_at=recent_time, airline="LA")

        result = is_duplicate_snapshot(
            db,
            route_group_id=group.id,
            origin="GRU",
            destination="GIG",
            departure_date=datetime.date(2026, 5, 1),
            return_date=datetime.date(2026, 5, 8),
            price=450.0,
            airline="G3",
        )
        assert result is False


class TestProcessFlightDedup:
    """Testes para integracao de deduplicacao no _process_flight."""

    @patch("app.services.polling_service.detect_signals", return_value=[])
    @patch("app.services.polling_service.save_flight_snapshot")
    @patch("app.services.polling_service.is_duplicate_snapshot", return_value=True)
    def test_process_flight_skips_save_when_duplicate(
        self, mock_is_dup, mock_save, mock_detect, db
    ):
        """Test 6: _process_flight pula save quando duplicata detectada."""
        from app.services.polling_service import _process_flight

        group = _create_route_group(db)
        flight = {"price": 450, "airline": "LA"}

        _process_flight(
            db, group, "GRU", "GIG",
            datetime.date(2026, 5, 1), datetime.date(2026, 5, 8),
            flight, None,
        )

        mock_is_dup.assert_called_once()
        mock_save.assert_not_called()

    @patch("app.services.polling_service.detect_signals", return_value=[])
    @patch("app.services.polling_service.save_flight_snapshot")
    @patch("app.services.polling_service.is_duplicate_snapshot", return_value=False)
    def test_process_flight_saves_when_not_duplicate(
        self, mock_is_dup, mock_save, mock_detect, db
    ):
        """Test 7: _process_flight salva normalmente quando nao e duplicata."""
        from app.services.polling_service import _process_flight

        group = _create_route_group(db)
        flight = {"price": 450, "airline": "LA"}

        _process_flight(
            db, group, "GRU", "GIG",
            datetime.date(2026, 5, 1), datetime.date(2026, 5, 8),
            flight, None,
        )

        mock_is_dup.assert_called_once()
        mock_save.assert_called_once()
