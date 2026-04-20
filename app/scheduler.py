import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.services.polling_service import run_polling_cycle
from app.services.weekly_digest_service import run_weekly_digest

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def init_scheduler():
    """Inicializa o scheduler com jobs de polling e digest.

    Polling: 04:00 BRT (07:00 UTC) e 16:00 BRT (19:00 UTC)
    Weekly digest: terca 18:00 BRT (21:00 UTC)
    """
    scheduler.add_job(
        run_polling_cycle,
        trigger=CronTrigger(hour=7, minute=0),  # 07:00 UTC = 04:00 BRT
        id="polling_morning",
        name="Polling matinal (04:00 BRT)",
        replace_existing=True,
    )
    scheduler.add_job(
        run_polling_cycle,
        trigger=CronTrigger(hour=19, minute=0),  # 19:00 UTC = 16:00 BRT
        id="polling_afternoon",
        name="Polling vespertino (16:00 BRT)",
        replace_existing=True,
    )
    scheduler.add_job(
        run_weekly_digest,
        trigger=CronTrigger(day_of_week="tue", hour=21, minute=0),  # ter 21:00 UTC = 18:00 BRT
        id="weekly_digest",
        name="Weekly digest (terca 18:00 BRT)",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started: polling 2x/dia + weekly digest terca 18:00 BRT")


def shutdown_scheduler():
    """Para o scheduler de forma limpa."""
    scheduler.shutdown(wait=False)
    logger.info("Scheduler stopped")
