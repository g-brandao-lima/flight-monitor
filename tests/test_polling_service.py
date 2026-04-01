import datetime
from unittest.mock import patch, MagicMock, call

from app.models import RouteGroup


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MOCK_FLIGHTS = [
    {
        "price": 450,
        "airline": "LATAM",
        "flights": [],
        "type": "Round trip",
    }
]

MOCK_INSIGHTS = {
    "lowest_price": 350,
    "typical_price_range": [400, 700],
    "price_history": [[1700000000, 500], [1700100000, 480]],
}

# fast-flights source: sem insights
MOCK_SEARCH_FF = (MOCK_FLIGHTS, None, "fast_flights")
# serpapi source: com insights
MOCK_SEARCH_SERPAPI = (MOCK_FLIGHTS, MOCK_INSIGHTS, "serpapi")


def _create_route_group(db, **overrides):
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


# ---------------------------------------------------------------------------
# TestPollingCycleProcessing
# ---------------------------------------------------------------------------


class TestPollingCycleProcessing:

    @patch("app.services.polling_service.save_flight_snapshot")
    @patch("app.services.polling_service.search_flights")
    def test_polling_cycle_processes_active_groups(self, mock_search, mock_save, db):
        from app.services.polling_service import run_polling_cycle

        _create_route_group(db, name="Group A")
        _create_route_group(db, name="Group B")

        mock_search.return_value = MOCK_SEARCH_FF

        with patch("app.services.polling_service.SessionLocal", return_value=db):
            run_polling_cycle()

        assert mock_save.call_count >= 2

    @patch("app.services.polling_service.save_flight_snapshot")
    @patch("app.services.polling_service.search_flights")
    def test_polling_cycle_skips_inactive_groups(self, mock_search, mock_save, db):
        from app.services.polling_service import run_polling_cycle

        _create_route_group(db, name="Active", is_active=True)
        _create_route_group(db, name="Inactive", is_active=False)

        mock_search.return_value = MOCK_SEARCH_FF

        with patch("app.services.polling_service.SessionLocal", return_value=db):
            run_polling_cycle()

        assert mock_save.call_count >= 1

    @patch("app.services.polling_service.save_flight_snapshot")
    @patch("app.services.polling_service.search_flights")
    def test_polling_cycle_continues_after_group_failure(self, mock_search, mock_save, db):
        from app.services.polling_service import run_polling_cycle

        _create_route_group(db, name="Failing Group")
        _create_route_group(db, name="Working Group")

        call_count = {"n": 0}

        def side_effect(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] <= 1:
                raise Exception("API Error for first group")
            return MOCK_SEARCH_FF

        mock_search.side_effect = side_effect

        with patch("app.services.polling_service.SessionLocal", return_value=db):
            run_polling_cycle()

        assert mock_save.call_count >= 1


# ---------------------------------------------------------------------------
# TestPollingUnifiedCall
# ---------------------------------------------------------------------------


class TestPollingUnifiedCall:

    @patch("app.services.polling_service.save_flight_snapshot")
    @patch("app.services.polling_service.search_flights")
    def test_single_api_call_per_combination(self, mock_search, mock_save, db):
        """Cada combinacao origem x destino x data usa exatamente 1 chamada."""
        from app.services.polling_service import run_polling_cycle

        _create_route_group(
            db,
            name="Single Call Test",
            origins=["GRU"],
            destinations=["GIG"],
            travel_start=datetime.date(2026, 5, 1),
            travel_end=datetime.date(2026, 5, 8),
            duration_days=7,
        )

        mock_search.return_value = MOCK_SEARCH_FF

        with patch("app.services.polling_service.SessionLocal", return_value=db):
            run_polling_cycle()

        assert mock_search.call_count == 1


# ---------------------------------------------------------------------------
# TestPollGroupCombinations
# ---------------------------------------------------------------------------


