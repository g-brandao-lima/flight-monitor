import datetime
from unittest.mock import patch, MagicMock

from app.models import RouteGroup


# Mock data fixtures
MOCK_FLIGHTS = [
    {
        "price": 450,
        "airline": "LATAM",
        "flights": [
            {
                "airline": "LATAM",
                "departure_airport": {"id": "GRU"},
                "arrival_airport": {"id": "GIG"},
            }
        ],
        "type": "Round trip",
    }
]

MOCK_INSIGHTS = {
    "lowest_price": 350,
    "typical_price_range": [400, 700],
    "price_history": [[1700000000, 500], [1700100000, 480]],
}


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


class TestPollingCycleSkips:
    """Tests for polling cycle skip conditions."""

    @patch("app.services.polling_service.SerpApiClient")
    def test_polling_cycle_skips_when_not_configured(self, mock_client_cls, db):
        from app.services.polling_service import run_polling_cycle

        mock_instance = MagicMock()
        mock_instance.is_configured = False
        mock_client_cls.return_value = mock_instance

        run_polling_cycle()

        mock_instance.search_flights_with_insights.assert_not_called()


class TestPollingCycleProcessing:
    """Tests for polling cycle group processing."""

    @patch("app.services.polling_service.save_flight_snapshot")
    @patch("app.services.polling_service.SerpApiClient")
    def test_polling_cycle_processes_active_groups(
        self, mock_client_cls, mock_save, db
    ):
        from app.services.polling_service import run_polling_cycle

        _create_route_group(db, name="Group A")
        _create_route_group(db, name="Group B")

        mock_instance = MagicMock()
        mock_instance.is_configured = True
        mock_instance.search_flights_with_insights.return_value = (MOCK_FLIGHTS, MOCK_INSIGHTS)
        mock_client_cls.return_value = mock_instance

        with patch("app.services.polling_service.SessionLocal", return_value=db):
            run_polling_cycle()

        assert mock_save.call_count >= 2

    @patch("app.services.polling_service.save_flight_snapshot")
    @patch("app.services.polling_service.SerpApiClient")
    def test_polling_cycle_skips_inactive_groups(
        self, mock_client_cls, mock_save, db
    ):
        from app.services.polling_service import run_polling_cycle

        _create_route_group(db, name="Active", is_active=True)
        _create_route_group(db, name="Inactive", is_active=False)

        mock_instance = MagicMock()
        mock_instance.is_configured = True
        mock_instance.search_flights_with_insights.return_value = (MOCK_FLIGHTS, MOCK_INSIGHTS)
        mock_client_cls.return_value = mock_instance

        with patch("app.services.polling_service.SessionLocal", return_value=db):
            run_polling_cycle()

        assert mock_save.call_count >= 1

    @patch("app.services.polling_service.save_flight_snapshot")
    @patch("app.services.polling_service.SerpApiClient")
    def test_polling_cycle_continues_after_group_failure(
        self, mock_client_cls, mock_save, db
    ):
        from app.services.polling_service import run_polling_cycle

        _create_route_group(db, name="Failing Group")
        _create_route_group(db, name="Working Group")

        mock_instance = MagicMock()
        mock_instance.is_configured = True

        call_count = {"n": 0}

        def side_effect_search(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] <= 1:
                raise Exception("API Error for first group")
            return (MOCK_FLIGHTS, MOCK_INSIGHTS)

        mock_instance.search_flights_with_insights.side_effect = side_effect_search
        mock_client_cls.return_value = mock_instance

        with patch("app.services.polling_service.SessionLocal", return_value=db):
            run_polling_cycle()

        assert mock_save.call_count >= 1


class TestPollingUnifiedCall:
    """Tests that polling uses a single API call per combination."""

    @patch("app.services.polling_service.save_flight_snapshot")
    @patch("app.services.polling_service.SerpApiClient")
    def test_single_api_call_per_combination(self, mock_client_cls, mock_save, db):
        """Cada combinacao origem x destino x data usa exatamente 1 chamada API."""
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

        mock_instance = MagicMock()
        mock_instance.is_configured = True
        mock_instance.search_flights_with_insights.return_value = (MOCK_FLIGHTS, MOCK_INSIGHTS)
        mock_client_cls.return_value = mock_instance

        with patch("app.services.polling_service.SessionLocal", return_value=db):
            run_polling_cycle()

        # 1 origin x 1 dest x 1 date pair = 1 API call
        assert mock_instance.search_flights_with_insights.call_count == 1


