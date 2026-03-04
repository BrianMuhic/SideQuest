import re
from datetime import date, datetime
from typing import Any

from flask import Flask

from config import config


def add_template_filters(app: Flask) -> None:
    """Register custom Jinja template filters with the Flask app."""
    for func in (
        phone_format,
        date_format,
        date_long_format,
        datetime_format,
        date_format_str,
        datetime_format_str,
        currency_format,
    ):
        app.jinja_env.filters[func.__name__] = func


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


def date_format(date_: date | None) -> str:
    """
    Formats a date object using the configured date format.
    in html: {{ record.date | date_format }}
    """
    return date_.strftime(config.DATE_FORMAT) if date_ else ""


def date_long_format(date_: date | None) -> str:
    """
    Formats a date object using the configured long date format.
    in html: {{ record.date | date_long_format }}
    """
    return date_.strftime(config.DATE_LONG_FORMAT) if date_ else ""


def datetime_format(datetime_: datetime | None) -> str:
    """
    Formats a datetime object using the configured datetime format.
    in html: `{{ record.date | datetime_format }}`
    """
    return datetime_.strftime(config.DATETIME_FORMAT_LONG) if datetime_ else ""


def date_format_str(_: Any) -> str:
    """
    Returns the date format string from the config, converted to Moment.js format.
    in html: `{{ '' | date_format_str }}`
    """
    return _convert_py_format_to_moment(config.DATE_FORMAT)


def datetime_format_str(_: Any) -> str:
    """
    Returns the datetime format string from the config, converted to Moment.js format.
    in html: `{{ '' | datetime_format_str }}`
    """
    return _convert_py_format_to_moment(config.DATETIME_FORMAT_LONG)


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


# ==================== Helpers ==================== #


def _convert_py_format_to_moment(py_format: str) -> str:
    """Converts Python's strftime format to Moment.js format."""

    format_map = {
        "%Y": "YYYY",
        "%y": "YY",
        "%m": "MM",
        "%-m": "M",
        "%d": "DD",
        "%-d": "D",
        "%H": "HH",
        "%-H": "H",
        "%I": "hh",
        "%-I": "h",
        "%M": "mm",
        "%-M": "m",
        "%S": "ss",
        "%-S": "s",
        "%f": "SSS",
        "%z": "Z",
        "%Z": "z",
        "%j": "DDDD",
        "%-j": "DDD",
        "%U": "ww",
        "%W": "ww",
        "%w": "e",
        "%a": "ddd",
        "%A": "dddd",
        "%b": "MMM",
        "%B": "MMMM",
        "%p": "A",
        "%c": "llll",
        "%x": "L",
        "%X": "LT",
        "%%": "%",
    }

    js_format = py_format
    for py_spec in sorted(format_map.keys(), key=len, reverse=True):
        js_format = js_format.replace(py_spec, format_map[py_spec])

    return js_format
