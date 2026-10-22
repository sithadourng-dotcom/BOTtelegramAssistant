"""Scheduled background jobs for automated reminders and alerts."""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from aiogram import Bot

from app.config import settings
from app.database.database import get_db_context
from app.services.notifications import NotificationService
from app.services.reports import ReportService
from app.services.products import ProductService
from app.services.tasks import TaskService
from app.utils.logger import logger
from app.utils.tz import get_timezone, today_tz

scheduler = AsyncIOScheduler(timezone=get_timezone())


async def morning_reminder_job(bot: Bot) -> None:
    """Send daily morning motivation and priorities."""
    logger.info("Executing morning reminder job...")
    try:
        async with get_db_context() as session:
            notif_service = NotificationService(session, bot)
            sent = await notif_service.send_morning_reminder()
            logger.info(f"Morning reminders sent to {sent} members.")
    except Exception as e:
        logger.error(f"Error executing morning reminder job: {e}")


async def daily_report_reminder_job(bot: Bot) -> None:
    """Remind team members who have not submitted today's report."""
    logger.info("Executing daily report reminder job...")
    try:
        async with get_db_context() as session:
            report_service = ReportService(session)
            notif_service = NotificationService(session, bot)

            missing = await report_service.get_missing_reports(today_tz())
            if missing:
                sent = await notif_service.send_report_reminder(missing)
                logger.info(f"Daily report reminders sent to {sent} members.")
            else:
                logger.info("All team members have already submitted today's report.")
    except Exception as e:
        logger.error(f"Error executing daily report reminder job: {e}")


async def low_stock_check_job(bot: Bot) -> None:
    """Check for inventory dropping below minimum stock."""
    logger.info("Executing low stock check job...")
    try:
        async with get_db_context() as session:
            prod_service = ProductService(session)
            notif_service = NotificationService(session, bot)

            low_stock_prods = await prod_service.get_low_stock_products()
            for prod in low_stock_prods:
                await notif_service.notify_low_stock(prod)
            logger.info(f"Checked low stock: {len(low_stock_prods)} products alerted.")
    except Exception as e:
        logger.error(f"Error in low stock check job: {e}")


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    """Configure and schedule all recurring business jobs."""
    # Morning reminder (e.g. 08:00)
    morning_hour, morning_minute = map(int, settings.MORNING_REMINDER_TIME.split(":"))
    scheduler.add_job(
        morning_reminder_job,
        trigger=CronTrigger(hour=morning_hour, minute=morning_minute, timezone=get_timezone()),
        args=[bot],
        id="morning_reminder",
        name="Daily Morning Priorities Reminder",
        replace_existing=True,
    )

    # Daily report reminder (e.g. 18:00)
    report_hour, report_minute = map(int, settings.DAILY_REPORT_REMINDER_TIME.split(":"))
    scheduler.add_job(
        daily_report_reminder_job,
        trigger=CronTrigger(hour=report_hour, minute=report_minute, timezone=get_timezone()),
        args=[bot],
        id="report_reminder",
        name="Daily Report Missing Reminder",
        replace_existing=True,
    )

    # Low stock periodic check (every 4 hours)
    scheduler.add_job(
        low_stock_check_job,
        trigger=IntervalTrigger(hours=4),
        args=[bot],
        id="low_stock_check",
        name="Periodic Low Stock Monitor",
        replace_existing=True,
    )

    return scheduler
