"""Formatting helpers for python"""

from decimal import Decimal
from typing import Any


def format_currency(val: float | Decimal | None, negative_parentheses: bool = True) -> str:
    """Handle parentheses for negative currency. Returns empty string for None."""
    if val is None:
        return ""
    if val >= 0:
        return f"${val:,.2f}"
    if negative_parentheses:
        return f"(${-val:,.2f})"
    return f"-${-val:,.2f}"


def truncate(string: str, length: int) -> str:
    """Return a truncated version of the given string"""
    return string if len(string) < length else f"{string[:length]}…"


def join_field(d: dict[str, Any], key: str, sep: str = ", ") -> None:
    """Join a list field in dictionary d[key] with separator."""
    d[key] = sep.join(d.get(key) or [])
