import typing as t

import sqlalchemy as sa

SelectT = t.TypeVar("SelectT", bound=sa.Select[tuple[t.Any, ...]])

type NameValueDict = dict[str, t.Any]
type NameValueDicts = list[NameValueDict]
type Yield[T] = t.Generator[T, None, None]
