import csv
from typing import Any, ClassVar, Iterable, Self

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
        with open(f"webapp/csv/{cls.csv_filename}", encoding="utf-8-sig") as f:
            cls.populate_records(db, csv.reader(f))

    @classmethod
    def populate_records(cls, db: Session, rows: Iterable[list[str]]) -> None:
        """
        Sync database records with CSV data.
        - Updates existing records if values differ
        - Adds new records from CSV
        - Deletes records not in CSV
        """
        # Convert rows to dict for easy lookup by ID
        csv_data = {data["id"]: data for data in (cls.row_data(row) for row in rows)}
        csv_ids = set(csv_data.keys())

        # Get all existing records
        existing_records = {record.id: record for record in db.scalars(select(cls)).all()}
        existing_ids = set(existing_records.keys())

        # Update existing records if values differ
        updated_count = 0
        for id_ in csv_ids & existing_ids:
            record = existing_records[id_]
            new_data = csv_data[id_]
            # Check if any field has changed
            if any(getattr(record, key) != value for key, value in new_data.items()):
                for key, value in new_data.items():
                    setattr(record, key, value)
                updated_count += 1

        # Add new records
        added_ids = csv_ids - existing_ids
        for id_ in added_ids:
            cls(**csv_data[id_]).add(db)

        # Delete records not in CSV
        deleted_ids = existing_ids - csv_ids
        for id_ in deleted_ids:
            db.delete(existing_records[id_])

        if updated_count or added_ids or deleted_ids:
            log.info(
                f"{cls.__name__}: updated {updated_count}, added {len(added_ids)}, deleted {len(deleted_ids)}"
            )

    @classmethod
    def row_data(cls, row: list[str]) -> dict[str, Any]:
        """
        Convert a CSV row to a dictionary for record creation/update.
        Override this method in subclasses to handle additional fields.
        """
        id_, name = row
        return dict(
            id=int(id_),
            name=name.strip(),
        )

    @classmethod
    def with_name(cls, name: str | None) -> Select[tuple[Self]]:
        name = (name or "").strip().lower()
        return select(cls).where(func.lower(cls.name) == name)

    @classmethod
    def names(cls, db: Session, use_title: bool = True) -> dict[str, str]:
        return {name: name.title() if use_title else name for name in db.scalars(select(cls.name))}

    @classmethod
    def choices(
        cls,
        db: Session,
        alphabetical: bool = True,
        use_title: bool = False,
        include: Iterable[int] | None = None,
        exclude: Iterable[int] | None = None,
        default: tuple[int, str] | None = None,
        default_index: int = 0,
    ) -> list[tuple[int, str]]:
        sort_col = cls.id if not alphabetical else cls.name
        selection = select(cls.id, cls.name).order_by(sort_col.asc())

        if include is not None:
            selection = selection.where(cls.id.in_(set(include)))
        if exclude is not None:
            selection = selection.where(cls.id.not_in(set(exclude)))

        arr = [(id_, name.title() if use_title else name) for id_, name in db.execute(selection)]

        if default is not None:
            arr.insert(default_index, default)

        return arr
