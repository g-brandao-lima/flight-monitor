from unittest.mock import patch, MagicMock


class TestSchedulerSetup:
    """Tests for scheduler initialization and shutdown."""

    @patch("app.scheduler.BackgroundScheduler")
    def test_scheduler_registers_daily_cron_job(self, mock_scheduler_cls):
        from app.scheduler import init_scheduler

        mock_sched_instance = MagicMock()
        mock_scheduler_cls.return_value = mock_sched_instance

        import app.scheduler as sched_module

        sched_module.scheduler = mock_sched_instance

        init_scheduler()

        assert mock_sched_instance.add_job.call_count == 3

        job_ids = [c.kwargs.get("id") for c in mock_sched_instance.add_job.call_args_list]
        assert "polling_morning" in job_ids
        assert "polling_afternoon" in job_ids
        assert "weekly_digest" in job_ids

        from apscheduler.triggers.cron import CronTrigger
        for call in mock_sched_instance.add_job.call_args_list:
            trigger = call.kwargs.get("trigger")
            assert isinstance(trigger, CronTrigger)

        mock_sched_instance.start.assert_called_once()

    @patch("app.scheduler.BackgroundScheduler")
    def test_scheduler_shutdown_stops_cleanly(self, mock_scheduler_cls):
        from app.scheduler import shutdown_scheduler

        mock_sched_instance = MagicMock()
        mock_scheduler_cls.return_value = mock_sched_instance

        import app.scheduler as sched_module

        sched_module.scheduler = mock_sched_instance

        shutdown_scheduler()

        mock_sched_instance.shutdown.assert_called_once()
