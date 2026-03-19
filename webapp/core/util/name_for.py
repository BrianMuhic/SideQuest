from typing import Protocol, TypeVar

from sqlalchemy.orm import Mapped

from core.db.base_csv import BaseCsv
from core.db.base_enum import BaseEnum

NameType = TypeVar("NameType", bound=str | None | Mapped[str] | Mapped[str | None])


class HasName(Protocol[NameType]):
    """Protocol for objects with a 'name' attribute that is string-like."""

    name: NameType


def name_for_any(obj: HasName | str | None, default: str = "") -> str:
    """
    Get name from any object with a string 'name' attribute.

    Returns:
    - `HasName => obj.name`
    - `str => obj`
    - `None => default`
    """
    if obj is None:
        return default
    if isinstance(obj, str):
        return obj

    value = obj.name
    if value is None:
        return default
    return value


def name_for(obj: BaseEnum | BaseCsv | str | None, default: str = "") -> str:
    """
    Convert enum-like objects to display strings with optional fallback.

    Returns:
    - `BaseEnum => obj.title`
    - `BaseCsv => obj.name`
    - `str => obj`
    - `None => default`

    For other object types with a 'name' attribute, use `name_for_any()`.
    """
    if obj is None:
        return default
    if isinstance(obj, BaseEnum):
        return obj.title
    if isinstance(obj, BaseCsv):
        return obj.name
    return obj