class TestPollGroupCombinations:

    @patch("app.services.polling_service.save_flight_snapshot")
    @patch("app.services.polling_service.search_flights")
    def test_poll_group_generates_origin_dest_combinations(self, mock_search, mock_save, db):
        from app.services.polling_service import run_polling_cycle

        _create_route_group(
            db,
            name="Multi Origin",
            origins=["GRU", "VCP"],
            destinations=["GIG"],
            travel_start=datetime.date(2026, 5, 1),
            travel_end=datetime.date(2026, 5, 8),
            duration_days=7,
        )

        mock_search.return_value = MOCK_SEARCH_FF

        with patch("app.services.polling_service.SessionLocal", return_value=db):
            run_polling_cycle()

        called_origins = [c.kwargs.get("origin") for c in mock_search.call_args_list]
        assert "GRU" in called_origins
        assert "VCP" in called_origins

    @patch("app.services.polling_service.save_flight_snapshot")
    @patch("app.services.polling_service.search_flights")
    def test_poll_group_generates_date_combinations_every_7_days(self, mock_search, mock_save, db):
        from app.services.polling_service import run_polling_cycle

        _create_route_group(
            db,
            name="Date Combos",
            origins=["GRU"],
            destinations=["GIG"],
            travel_start=datetime.date(2026, 5, 1),
            travel_end=datetime.date(2026, 5, 31),
            duration_days=7,
        )

        mock_search.return_value = MOCK_SEARCH_FF

        with patch("app.services.polling_service.SessionLocal", return_value=db):
            run_polling_cycle()

        # May 1,8,15,22 → 4 pares
        assert mock_search.call_count == 4

        dep_dates = [c.kwargs.get("departure_date") for c in mock_search.call_args_list]
        assert "2026-05-01" in dep_dates
        assert "2026-05-08" in dep_dates
        assert "2026-05-15" in dep_dates
        assert "2026-05-22" in dep_dates


# ---------------------------------------------------------------------------
# TestPollGroupSnapshotData
# ---------------------------------------------------------------------------


class TestPollGroupSnapshotData:

    @patch("app.services.polling_service.save_flight_snapshot")
    @patch("app.services.polling_service.search_flights")
    def test_poll_group_saves_snapshot_with_serpapi_insights(self, mock_search, mock_save, db):
        from app.services.polling_service import run_polling_cycle

        group = _create_route_group(
            db,
            name="Snapshot Test",
            origins=["GRU"],
            destinations=["GIG"],
            travel_start=datetime.date(2026, 5, 1),
            travel_end=datetime.date(2026, 5, 8),
            duration_days=7,
        )

        mock_search.return_value = MOCK_SEARCH_SERPAPI

        with patch("app.services.polling_service.SessionLocal", return_value=db):
            run_polling_cycle()

        assert mock_save.call_count >= 1
        snapshot_data = mock_save.call_args_list[0][0][1]

        assert snapshot_data["route_group_id"] == group.id
        assert snapshot_data["origin"] == "GRU"
        assert snapshot_data["destination"] == "GIG"
        assert snapshot_data["price"] == 450.0
        assert snapshot_data["airline"] == "LATAM"
        assert snapshot_data["currency"] == "BRL"
        assert snapshot_data["price_min"] == 350
        assert snapshot_data["price_first_quartile"] == 400
        assert snapshot_data["price_median"] == 550.0
        assert snapshot_data["price_third_quartile"] == 700
        assert snapshot_data["price_classification"] == "MEDIUM"

    @patch("app.services.polling_service.get_historical_price_range")
    @patch("app.services.polling_service.save_flight_snapshot")
    @patch("app.services.polling_service.search_flights")
    def test_poll_group_uses_historical_range_when_fast_flights(
        self, mock_search, mock_save, mock_hist, db
    ):
        """Quando fonte e fast-flights (sem insights), usa range historico para classificar."""
        from app.services.polling_service import run_polling_cycle

        _create_route_group(
            db,
            name="FF Snapshot Test",
            origins=["GRU"],
            destinations=["GIG"],
            travel_start=datetime.date(2026, 5, 1),
            travel_end=datetime.date(2026, 5, 8),
            duration_days=7,
        )

        mock_search.return_value = MOCK_SEARCH_FF  # fast_flights, sem insights
        mock_hist.return_value = [400, 700]  # range historico

        with patch("app.services.polling_service.SessionLocal", return_value=db):
            run_polling_cycle()

        assert mock_save.call_count >= 1
        snapshot_data = mock_save.call_args_list[0][0][1]
        assert snapshot_data["price_classification"] == "MEDIUM"
        assert snapshot_data["price_first_quartile"] == 400
        assert snapshot_data["price_third_quartile"] == 700

    @patch("app.services.polling_service.get_historical_price_range")
    @patch("app.services.polling_service.save_flight_snapshot")
    @patch("app.services.polling_service.search_flights")
    def test_poll_group_no_classification_without_history(
        self, mock_search, mock_save, mock_hist, db
    ):
        """Sem insights e sem historico, price_classification fica None."""
        from app.services.polling_service import run_polling_cycle

        _create_route_group(
            db,
            name="No History",
            origins=["GRU"],
            destinations=["GIG"],
            travel_start=datetime.date(2026, 5, 1),
            travel_end=datetime.date(2026, 5, 8),
            duration_days=7,
        )

        mock_search.return_value = MOCK_SEARCH_FF
        mock_hist.return_value = None  # sem historico suficiente

        with patch("app.services.polling_service.SessionLocal", return_value=db):
            run_polling_cycle()

        snapshot_data = mock_save.call_args_list[0][0][1]
        assert snapshot_data["price_classification"] is None


