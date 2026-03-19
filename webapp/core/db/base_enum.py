from enum import IntEnum
from typing import Iterable, Self

from werkzeug.exceptions import NotFound


class BaseEnum(IntEnum):
    @property
    def title(self) -> str:
        return super().name.replace("_", " ").title()

    def __str__(self) -> str:
        return self.title

    @classmethod
    def options(cls) -> dict[int, str]:
        return {x.value: x.title for x in cls}

    @classmethod
    def choices(
        cls,
        alphabetical: bool = False,
        include: Iterable[Self | int] | None = None,
        exclude: Iterable[Self | int] | None = None,
        default: tuple[int, str] | None = None,
        default_index: int = 0,
    ) -> list[tuple[int, str]]:
        sort_key = (lambda x: x[1]) if alphabetical else (lambda x: x[0])
        arr = sorted(((x.value, x.title) for x in cls), key=sort_key)

        if include is not None:
            include = set(include)
            arr = [x for x in arr if x[0] in include]
        if exclude is not None:
            exclude = set(exclude)
            arr = [x for x in arr if x[0] not in exclude]

        if default is not None:
            arr.insert(default_index, default)

        return arr

    @classmethod
    def with_title(cls, title: str) -> Self:
        for member in cls:
            if member.title == title:
                return member
        raise NotFound(f"No {cls.__name__.title()} with title '{title}'")
