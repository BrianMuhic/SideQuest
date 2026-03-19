from typing import Any, TypeVar

from sqlalchemy import (
    ColumnElement,
    ColumnExpressionArgument,
    Executable,
    Inspector,
    Select,
    exists,
    func,
    or_,
    select,
    text,
)
from sqlalchemy.orm import InstrumentedAttribute, Session

from core.db.base_model import Base
from core.db.engine import get_engine

T = TypeVar("T", bound="Base")
U = TypeVar("U")


def count(db: Session, selection: Select[Any]) -> int:
    """Return the number of records in the selection."""
    selection = select(func.count()).select_from(selection.subquery())
    return db.scalar(selection) or 0


def db_count(db: Session, model: type[Base], *condition: ColumnElement[bool]) -> int:
    """Return the count of records in a model table matching the optional conditions."""
    selection = select(func.count()).select_from(model)
    if condition:
        selection = selection.where(*condition)
    return db.scalar(selection) or 0


def db_sum(db: Session, field: ColumnElement[Any], *condition: ColumnElement[bool]) -> int:
    """Return the sum of a field for records matching the optional conditions."""
    selection = select(func.sum(field))
    if condition:
        selection = selection.where(*condition)
    return db.scalar(selection) or 0


def exists_where(db: Session, *clause: ColumnExpressionArgument[bool]) -> bool:
    """Returns whether a record exists that meets the specified clauses."""
    selection = select(exists().where(*clause))
    return bool(db.scalar(selection))


def ne(field: InstrumentedAttribute[U | None], value: U | None) -> ColumnElement[bool]:
    """
    Safely compare a nullable field to value.
    If field is Null, simply asking != will return False.
    """
    if value is None:
        return field.is_not(None)
    return or_(field.is_(None), field != value)


def bulk_execute(db: Session, statement: Executable) -> None:
    """Execute a statement without synchronizing the session (faster for bulk operations)."""
    db.execute(statement.execution_options(synchronize_session=False))


def create_record(model: type[T], src: Base | dict[str, Any], set_id: bool = False) -> T:
    """
    Create a new instance of a model class from an existing record.

    Args:
        model: The target model class to instantiate
        src: The source record to copy field values from
        set_id: If True, include the id field in the copy; if False, exclude it to allow
            database auto-generation of a new id

    Returns:
        A new instance of model with field values copied from src
    """

    data = src if isinstance(src, dict) else dict(src.__dict__)
    if not set_id:
        data.pop("id", None)

    fields = {k: v for k, v in data.items() if not k.startswith("_")}
    return model(**fields)


# ============================== Admin Helpers ============================== #


def create_all_tables() -> None:
    """Create all tables in the database."""
    engine = get_engine()
    Base.metadata.create_all(engine)


def drop_all_tables() -> None:
    """Drop all tables from the database."""
    engine = get_engine()
    Base.metadata.drop_all(engine)


def drop_table(table: Any) -> None:
    """Drop a specific table."""
    engine = get_engine()
    inspector = Inspector.from_engine(engine)
    if table.__tablename__ in inspector.get_table_names():
        table.__table__.drop(engine)


def get_table_sizes(db: Session) -> list[tuple[str, str, str]]:
    """
    Get the size of all tables in the database.

    Returns a list of tuples containing (table_name, size_mb, num_records).
    """

    query = text("""
        SELECT
            table_name,
            ROUND(((data_length + index_length) / 1024 / 1024), 2) AS size_mb,
            table_rows
        FROM information_schema.TABLES
        WHERE table_schema = DATABASE()
        ORDER BY (data_length + index_length) DESC
    """)

    return [
        (str(table_name), f"{table_size_mb:.3f}", str(table_records))
        for table_name, table_size_mb, table_records in db.execute(query)
    ]