# ---------------------------------------------------------------------------
# TestQuotaUsage
# ---------------------------------------------------------------------------


class TestQuotaUsage:

    @patch("app.services.polling_service.increment_usage")
    @patch("app.services.polling_service.save_flight_snapshot")
    @patch("app.services.polling_service.search_flights")
    def test_increment_usage_only_for_serpapi(self, mock_search, mock_save, mock_inc, db):
        """increment_usage so e chamado quando a fonte e serpapi."""
        from app.services.polling_service import run_polling_cycle

        _create_route_group(
            db,
            name="Quota Test",
            origins=["GRU"],
            destinations=["GIG"],
            travel_start=datetime.date(2026, 5, 1),
            travel_end=datetime.date(2026, 5, 8),
            duration_days=7,
        )

        mock_search.return_value = MOCK_SEARCH_FF  # fast_flights

        with patch("app.services.polling_service.SessionLocal", return_value=db):
            run_polling_cycle()

        mock_inc.assert_not_called()

    @patch("app.services.polling_service.increment_usage")
    @patch("app.services.polling_service.save_flight_snapshot")
    @patch("app.services.polling_service.search_flights")
    def test_increment_usage_called_for_serpapi(self, mock_search, mock_save, mock_inc, db):
        """increment_usage e chamado quando a fonte e serpapi."""
        from app.services.polling_service import run_polling_cycle

        _create_route_group(
            db,
            name="Quota SerpAPI",
            origins=["GRU"],
            destinations=["GIG"],
            travel_start=datetime.date(2026, 5, 1),
            travel_end=datetime.date(2026, 5, 8),
            duration_days=7,
        )

        mock_search.return_value = MOCK_SEARCH_SERPAPI  # serpapi

        with patch("app.services.polling_service.SessionLocal", return_value=db):
            run_polling_cycle()

        mock_inc.assert_called_once()


# ---------------------------------------------------------------------------
# TestPollingAlertIntegration
# ---------------------------------------------------------------------------


class TestPollingAlertIntegration:

    @patch("app.services.polling_service.send_email")
    @patch("app.services.polling_service.compose_consolidated_email")
    @patch("app.services.polling_service.should_alert")
    @patch("app.services.polling_service.detect_signals")
    @patch("app.services.polling_service.save_flight_snapshot")
    @patch("app.services.polling_service.search_flights")
    def test_polling_sends_alert_on_signal(
        self, mock_search, mock_save, mock_detect, mock_should_alert, mock_compose, mock_send, db
    ):
        from app.services.polling_service import run_polling_cycle

        _create_route_group(
            db, origins=["GRU"], destinations=["GIG"],
            travel_start=datetime.date(2026, 5, 1),
            travel_end=datetime.date(2026, 5, 8), duration_days=7,
        )

        mock_search.return_value = MOCK_SEARCH_FF
        mock_save.return_value = MagicMock()
        mock_detect.return_value = [MagicMock()]
        mock_should_alert.return_value = True
        mock_compose.return_value = MagicMock()

        with patch("app.services.polling_service.SessionLocal", return_value=db):
            run_polling_cycle()

        mock_send.assert_called_once()

    @patch("app.services.polling_service.send_email")
    @patch("app.services.polling_service.compose_consolidated_email")
    @patch("app.services.polling_service.should_alert")
    @patch("app.services.polling_service.detect_signals")
    @patch("app.services.polling_service.save_flight_snapshot")
    @patch("app.services.polling_service.search_flights")
    def test_polling_skips_alert_silenced_group(
        self, mock_search, mock_save, mock_detect, mock_should_alert, mock_compose, mock_send, db
    ):
        from app.services.polling_service import run_polling_cycle

        _create_route_group(
            db, origins=["GRU"], destinations=["GIG"],
            travel_start=datetime.date(2026, 5, 1),
            travel_end=datetime.date(2026, 5, 8), duration_days=7,
        )

        mock_search.return_value = MOCK_SEARCH_FF
        mock_save.return_value = MagicMock()
        mock_detect.return_value = [MagicMock()]
        mock_should_alert.return_value = False

        with patch("app.services.polling_service.SessionLocal", return_value=db):
            run_polling_cycle()

        mock_send.assert_not_called()

    @patch("app.services.polling_service.send_email")
    @patch("app.services.polling_service.compose_consolidated_email")
    @patch("app.services.polling_service.should_alert")
    @patch("app.services.polling_service.detect_signals")
    @patch("app.services.polling_service.save_flight_snapshot")
    @patch("app.services.polling_service.search_flights")
    def test_polling_continues_on_smtp_failure(
        self, mock_search, mock_save, mock_detect, mock_should_alert, mock_compose, mock_send, db
    ):
        from app.services.polling_service import run_polling_cycle

        _create_route_group(
            db, origins=["GRU"], destinations=["GIG"],
            travel_start=datetime.date(2026, 5, 1),
            travel_end=datetime.date(2026, 5, 8), duration_days=7,
        )

        mock_search.return_value = MOCK_SEARCH_FF
        mock_save.return_value = MagicMock()
        mock_detect.return_value = [MagicMock()]
        mock_should_alert.return_value = True
        mock_compose.return_value = MagicMock()
        mock_send.side_effect = Exception("SMTP connection refused")

        with patch("app.services.polling_service.SessionLocal", return_value=db):
            run_polling_cycle()

        mock_send.assert_called_once()


