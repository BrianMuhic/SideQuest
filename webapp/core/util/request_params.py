"""Utilities for extracting and coercing Flask request parameters."""

from typing import Any, Callable, Mapping, TypeVar

from flask import request
from werkzeug.exceptions import BadRequest

T = TypeVar("T")


class _Missing:
    pass


# ============================== Public Functions ============================== #


def get_param(key: str, coerce: Callable[[str], T], default: T = None) -> T:  # type: ignore[invalid-parameter-default]
    """Extract and coerce a query parameter from request args."""

    try:
        raw_value = request.args[key]
    except KeyError:
        return default

    if raw_value is None:
        return default

    return _coerce_value(raw_value, coerce)


def require_param(key: str, coerce: Callable[[str], T]) -> T:
    """Extract and coerce a query parameter from request args, raising BadRequest if missing or invalid."""
    value = get_param(key=key, coerce=coerce, default=_Missing())
    if isinstance(value, _Missing):
        raise BadRequest(f"Required parameter '{key}' is missing or invalid")
    return value


def get_json(key: str, coerce: Callable[[Any], T], default: T = None) -> T:  # type: ignore[invalid-parameter-default]
    """Extract and coerce a field from the JSON request body."""
    json_data = request.get_json()
    if not isinstance(json_data, Mapping):
        raise TypeError(
            f"Invalid JSON from request body, dictionary required - ({type(json_data)}) {json_data}"
        )

    try:
        raw_value = json_data[key]
    except KeyError:
        return default

    if raw_value is None:
        return default

    return _coerce_value(raw_value, coerce)


def require_json(key: str, coerce: Callable[[Any], T]) -> T:
    """Extract and coerce a field from the JSON request body, raising BadRequest if missing or invalid."""
    value = get_json(key=key, coerce=coerce, default=_Missing())
    if isinstance(value, _Missing):
        raise BadRequest(f"Required field '{key}' is missing or invalid")
    return value


# ============================== Helpers ============================== #


def _coerce_value(raw_value: Any, coerce: Callable[[Any], T]) -> T:
    """Coerce a raw value using the provided callable, with special handling for booleans."""

    if isinstance(raw_value, str):
        raw_value = raw_value.strip().replace("\r\n", "\n")

    if coerce is bool:
        if isinstance(raw_value, bool):
            return raw_value  # type: ignore
        if isinstance(raw_value, str):
            lower_value = raw_value.lower()
            if lower_value in ("true", "1", "yes", "on"):
                return True  # type: ignore
            elif lower_value in ("false", "0", "no", "off", ""):
                return False  # type: ignore
        return bool(raw_value)  # type: ignore

    return coerce(raw_value)
