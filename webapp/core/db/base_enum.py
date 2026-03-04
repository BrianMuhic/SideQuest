from enum import IntEnum
from typing import Self, Sequence

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
        blank: bool = False,
        other: bool = False,
        include: Sequence[Self | int] | None = None,
        exclude: Sequence[Self | int] | None = None,
    ) -> list[tuple[int, str]]:
        arr = [(x.value, x.title) for x in cls]

        if include:
            arr = [x for x in arr if x[0] in include]
        if exclude:
            arr = [x for x in arr if x[0] not in exclude]

        if alphabetical:
            arr.sort(key=lambda x: x[1])

        if blank:
            arr.insert(0, (0, ""))
        elif other:
            arr.insert(0, (0, "Other"))

        return arr

    @classmethod
    def with_title(cls, title: str) -> Self:
        for member in cls:
            if member.title == title:
                return member
        raise NotFound(f"No {cls.__name__.title()} with title '{title}'")