# ---------------------------------------------------------------------------
# TestConsolidatedEmailFlow
# ---------------------------------------------------------------------------


class TestConsolidatedEmailFlow:

    @patch("app.services.polling_service.send_email")
    @patch("app.services.polling_service.compose_consolidated_email")
    @patch("app.services.polling_service.should_alert")
    @patch("app.services.polling_service.detect_signals")
    @patch("app.services.polling_service.save_flight_snapshot")
    @patch("app.services.polling_service.search_flights")
    def test_poll_group_sends_consolidated_email_when_signals_detected(
        self, mock_search, mock_save, mock_detect, mock_should_alert, mock_compose, mock_send, db
    ):
        from app.services.polling_service import run_polling_cycle

        group = _create_route_group(
            db, name="Consolidated Test",
            origins=["GRU"], destinations=["GIG"],
            travel_start=datetime.date(2026, 5, 1),
            travel_end=datetime.date(2026, 5, 8), duration_days=7,
        )

        mock_search.return_value = MOCK_SEARCH_FF
        fake_snapshot = MagicMock()
        mock_save.return_value = fake_snapshot
        fake_signal = MagicMock()
        mock_detect.return_value = [fake_signal]
        mock_should_alert.return_value = True
        fake_msg = MagicMock()
        mock_compose.return_value = fake_msg

        with patch("app.services.polling_service.SessionLocal", return_value=db):
            run_polling_cycle()

        mock_compose.assert_called_once()
        call_args = mock_compose.call_args[0]
        assert fake_signal in call_args[0]
        assert call_args[2].name == "Consolidated Test"
        mock_send.assert_called_once_with(fake_msg)

    @patch("app.services.polling_service.send_email")
    @patch("app.services.polling_service.compose_consolidated_email")
    @patch("app.services.polling_service.should_alert")
    @patch("app.services.polling_service.detect_signals")
    @patch("app.services.polling_service.save_flight_snapshot")
    @patch("app.services.polling_service.search_flights")
    def test_poll_group_no_email_when_no_signals(
        self, mock_search, mock_save, mock_detect, mock_should_alert, mock_compose, mock_send, db
    ):
        from app.services.polling_service import run_polling_cycle

        _create_route_group(
            db, origins=["GRU"], destinations=["GIG"],
            travel_start=datetime.date(2026, 5, 1),
            travel_end=datetime.date(2026, 5, 8), duration_days=7,
        )

        mock_search.return_value = MOCK_SEARCH_FF
        mock_save.return_value = MagicMock()
        mock_detect.return_value = []

        with patch("app.services.polling_service.SessionLocal", return_value=db):
            run_polling_cycle()

        mock_compose.assert_not_called()
        mock_send.assert_not_called()

    @patch("app.services.polling_service.detect_signals")
    @patch("app.services.polling_service.save_flight_snapshot")
    @patch("app.services.polling_service.is_duplicate_snapshot")
    def test_process_flight_returns_signal_and_snapshot(self, mock_is_dup, mock_save, mock_detect, db):
        from app.services.polling_service import _process_flight

        group = _create_route_group(db, name="Return Test")
        mock_is_dup.return_value = False
        fake_snapshot = MagicMock()
        mock_save.return_value = fake_snapshot
        fake_signal = MagicMock()
        mock_detect.return_value = [fake_signal]

        result = _process_flight(
            db, group, "GRU", "GIG",
            datetime.date(2026, 5, 1), datetime.date(2026, 5, 8),
            {"price": 450, "airline": "LATAM"}, MOCK_INSIGHTS,
        )

        assert result is not None
        snapshot_result, signals_result = result
        assert snapshot_result == fake_snapshot
        assert signals_result == [fake_signal]