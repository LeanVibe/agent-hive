from datetime import datetime, timezone
from typing import Final

UTC_TZ: Final = timezone.utc

def now_utc() -> datetime:
    """Return a timezone-aware current UTC datetime.

    Centralized to avoid use of deprecated datetime.utcnow().
    """
    return datetime.now(UTC_TZ)


def iso_now_utc() -> str:
    """Return current UTC time as ISO 8601 string with timezone info."""
    return now_utc().isoformat()


def ensure_naive(dt: datetime) -> datetime:
    """Return a naive (tzinfo=None) UTC datetime for safe comparisons.

    If the datetime is timezone-aware, drop tzinfo. Assumes input is UTC.
    """
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt
