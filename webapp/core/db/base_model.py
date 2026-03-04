"""
A base model used for interacting with the database.
All other models are assumed to subclass Base.
"""

from datetime import datetime, timezone
from functools import partial
from typing import (
    Any,
    Iterable,
    TypeVar,
)

from sqlalchemy import (
    ColumnElement,
    ForeignKey,
    MetaData,
    or_,
    select,
    text,
)
from sqlalchemy.dialects.mysql import LONGBLOB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import (
    DeclarativeBase,
    InstrumentedAttribute,
    Mapped,
    Session,
    mapped_column,
    relationship,
)
from sqlalchemy.sql import Executable, Select
from sqlalchemy.sql.functions import func
from typing_extensions import Self
from werkzeug.exceptions import NotFound

from core.db.mapped_types import DateTimeNow, Int

T = TypeVar("T", bound="Base")
U = TypeVar("U")


@compiles(LONGBLOB, "sqlite")
def compile_longblob_sqlite(_type, _compiler, **_kw) -> str:
    """Compile MySQL LONGBLOB as BLOB for SQLite compatibility."""
    return "BLOB"


class Base(DeclarativeBase):
    __abstract__ = True

    # Naming conventions for alembic migrations
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(table_name)s_%(column_0_name)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )

    id: Int = mapped_column(primary_key=True, autoincrement=True)

    def __init__(self, **kwargs) -> None:
        """Initialize model with keyword arguments as attributes."""
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __repr__(self) -> str:
        """Return string representation showing class name and ID."""
        return f"<{self.__class__.__name__} #{self.id}>"

    # ---------- Foreign Keys ---------- #
    @classmethod
    def _fk(
        cls, nullable: bool, index: bool = True, use_alter: bool = False, **kwargs
    ) -> Mapped[int]:
        """Create a foreign key to this model."""
        fk = ForeignKey(f"{cls.__tablename__}.id", use_alter=use_alter)
        return mapped_column(fk, nullable=nullable, index=index, **kwargs)

    @classmethod
    def fk(cls, **kwargs) -> Mapped[int]:
        """Create a foreign key to this model."""
        return cls._fk(nullable=False, **kwargs)

    @classmethod
    def fk_none(cls, **kwargs) -> Mapped[int | None]:
        """Create a nullable foreign key to this model."""
        return cls._fk(nullable=True, **kwargs)

    # ---------- Relationships ---------- #
    @classmethod
    def relationship(
        cls: type[T],
        fk: Mapped[int] | Mapped[int | None] | None = None,
        **kwargs,
    ) -> Mapped[T]:
        """Create a relationship to this model."""
        foreign_keys = [fk] if fk else None
        return relationship(cls.__name__, foreign_keys=foreign_keys, **kwargs)

    @classmethod
    def relationship_none(
        cls: type[T],
        fk: Mapped[int] | Mapped[int | None] | None = None,
        **kwargs,
    ) -> Mapped[T | None]:
        """Create a nullable relationship to this model."""
        return cls.relationship(fk=fk, **kwargs)

    # ---------- Getters ---------- #
    def as_data(self) -> dict[str, Any]:
        """Return all column values as a dictionary."""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    @classmethod
    def get(cls, db: Session, id_: int | None) -> Self | None:
        """Get a record by ID, returning None if not found."""
        if id_ is None:
            return None
        return db.get(cls, id_)

    @classmethod
    def get_one(cls, db: Session, id_: int | None) -> Self:
        """Get a record by ID, raising NotFound if not found."""
        record = cls.get(db, id_)
        if record is None:
            raise NotFound
        return record

    @classmethod
    def all(cls, db: Session) -> Iterable[Self]:
        """Return all records of this model."""
        return db.scalars(select(cls))

    @classmethod
    def is_populated(cls, db: Session) -> bool:
        """Returns whether any records of cls exist."""
        return db.scalar(select(cls.id)) is not None

    # ---------- Setters ---------- #
    def add(self, db: Session, flush: bool = False) -> Self:
        """Add this record to the session, optionally flushing immediately."""
        db.add(self)
        if flush:
            db.flush([self])
        return self

    def clone(self) -> Self:
        """Warning: Does not clone sub-records"""
        return self.__class__(**self.as_data())

    def flush(self, db: Session) -> Self:
        """Flush this record to the database without committing."""
        db.flush([self])
        return self

    @classmethod
    def delete(cls, db: Session, id_: int) -> None:
        """Delete a record by ID."""
        record = cls.get_one(db, id_)
        db.delete(record)

    @classmethod
    def truncate(cls, db: Session) -> None:
        """Delete all records from this table (TRUNCATE)."""
        command = f"TRUNCATE TABLE {cls.__tablename__}"
        with db.begin():
            db.execute(text(command))


class BaseAudit(Base):
    __abstract__ = True

    created_date: DateTimeNow
    modified_date: DateTimeNow = mapped_column(
        onupdate=partial(datetime.now, timezone.utc),
    )


# ==================== Relationship Helpers ==================== #
# Prevents circular dependencies until we find a better solution
def fk_to(
    table_name: str,
    nullable: bool = False,
    index: bool = True,
    use_alter: bool = False,
    **kwargs,
) -> Mapped:
    """Create a foreign key to a specific table."""
    fk = ForeignKey(f"{table_name}.id", use_alter=use_alter)
    return mapped_column(fk, nullable=nullable, index=index, **kwargs)


def relationship_to(
    model_name: str, fk: Mapped[int] | Mapped[int | None] | None = None, **kwargs
) -> Mapped:
    """Create a relationship to another model."""
    foreign_keys = [fk] if fk else None
    return relationship(model_name, foreign_keys=foreign_keys, **kwargs)


# ============================== Helpers ============================== #


def count(db: Session, query: Select[Any]) -> int:
    """Return the number of records in the query"""
    statement = select(func.count()).select_from(query.subquery())
    result = db.execute(statement).scalar()
    return result if result is not None else 0


def bulk_execute(db: Session, statement: Executable) -> None:
    """Execute a statement without synchronizing the session (faster for bulk operations)."""
    db.execute(statement.execution_options(synchronize_session=False))


def ne(nullable_field: InstrumentedAttribute[U], value: U | None) -> ColumnElement[bool]:
    """
    Safely compare a nullable field to value.
    If field is Null, simply asking != will return False.
    """
    if value is None:
        return nullable_field.isnot(None)
    return or_(nullable_field.is_(None), nullable_field != value)


def create_record(model_class: type[T], src_record: Base, set_id: bool = False) -> T:
    """
    Create a new instance of a model class from an existing record.

    Args:
        model_class: The target model class to instantiate
        src_record: The source record to copy field values from
        set_id: If True, include the id field in the copy; if False, exclude it to allow
            database auto-generation of a new id

    Returns:
        A new instance of model_class with field values copied from src_record
    """

    fields = {
        k: v
        for k, v in src_record.__dict__.items()
        if not k.startswith("_") and (set_id or k != "id")
    }
    return model_class(**fields)
