"""Timezone utilities for consistent datetime handling."""
from datetime import datetime
from zoneinfo import ZoneInfo

from src.config import settings


def get_timezone() -> ZoneInfo:
    """Get the configured timezone.

    Returns:
        ZoneInfo: Asia/Taipei timezone object
    """
    return ZoneInfo(settings.TIMEZONE)


def now() -> datetime:
    """Get current time in configured timezone.

    Returns:
        datetime: Current time with timezone info (Asia/Taipei)
    """
    return datetime.now(get_timezone())


def to_local(dt: datetime) -> datetime:
    """Convert datetime to configured timezone.

    Args:
        dt: Datetime object (naive or timezone-aware)

    Returns:
        datetime: Datetime in Asia/Taipei timezone
    """
    taipei_tz = get_timezone()
    if dt.tzinfo is None:
        # Naive datetime: assume it's already in Asia/Taipei
        return dt.replace(tzinfo=taipei_tz)
    else:
        # Aware datetime: convert to Asia/Taipei
        return dt.astimezone(taipei_tz)


def from_str(s: str, format_str: str = None) -> datetime:
    """Parse string to timezone-aware datetime.

    Args:
        s: Datetime string to parse
        format_str: Optional format string (default: ISO format)

    Returns:
        datetime: Timezone-aware datetime in Asia/Taipei timezone

    Raises:
        ValueError: If string cannot be parsed
    """
    taipei_tz = get_timezone()

    if format_str:
        dt = datetime.strptime(s, format_str)
        return dt.replace(tzinfo=taipei_tz)

    # Try ISO format parsing
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=taipei_tz)
    else:
        return dt.astimezone(taipei_tz)