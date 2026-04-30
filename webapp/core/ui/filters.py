import re
from datetime import date, datetime
from zoneinfo import ZoneInfo

from jinja2 import Environment

from config import config


def add_template_filters(jinja_env: Environment) -> None:
    """Register custom Jinja template filters with the Flask app."""
    for func in (
        phone_format,
        date_format,
        date_long_format,
        datetime_format,
        currency_format,
    ):
        jinja_env.filters[func.__name__] = func


# ==================== Filters ==================== #


def phone_format(phone_number: str | None) -> str:
    """
    Removes any non-digits and if there are 10 digits, returns ###-###-####
    in html: `{{ phone_number | phone_format }}`
    """
    if not phone_number:
        return ""

    phone_number = re.sub(r"\D", "", phone_number)
    if len(phone_number) == 11 and phone_number[0] == "1":
        phone_number = phone_number[1:]
    if len(phone_number) == 10:
        return f"{phone_number[:3]}-{phone_number[3:6]}-{phone_number[6:]}"
    return phone_number


def date_format(date_: date | datetime | None, format: str | None = None) -> str:
    """
    Formats a date object using the configured date format.
    in html: {{ record.date | date_format }}
    """
    format = format or config.DATE_FORMAT
    return date_.strftime(format) if date_ else ""


def date_long_format(date_: date | datetime | None, format: str | None = None) -> str:
    """
    Formats a date object using the configured long date format.
    in html: {{ record.date | date_long_format }}
    """
    format = format or config.DATE_LONG_FORMAT
    return date_.strftime(format) if date_ else ""


def datetime_format(datetime_: datetime | None, format: str | None = None) -> str:
    """
    Formats a datetime object using the configured datetime format.
    If the datetime object is timezone aware, convert it to config.LOCAL_TIMEZONE.
    in html: `{{ record.date | datetime_format }}`
    """
    if not datetime_:
        return ""
    if datetime_.tzinfo is not None:
        datetime_ = datetime_.astimezone(ZoneInfo(config.LOCAL_TIMEZONE))
    format = format or config.DATETIME_FORMAT
    return datetime_.strftime(format)


def currency_format(value: float | int | str | None, decimals: int = 0, symbol: str = "$") -> str:
    """
    Formats a number as currency with optional decimal places and currency symbol.
    Returns empty string if value is None.

    in html: `{{ 1234.00 | currency_format }}`  -> "$1,234"
    """
    if value is None:
        return ""
    if isinstance(value, str):
        value = float(value)
    return f"{symbol}{value:,.{decimals}f}"
