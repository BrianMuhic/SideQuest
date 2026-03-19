"""
A base model used for interacting with the database.
All other models are assumed to subclass Base.
"""

from datetime import datetime, timezone
from functools import partial
from typing import Any, Iterable, Self, TypeVar

from sqlalchemy import ForeignKey, MetaData, ScalarResult, exists, select, text
from sqlalchemy.dialects.mysql import LONGBLOB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship
from werkzeug.exceptions import NotFound

from core.db.mapped_types import DateTimeNow, Int

T = TypeVar("T", bound="Base")


@compiles(LONGBLOB, "sqlite")
def compile_longblob_sqlite(_type, _compiler, **_kw) -> str:
    """Compile MySQL LONGBLOB as BLOB for SQLite compatibility."""
    return "BLOB"


class Base(DeclarativeBase):
    __abstract__ = True
    __allow_unmapped__ = True

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

    def __repr__(self) -> str:
        """Return string representation showing class name and ID."""
        return f"<{self.__class__.__name__} #{self.id}>"

    # --------------- Foreign Keys --------------- #
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

    # --------------- Relationships --------------- #
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

    @classmethod
    def secondary_relationship(
        cls: type[T],
        table_name: str,
        **kwargs,
    ) -> Mapped[list[T]]:
        return relationship(cls.__name__, secondary=table_name, **kwargs)

    # --------------- Getters --------------- #
    def to_dict(self) -> dict[str, Any]:
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
            raise NotFound(f"{cls.__name__} {id_} not found")
        return record

    @classmethod
    def all(cls, db: Session) -> list[Self]:
        """Return all records of this model."""
        return list(db.scalars(select(cls)))

    @classmethod
    def with_ids(cls, db: Session, ids: Iterable[int]) -> list[Self]:
        """Return records matching the given IDs."""
        return list(db.scalars(select(cls).where(cls.id.in_(ids))))

    @classmethod
    def these(cls, db: Session, ids: Iterable[int]) -> ScalarResult[Self]:
        """Return records matching the given IDs."""
        # FIXME: why name the function `these`?
        return db.scalars(select(cls).where(cls.id.in_(ids)))

    @classmethod
    def is_populated(cls, db: Session) -> bool:
        """Returns whether any records of cls exist."""
        return bool(db.scalar(select(exists(select(cls.id)))))

    # --------------- Setters --------------- #
    def add(self, db: Session, flush: bool = False) -> Self:
        """Add this record to the session, optionally flushing immediately."""
        db.add(self)
        if flush:
            self.flush(db)
        return self

    def flush(self, db: Session) -> Self:
        """Flush this record to the database without committing."""
        db.flush([self])
        return self

    def clone(self) -> Self:
        """Warning: Does not clone sub-records"""
        fields = self.to_dict()
        for f in {"id", "created_date", "modified_date"}:
            fields.pop(f, None)
        return self.__class__(**fields)

    @classmethod
    def delete(cls, db: Session, id_: int) -> None:
        """Delete a record by ID."""
        cls.__table__
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
    modified_date: DateTimeNow = mapped_column(onupdate=partial(datetime.now, timezone.utc))


# ============================== Relationship Helpers ============================== #
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
