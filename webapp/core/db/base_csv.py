import csv
from typing import ClassVar, Iterable, Self

from sqlalchemy import func
from sqlalchemy.orm import mapped_column
from sqlalchemy.sql import Select, select

from core.db.base_model import Base, Session
from core.db.mapped_types import Str
from core.service.logger import get_logger

log = get_logger()


class BaseCsv(Base):
    __abstract__ = True
    csv_filename: ClassVar[str]
    name: Str = mapped_column(index=True)

    @classmethod
    def initialize(cls, db: Session) -> None:
        if cls.is_populated(db):
            log.d(f"Data already in {cls.__tablename__} table")
            return

        with open(f"webapp/csv/{cls.csv_filename}", encoding="utf-8-sig") as f:
            cls.populate_records(db, csv.reader(f))

    @classmethod
    def populate_records(cls, db: Session, rows: Iterable[list[str]]) -> None:
        for id_, name in rows:
            cls(
                id=int(id_),
                name=name.strip(),
            ).add(db)

    @classmethod
    def with_name(cls, name: str | None) -> Select[tuple[Self]]:
        name = (name or "").strip().lower()
        return select(cls).where(func.lower(cls.name) == name)

    @classmethod
    def names(cls, db: Session, use_title: bool = True) -> dict[str, str]:
        return {name: name.title() if use_title else name for name in db.scalars(select(cls.name))}