class TestPollGroupCombinations:
    """Tests for route and date combination generation."""

    @patch("app.services.polling_service.save_flight_snapshot")
    @patch("app.services.polling_service.SerpApiClient")
    def test_poll_group_generates_origin_dest_combinations(
        self, mock_client_cls, mock_save, db
    ):
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

        mock_instance = MagicMock()
        mock_instance.is_configured = True
        mock_instance.search_flights_with_insights.return_value = (MOCK_FLIGHTS, MOCK_INSIGHTS)
        mock_client_cls.return_value = mock_instance

        with patch("app.services.polling_service.SessionLocal", return_value=db):
            run_polling_cycle()

        origins_called = [
            c.kwargs.get("origin", c.args[0] if c.args else None)
            for c in mock_instance.search_flights_with_insights.call_args_list
        ]
        assert "GRU" in origins_called or any(
            "GRU" in str(c) for c in mock_instance.search_flights_with_insights.call_args_list
        )
        assert "VCP" in origins_called or any(
            "VCP" in str(c) for c in mock_instance.search_flights_with_insights.call_args_list
        )

    @patch("app.services.polling_service.save_flight_snapshot")
    @patch("app.services.polling_service.SerpApiClient")
    def test_poll_group_generates_date_combinations_every_7_days(
        self, mock_client_cls, mock_save, db
    ):
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

        mock_instance = MagicMock()
        mock_instance.is_configured = True
        mock_instance.search_flights_with_insights.return_value = (MOCK_FLIGHTS, MOCK_INSIGHTS)
        mock_client_cls.return_value = mock_instance

        with patch("app.services.polling_service.SessionLocal", return_value=db):
            run_polling_cycle()

        # travel_start=May 1, travel_end=May 31, duration=7, step=7
        # Dates: May 1 (ret May 8), May 8 (ret May 15), May 15 (ret May 22), May 22 (ret May 29)
        # That's 4 date pairs
        assert mock_instance.search_flights_with_insights.call_count == 4

        dep_dates_used = [
            c.kwargs.get("departure_date")
            for c in mock_instance.search_flights_with_insights.call_args_list
        ]
        assert "2026-05-01" in dep_dates_used
        assert "2026-05-08" in dep_dates_used
        assert "2026-05-15" in dep_dates_used
        assert "2026-05-22" in dep_dates_used


class TestPollGroupSnapshotData:
    """Tests for snapshot data correctness."""

    @patch("app.services.polling_service.save_flight_snapshot")
    @patch("app.services.polling_service.SerpApiClient")
    def test_poll_group_saves_snapshot_with_price_insights(
        self, mock_client_cls, mock_save, db
    ):
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

        mock_instance = MagicMock()
        mock_instance.is_configured = True
        mock_instance.search_flights_with_insights.return_value = (MOCK_FLIGHTS, MOCK_INSIGHTS)
        mock_client_cls.return_value = mock_instance

        with patch("app.services.polling_service.SessionLocal", return_value=db):
            run_polling_cycle()

        assert mock_save.call_count >= 1

        first_call_args = mock_save.call_args_list[0]
        snapshot_data = first_call_args[0][1]

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

        assert snapshot_data["booking_classes"] == []

    @patch("app.services.polling_service.save_flight_snapshot")
    @patch("app.services.polling_service.SerpApiClient")
    def test_poll_group_handles_missing_price_insights(
        self, mock_client_cls, mock_save, db
    ):
        from app.services.polling_service import run_polling_cycle

        _create_route_group(
            db,
            name="No Insights",
            origins=["GRU"],
            destinations=["GIG"],
            travel_start=datetime.date(2026, 5, 1),
            travel_end=datetime.date(2026, 5, 8),
            duration_days=7,
        )

        mock_instance = MagicMock()
        mock_instance.is_configured = True
        mock_instance.search_flights_with_insights.return_value = (MOCK_FLIGHTS, None)
        mock_client_cls.return_value = mock_instance

        with patch("app.services.polling_service.SessionLocal", return_value=db):
            run_polling_cycle()

        assert mock_save.call_count >= 1

        snapshot_data = mock_save.call_args_list[0][0][1]
        assert snapshot_data["price_classification"] is None
        assert snapshot_data.get("price_min") is None
        assert snapshot_data.get("price_first_quartile") is None


