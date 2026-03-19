"""
See https://docs.sqlalchemy.org/en/20/orm/declarative_tables.html
"""

import decimal as d
import traceback
from datetime import date, datetime, timezone
from typing import Annotated, Any

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
Bool = Mapped[Annotated[bool, mapped_column(sa.Boolean, nullable=False)]]
BoolTrue = Mapped[
    Annotated[
        bool,
        mapped_column(sa.Boolean, nullable=False, default=True, server_default=sa.text("1")),
    ]
]
BoolFalse = Mapped[
    Annotated[
        bool,
        mapped_column(sa.Boolean, nullable=False, default=False, server_default=sa.text("0")),
    ]
]
BoolNone = Mapped[Annotated[bool | None, mapped_column(sa.Boolean, nullable=True)]]


# ============================== Numbers ============================== #
# int
Int = Mapped[Annotated[int, mapped_column(sa.Integer, nullable=False)]]
IntZero = Mapped[
    Annotated[
        int,
        mapped_column(sa.Integer, nullable=False, default=0, server_default=sa.text("0")),
    ]
]
IntNone = Mapped[Annotated[int | None, mapped_column(sa.Integer, nullable=True)]]

BigInt = Mapped[Annotated[int, mapped_column(sa.BigInteger, nullable=False)]]
BigIntZero = Mapped[
    Annotated[
        int,
        mapped_column(sa.BigInteger, nullable=False, default=0, server_default=sa.text("0")),
    ]
]
BigIntNone = Mapped[Annotated[int, mapped_column(sa.BigInteger, nullable=True)]]

# float (python stores floats as 64-bit, so sa.Double is needed)
Float = Mapped[Annotated[float, mapped_column(sa.Double, nullable=False)]]
FloatNone = Mapped[Annotated[float | None, mapped_column(sa.Double, nullable=True)]]

# Decimal
Decimal = Mapped[Annotated[d.Decimal, mapped_column(sa.DECIMAL, nullable=False)]]
DecimalNone = Mapped[Annotated[d.Decimal | None, mapped_column(sa.DECIMAL, nullable=True)]]


# ============================== Dates ============================== #
# date
Date = Mapped[Annotated[date, mapped_column(sa.Date, nullable=False)]]
DateToday = Mapped[
    Annotated[
        date,
        mapped_column(
            sa.Date,
            nullable=False,
            default=lambda: datetime.now(timezone.utc).date(),
            server_default=sa.text("utc_date()"),
        ),
    ]
]
DateNone = Mapped[Annotated[date | None, mapped_column(sa.Date, nullable=True)]]

# datetime
DateTime = Mapped[Annotated[datetime, mapped_column(_DateTimeUTC, nullable=False)]]
DateTimeNow = Mapped[
    Annotated[
        datetime,
        mapped_column(
            _DateTimeUTC,
            nullable=False,
            default=lambda: datetime.now(timezone.utc),
            server_default=sa.text("utc_timestamp()"),
        ),
    ]
]
DateTimeNone = Mapped[Annotated[datetime | None, mapped_column(_DateTimeUTC, nullable=True)]]


# ============================== Strings ============================== #
# str
Str = Mapped[Annotated[str, mapped_column(sa.String(256), nullable=False)]]
StrEmpty = Mapped[
    Annotated[
        str,
        mapped_column(sa.String(256), nullable=False, default="", server_default=sa.text("''")),
    ]
]
StrNone = Mapped[Annotated[str | None, mapped_column(sa.String(256), nullable=True)]]

StrLong = Mapped[Annotated[str, mapped_column(sa.String(1024), nullable=False)]]
StrLongEmpty = Mapped[
    Annotated[
        str,
        mapped_column(sa.String(1024), nullable=False, default="", server_default=sa.text("''")),
    ]
]
StrLongNone = Mapped[Annotated[str | None, mapped_column(sa.String(1024), nullable=True)]]

# str (Text)
Text = Mapped[Annotated[str, mapped_column(sa.Text, nullable=False)]]
TextEmpty = Mapped[
    Annotated[
        str,
        mapped_column(sa.Text, nullable=False, default="", server_default=sa.text("''")),
    ]
]
TextNone = Mapped[Annotated[str | None, mapped_column(sa.Text, nullable=True)]]


# ==================== Misc. Types ==================== #
# bytes
MB = 2**20
Bytes = Mapped[Annotated[bytes, mapped_column(LONGBLOB, nullable=False, deferred=True)]]
BytesNone = Mapped[Annotated[bytes | None, mapped_column(LONGBLOB, nullable=True, deferred=True)]]

# Any (json)
Json = Mapped[Annotated[Any, mapped_column(sa.JSON, nullable=False)]]
JsonNone = Mapped[Annotated[Any | None, mapped_column(sa.JSON, nullable=True)]]
