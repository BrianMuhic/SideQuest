"""Utilities for random python tasks"""

from typing import Any, Callable, TypeVar

from flask import request
from werkzeug.exceptions import BadRequest

T = TypeVar("T")


def contents(obj: Any) -> str:
    """Return contents of object's internal dict"""
    dict_ = obj.__dict__.copy()
    return "\n".join(f"\t{k:<24}\t{v:.96}" for k, v in dict_.items())


def _coerce_value(raw_value: Any, coerce: Callable[[str], T], default: T | None = None) -> T | None:
    """Helper to coerce a raw value, returning default if None or coercion fails."""
    if raw_value is None:
        return default

    if coerce is bool and isinstance(raw_value, str):
        lower_value = raw_value.lower().strip()
        if lower_value in ("true", "1", "yes", "on"):
            return True  # type: ignore
        elif lower_value in ("false", "0", "no", "off"):
            return False  # type: ignore
        else:
            return default

    try:
        return coerce(raw_value)
    except Exception:
        return default


def get_param(key: str, coerce: Callable[[str], T], default: T | None = None) -> T | None:
    """Extract and coerce a query parameter, returning default if missing or invalid."""
    raw_value = request.args.get(key=key)
    return _coerce_value(raw_value, coerce, default)


def require_param(key: str, coerce: Callable[[str], T], default: T | None = None) -> T:
    """Extract and coerce a required query parameter, using default or raising BadRequest if missing or invalid."""
    value = get_param(key=key, coerce=coerce, default=default)
    if value is None:
        raise BadRequest(f"Required parameter '{key}' is missing or invalid")
    return value


def get_json(key: str, coerce: Callable[[Any], T], default: T | None = None) -> T | None:
    """Extract and coerce a field from JSON request body, returning default if missing or invalid."""
    json_data = request.get_json(silent=True)
    if json_data is None:
        return default
    raw_value = json_data.get(key)
    return _coerce_value(raw_value, coerce, default)


def require_json(key: str, coerce: Callable[[Any], T], default: T | None = None) -> T:
    """Extract and coerce a required field from JSON request body."""
    value = get_json(key=key, coerce=coerce, default=default)
    if value is None:
        raise BadRequest(f"Required JSON field '{key}' is missing or invalid")
    return value
