from typing import Any, Generator, TypeVar

from sqlalchemy import Select

SelectT = TypeVar("SelectT", bound=Select[tuple[Any, ...]])

type NameValueDict = dict[str, Any]
type NameValueDicts = list[NameValueDict]
type Yield[T] = Generator[T, None, None]
