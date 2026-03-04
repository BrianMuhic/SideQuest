"""
See https://docs.sqlalchemy.org/en/20/orm/declarative_tables.html
"""

import decimal as d
import traceback
from datetime import (
    date,
    datetime,
    timezone,
)
from typing import (
    Annotated,
    Any,
    TypeAlias,
)

import sqlalchemy as sa
from sqlalchemy.dialects.mysql import LONGBLOB
from sqlalchemy.orm import Mapped, mapped_column

from core.service.logger import get_logger
from core.util.traceback import format_traceback

log = get_logger()


# ============================== Custom Types ============================== #
class _DateTimeUTC(sa.TypeDecorator):
    """Timezone-aware DateTime"""

    impl = sa.DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Any) -> datetime | None:
        """Validate datetime has timezone info before storing."""
        if value is None:
            return None

        if value.tzinfo is None:
            exc = Exception("Naive datetime saved to db, assuming UTC and continuing")
            tb = traceback.extract_stack()[:-1]
            log.e(format_traceback(exc, tb))
            return value.replace(tzinfo=timezone.utc)

        return value.astimezone(timezone.utc)

    def process_result_value(self, value: datetime | None, dialect: Any) -> datetime | None:
        """Add UTC tzinfo to naive datetime retrieved from database."""
        if value is None:
            return None

        if value.tzinfo is not None:
            return value.astimezone(timezone.utc)

        return value.replace(tzinfo=timezone.utc)


# ============================== Booleans ============================== #
# bool
Bool: TypeAlias = Mapped[Annotated[bool, mapped_column(sa.Boolean, nullable=False)]]
BoolTrue: TypeAlias = Mapped[
    Annotated[
        bool,
        mapped_column(sa.Boolean, nullable=False, default=True, server_default=sa.text("1")),
    ]
]
BoolFalse: TypeAlias = Mapped[
    Annotated[
        bool,
        mapped_column(sa.Boolean, nullable=False, default=False, server_default=sa.text("0")),
    ]
]
BoolNone: TypeAlias = Mapped[Annotated[bool | None, mapped_column(sa.Boolean, nullable=True)]]


# ============================== Numbers ============================== #
# int
Int: TypeAlias = Mapped[Annotated[int, mapped_column(sa.Integer, nullable=False)]]
IntZero: TypeAlias = Mapped[
    Annotated[
        int,
        mapped_column(sa.Integer, nullable=False, default=0, server_default=sa.text("0")),
    ]
]
IntNone: TypeAlias = Mapped[Annotated[int | None, mapped_column(sa.Integer, nullable=True)]]

BigInt: TypeAlias = Mapped[Annotated[int, mapped_column(sa.BigInteger, nullable=False)]]
BigIntZero: TypeAlias = Mapped[
    Annotated[
        int,
        mapped_column(sa.BigInteger, nullable=False, default=0, server_default=sa.text("0")),
    ]
]
BigIntNone: TypeAlias = Mapped[Annotated[int, mapped_column(sa.BigInteger, nullable=True)]]

# float (python stores floats as 64-bit, so sa.Double is needed)
Float: TypeAlias = Mapped[Annotated[float, mapped_column(sa.Double, nullable=False)]]
FloatNone: TypeAlias = Mapped[Annotated[float | None, mapped_column(sa.Double, nullable=True)]]

# Decimal
Decimal: TypeAlias = Mapped[Annotated[d.Decimal, mapped_column(sa.DECIMAL, nullable=False)]]
DecimalNone: TypeAlias = Mapped[
    Annotated[d.Decimal | None, mapped_column(sa.DECIMAL, nullable=True)]
]


# ============================== Dates ============================== #
# date
Date: TypeAlias = Mapped[Annotated[date, mapped_column(sa.Date, nullable=False)]]
DateToday: TypeAlias = Mapped[
    Annotated[
        date,
        mapped_column(
            sa.Date,
            nullable=False,
            default=lambda: datetime.now(timezone.utc).date(),
            server_default=sa.text("UTC_DATE"),
        ),
    ]
]
DateNone: TypeAlias = Mapped[Annotated[date | None, mapped_column(sa.Date, nullable=True)]]

# datetime
DateTime: TypeAlias = Mapped[Annotated[datetime, mapped_column(_DateTimeUTC, nullable=False)]]
DateTimeNow: TypeAlias = Mapped[
    Annotated[
        datetime,
        mapped_column(
            _DateTimeUTC,
            nullable=False,
            default=lambda: datetime.now(timezone.utc),
            server_default=sa.text("UTC_TIMESTAMP"),
        ),
    ]
]
DateTimeNone: TypeAlias = Mapped[
    Annotated[datetime | None, mapped_column(_DateTimeUTC, nullable=True)]
]


# ============================== Strings ============================== #
# str
Str: TypeAlias = Mapped[Annotated[str, mapped_column(sa.String(256), nullable=False)]]
StrEmpty: TypeAlias = Mapped[
    Annotated[
        str,
        mapped_column(sa.String(256), nullable=False, default="", server_default=sa.text("''")),
    ]
]
StrNone: TypeAlias = Mapped[Annotated[str | None, mapped_column(sa.String(256), nullable=True)]]

StrLong: TypeAlias = Mapped[Annotated[str, mapped_column(sa.String(1024), nullable=False)]]
StrLongEmpty: TypeAlias = Mapped[
    Annotated[
        str,
        mapped_column(sa.String(1024), nullable=False, default="", server_default=sa.text("''")),
    ]
]
StrLongNone: TypeAlias = Mapped[
    Annotated[str | None, mapped_column(sa.String(1024), nullable=True)]
]

# str (Text)
Text: TypeAlias = Mapped[Annotated[str, mapped_column(sa.Text, nullable=False)]]
TextEmpty: TypeAlias = Mapped[
    Annotated[
        str,
        mapped_column(sa.Text, nullable=False, default="", server_default=sa.text("''")),
    ]
]
TextNone: TypeAlias = Mapped[Annotated[str | None, mapped_column(sa.Text, nullable=True)]]


# ==================== Misc. Types ==================== #
# bytes
MB = 2**20
Bytes: TypeAlias = Mapped[Annotated[bytes, mapped_column(LONGBLOB, nullable=False, deferred=True)]]
BytesNone: TypeAlias = Mapped[
    Annotated[bytes | None, mapped_column(LONGBLOB, nullable=True, deferred=True)]
]

# Any (json)
Json: TypeAlias = Mapped[Annotated[Any, mapped_column(sa.JSON, nullable=False)]]
JsonNone: TypeAlias = Mapped[Annotated[Any | None, mapped_column(sa.JSON, nullable=True)]]