class TestPollingAlertIntegration:
    """Tests for alert_service integration within the polling cycle (consolidated flow)."""

    @patch("app.services.polling_service.send_email")
    @patch("app.services.polling_service.compose_consolidated_email")
    @patch("app.services.polling_service.should_alert")
    @patch("app.services.polling_service.detect_signals")
    @patch("app.services.polling_service.save_flight_snapshot")
    @patch("app.services.polling_service.SerpApiClient")
    def test_polling_sends_alert_on_signal(
        self,
        mock_client_cls,
        mock_save,
        mock_detect,
        mock_should_alert,
        mock_compose,
        mock_send_email,
        db,
    ):
        from app.services.polling_service import run_polling_cycle

        _create_route_group(
            db,
            name="Alert Group",
            origins=["GRU"],
            destinations=["GIG"],
            travel_start=datetime.date(2026, 5, 1),
            travel_end=datetime.date(2026, 5, 8),
            duration_days=7,
        )

        mock_instance = MagicMock()
        mock_instance.is_configured = True
        mock_instance.search_flights_with_insights.return_value = (MOCK_FLIGHTS, MOCK_INSIGHTS)
        mock_client_cls.return_value = mock_instance

        fake_snapshot = MagicMock()
        mock_save.return_value = fake_snapshot
        fake_signal = MagicMock()
        mock_detect.return_value = [fake_signal]
        mock_should_alert.return_value = True
        fake_msg = MagicMock()
        mock_compose.return_value = fake_msg

        with patch("app.services.polling_service.SessionLocal", return_value=db):
            run_polling_cycle()

        mock_send_email.assert_called_once_with(fake_msg)

    @patch("app.services.polling_service.send_email")
    @patch("app.services.polling_service.compose_consolidated_email")
    @patch("app.services.polling_service.should_alert")
    @patch("app.services.polling_service.detect_signals")
    @patch("app.services.polling_service.save_flight_snapshot")
    @patch("app.services.polling_service.SerpApiClient")
    def test_polling_skips_alert_silenced_group(
        self,
        mock_client_cls,
        mock_save,
        mock_detect,
        mock_should_alert,
        mock_compose,
        mock_send_email,
        db,
    ):
        from app.services.polling_service import run_polling_cycle

        _create_route_group(
            db,
            name="Silenced Group",
            origins=["GRU"],
            destinations=["GIG"],
            travel_start=datetime.date(2026, 5, 1),
            travel_end=datetime.date(2026, 5, 8),
            duration_days=7,
        )

        mock_instance = MagicMock()
        mock_instance.is_configured = True
        mock_instance.search_flights_with_insights.return_value = (MOCK_FLIGHTS, MOCK_INSIGHTS)
        mock_client_cls.return_value = mock_instance

        fake_snapshot = MagicMock()
        mock_save.return_value = fake_snapshot
        fake_signal = MagicMock()
        mock_detect.return_value = [fake_signal]
        mock_should_alert.return_value = False

        with patch("app.services.polling_service.SessionLocal", return_value=db):
            run_polling_cycle()

        mock_send_email.assert_not_called()

    @patch("app.services.polling_service.send_email")
    @patch("app.services.polling_service.compose_consolidated_email")
    @patch("app.services.polling_service.should_alert")
    @patch("app.services.polling_service.detect_signals")
    @patch("app.services.polling_service.save_flight_snapshot")
    @patch("app.services.polling_service.SerpApiClient")
    def test_polling_continues_on_smtp_failure(
        self,
        mock_client_cls,
        mock_save,
        mock_detect,
        mock_should_alert,
        mock_compose,
        mock_send_email,
        db,
    ):
        from app.services.polling_service import run_polling_cycle

        _create_route_group(
            db,
            name="SMTP Failure Group",
            origins=["GRU"],
            destinations=["GIG"],
            travel_start=datetime.date(2026, 5, 1),
            travel_end=datetime.date(2026, 5, 8),
            duration_days=7,
        )

        mock_instance = MagicMock()
        mock_instance.is_configured = True
        mock_instance.search_flights_with_insights.return_value = (MOCK_FLIGHTS, MOCK_INSIGHTS)
        mock_client_cls.return_value = mock_instance

        fake_snapshot = MagicMock()
        mock_save.return_value = fake_snapshot
        fake_signal = MagicMock()
        mock_detect.return_value = [fake_signal]
        mock_should_alert.return_value = True
        mock_compose.return_value = MagicMock()
        mock_send_email.side_effect = Exception("SMTP connection refused")

        with patch("app.services.polling_service.SessionLocal", return_value=db):
            run_polling_cycle()

        mock_send_email.assert_called_once()


