"""Timezone utilities for business operations."""

from datetime import datetime, date, timedelta
import pytz
from app.config import settings


def get_timezone(tz_name: str | None = None) -> pytz.BaseTzInfo:
    """Return pytz timezone object, falling back to configured timezone."""
    name = tz_name or settings.TIMEZONE
    try:
        return pytz.timezone(name)
    except pytz.UnknownTimeZoneError:
        return pytz.timezone("Asia/Phnom_Penh")


def now_tz(tz_name: str | None = None) -> datetime:
    """Get current datetime in the configured timezone."""
    tz = get_timezone(tz_name)
    return datetime.now(tz)


def today_tz(tz_name: str | None = None) -> date:
    """Get current date in the configured timezone."""
    return now_tz(tz_name).date()


def format_dt(dt: datetime | None, fmt: str = "%Y-%m-%d %H:%M") -> str:
    """Format datetime string nicely."""
    if not dt:
        return "N/A"
    return dt.strftime(fmt)


def format_date(d: date | None, fmt: str = "%Y-%m-%d") -> str:
    """Format date string nicely."""
    if not d:
        return "N/A"
    return d.strftime(fmt)
