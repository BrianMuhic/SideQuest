from datetime import date, datetime
from zoneinfo import ZoneInfo

_UTC_ZONEINFO = ZoneInfo("UTC")


def now_utc() -> datetime:
    """Return timezone aware datetime for now in UTC."""
    return datetime.now(_UTC_ZONEINFO)


def tz_offset_aware(datetime_: datetime, tzinfo: ZoneInfo = _UTC_ZONEINFO) -> datetime:
    """Return a timezone offset-aware datetime, input can be naive or aware.

    - If datetime_ is naive (no timezone), assumes it's UTC and converts to target timezone
    - If datetime_ is aware (has timezone), converts to the target timezone
    """
    if datetime_.tzinfo is None:
        datetime_ = datetime_.replace(tzinfo=_UTC_ZONEINFO)
    return datetime_.astimezone(tzinfo)


def to_datetime(date_: date, tzinfo: ZoneInfo = _UTC_ZONEINFO) -> datetime:
    """Convert a date to a timezone-aware datetime at noon (12:00:00)."""
    return datetime(date_.year, date_.month, date_.day, 12, tzinfo=tzinfo)


def get_ordinal_suffix(day: int | date | datetime | str) -> str:
    """Get the ordinal suffix for a day of the month."""

    if isinstance(day, (date, datetime)):
        day = day.day
    elif isinstance(day, str):
        day = int(day)

    if 11 <= day <= 13:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