class TestConsolidatedEmailFlow:
    """Tests for consolidated email flow: 1 email per group per cycle."""

    @patch("app.services.polling_service.send_email")
    @patch("app.services.polling_service.compose_consolidated_email")
    @patch("app.services.polling_service.should_alert")
    @patch("app.services.polling_service.detect_signals")
    @patch("app.services.polling_service.save_flight_snapshot")
    @patch("app.services.polling_service.SerpApiClient")
    def test_poll_group_sends_consolidated_email_when_signals_detected(
        self,
        mock_client_cls,
        mock_save,
        mock_detect,
        mock_should_alert,
        mock_compose,
        mock_send_email,
        db,
    ):
        """Quando sinais sao detectados, envia 1 email consolidado via compose_consolidated_email."""
        from app.services.polling_service import run_polling_cycle

        group = _create_route_group(
            db,
            name="Consolidated Test",
            origins=["GRU"],
            destinations=["GIG"],
            travel_start=datetime.date(2026, 5, 1),
            travel_end=datetime.date(2026, 5, 8),
            duration_days=7,
        )

        mock_instance = MagicMock()
        mock_instance.is_configured = True
        mock_instance.search_flights_with_insights.return_value = (MOCK_FLIGHTS, MOCK_INSIGHTS)
        mock_client_cls.return_value = mock_instance

        fake_snapshot = MagicMock()
        mock_save.return_value = fake_snapshot

        fake_signal = MagicMock()
        mock_detect.return_value = [fake_signal]
        mock_should_alert.return_value = True
        fake_msg = MagicMock()
        mock_compose.return_value = fake_msg

        with patch("app.services.polling_service.SessionLocal", return_value=db):
            run_polling_cycle()

        # compose_consolidated_email deve ser chamado (nao compose_alert_email)
        mock_compose.assert_called_once()
        call_args = mock_compose.call_args
        # Primeiro arg: lista de sinais
        assert isinstance(call_args[0][0], list)
        assert fake_signal in call_args[0][0]
        # Segundo arg: lista de snapshots
        assert isinstance(call_args[0][1], list)
        # Terceiro arg: grupo
        assert call_args[0][2].name == "Consolidated Test"
        # send_email chamado 1 vez
        mock_send_email.assert_called_once_with(fake_msg)

    @patch("app.services.polling_service.send_email")
    @patch("app.services.polling_service.compose_consolidated_email")
    @patch("app.services.polling_service.should_alert")
    @patch("app.services.polling_service.detect_signals")
    @patch("app.services.polling_service.save_flight_snapshot")
    @patch("app.services.polling_service.SerpApiClient")
    def test_poll_group_no_email_when_no_signals(
        self,
        mock_client_cls,
        mock_save,
        mock_detect,
        mock_should_alert,
        mock_compose,
        mock_send_email,
        db,
    ):
        """Quando nenhum sinal e detectado, nenhum email e enviado."""
        from app.services.polling_service import run_polling_cycle

        _create_route_group(
            db,
            name="No Signals",
            origins=["GRU"],
            destinations=["GIG"],
            travel_start=datetime.date(2026, 5, 1),
            travel_end=datetime.date(2026, 5, 8),
            duration_days=7,
        )

        mock_instance = MagicMock()
        mock_instance.is_configured = True
        mock_instance.search_flights_with_insights.return_value = (MOCK_FLIGHTS, MOCK_INSIGHTS)
        mock_client_cls.return_value = mock_instance

        fake_snapshot = MagicMock()
        mock_save.return_value = fake_snapshot
        mock_detect.return_value = []  # Nenhum sinal

        with patch("app.services.polling_service.SessionLocal", return_value=db):
            run_polling_cycle()

        mock_compose.assert_not_called()
        mock_send_email.assert_not_called()

    @patch("app.services.polling_service.send_email")
    @patch("app.services.polling_service.compose_consolidated_email")
    @patch("app.services.polling_service.should_alert")
    @patch("app.services.polling_service.detect_signals")
    @patch("app.services.polling_service.save_flight_snapshot")
    @patch("app.services.polling_service.SerpApiClient")
    def test_poll_group_no_email_when_silenced(
        self,
        mock_client_cls,
        mock_save,
        mock_detect,
        mock_should_alert,
        mock_compose,
        mock_send_email,
        db,
    ):
        """Quando grupo esta silenciado, nenhum email e enviado mesmo com sinais."""
        from app.services.polling_service import run_polling_cycle

        _create_route_group(
            db,
            name="Silenced Consolidated",
            origins=["GRU"],
            destinations=["GIG"],
            travel_start=datetime.date(2026, 5, 1),
            travel_end=datetime.date(2026, 5, 8),
            duration_days=7,
        )

        mock_instance = MagicMock()
        mock_instance.is_configured = True
        mock_instance.search_flights_with_insights.return_value = (MOCK_FLIGHTS, MOCK_INSIGHTS)
        mock_client_cls.return_value = mock_instance

        fake_snapshot = MagicMock()
        mock_save.return_value = fake_snapshot
        fake_signal = MagicMock()
        mock_detect.return_value = [fake_signal]
        mock_should_alert.return_value = False  # Silenciado

        with patch("app.services.polling_service.SessionLocal", return_value=db):
            run_polling_cycle()

        mock_send_email.assert_not_called()

    @patch("app.services.polling_service.send_email")
    @patch("app.services.polling_service.compose_consolidated_email")
    @patch("app.services.polling_service.should_alert")
    @patch("app.services.polling_service.detect_signals")
    @patch("app.services.polling_service.save_flight_snapshot")
    @patch("app.services.polling_service.SerpApiClient")
    def test_poll_group_accumulates_all_signals(
        self,
        mock_client_cls,
        mock_save,
        mock_detect,
        mock_should_alert,
        mock_compose,
        mock_send_email,
        db,
    ):
        """Quando multiplos voos geram sinais, todos sao acumulados no email unico."""
        from app.services.polling_service import run_polling_cycle

        _create_route_group(
            db,
            name="Multi Signal",
            origins=["GRU"],
            destinations=["GIG"],
            travel_start=datetime.date(2026, 5, 1),
            travel_end=datetime.date(2026, 5, 15),
            duration_days=7,
        )

        mock_instance = MagicMock()
        mock_instance.is_configured = True
        # 2 flights per search, 2 date pairs
        two_flights = [
            {"price": 450, "airline": "LATAM", "flights": [], "type": "Round trip"},
            {"price": 550, "airline": "GOL", "flights": [], "type": "Round trip"},
        ]
        mock_instance.search_flights_with_insights.return_value = (two_flights, MOCK_INSIGHTS)
        mock_client_cls.return_value = mock_instance

        fake_snapshot = MagicMock()
        mock_save.return_value = fake_snapshot

        signal_a = MagicMock(signal_type="PRECO_BAIXO")
        signal_b = MagicMock(signal_type="BALDE_FECHANDO")
        # Alternate signals per call
        mock_detect.side_effect = [[signal_a], [signal_b], [signal_a], [signal_b]]
        mock_should_alert.return_value = True
        mock_compose.return_value = MagicMock()

        with patch("app.services.polling_service.SessionLocal", return_value=db):
            run_polling_cycle()

        # compose_consolidated_email chamado 1 vez com TODOS os sinais acumulados
        mock_compose.assert_called_once()
        all_signals = mock_compose.call_args[0][0]
        assert len(all_signals) >= 2  # Pelo menos 2 sinais acumulados

    @patch("app.services.polling_service.detect_signals")
    @patch("app.services.polling_service.save_flight_snapshot")
    @patch("app.services.polling_service.is_duplicate_snapshot")
    def test_process_flight_returns_signal_and_snapshot(
        self,
        mock_is_dup,
        mock_save,
        mock_detect,
        db,
    ):
        """_process_flight retorna (snapshot, signals) ao inves de enviar email."""
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
