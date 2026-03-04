from datetime import date, datetime
from zoneinfo import ZoneInfo

from constant import LOCAL_ZONEINFO


def tz_offset_aware(datetime_: datetime, tzinfo: ZoneInfo = LOCAL_ZONEINFO) -> datetime:
    """Return a timezone offset-aware datetime, input can be naive or aware."""
    return datetime_.replace(tzinfo=tzinfo)


def to_datetime(date_: date, tzinfo: ZoneInfo = LOCAL_ZONEINFO) -> datetime:
    """Convert a date to a timezone-aware datetime at noon (12:00:00)."""
    return datetime(date_.year, date_.month, date_.day, 12, tzinfo=tzinfo)


def ordinal_suffix(day: int | date | datetime | str) -> str:
    """Get the ordinal suffix for a day of the month."""

    if isinstance(day, (date, datetime)):
        day = day.day
    elif isinstance(day, str):
        day = int(day)

    if 11 <= day <= 13:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
