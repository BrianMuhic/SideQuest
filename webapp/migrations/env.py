import importlib
from pathlib import Path
from typing import Any, Literal

from alembic import context
from alembic.autogenerate.api import AutogenContext
from alembic.runtime.migration import MigrationContext
from sqlalchemy import Column, Engine, Enum
from sqlalchemy.types import TypeEngine
from sqlalchemy_utils import create_database, database_exists

from config import config
from core.db.base_model import Base
from core.db.engine import init_engine
from core.service.logger import config_logger, set_log_level

# ============================== Import Models ============================== #

webapp_dir = Path(__file__).parent.parent
app_modules = [d.name for d in webapp_dir.iterdir() if d.is_dir() and not d.name.startswith("_")]

for app_name in app_modules:
    app_dir = webapp_dir / app_name
    models_file = app_dir / "models.py"
    models_dir = app_dir / "models"

    if models_file.exists():
        importlib.import_module(f"{app_name}.models")
    elif models_dir.exists():
        for model_file in models_dir.glob("*.py"):
            if model_file.stem != "__init__":
                module_path = f"{app_name}.models.{model_file.stem}"
                importlib.import_module(module_path)


# ============================== Migration Functions ============================== #


def create_database_if_not_exists(engine: Engine) -> bool:
    database_url = engine.url
    if not database_exists(database_url):
        print(f"Creating database {database_url}")
        create_database(database_url)
        return True
    return False


def render_item(_type_: str, obj: Any, _autogen_context: AutogenContext) -> str | Literal[False]:
    """Custom type rendering for Alembic autogenerate."""

    from core.db.mapped_types import _DateTimeUTC

    if _type_ != "type":
        return False

    mapping = {
        _DateTimeUTC: "sa.DateTime()",
    }

    return mapping.get(type(obj), False)


def compare_type(
    context: MigrationContext,
    inspected_column: Column[Any],
    metadata_column: Column[Any],
    inspected_type: TypeEngine[Any],
    metadata_type: TypeEngine[Any],
) -> bool | None:
    """
    Compare enum types to detect changes in enum values.

    Return False if types match, True if they differ, None for default comparison.
    """

    if isinstance(inspected_type, Enum) and isinstance(metadata_type, Enum):
        return set(inspected_type.enums) != set(metadata_type.enums)

    return None


# ============================== Run Migration ============================== #


def run_migrations():
    config_logger(config)
    set_log_level("INFO", "alembic")

    engine = init_engine(config)

    create_database_if_not_exists(engine)
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=Base.metadata,
            compare_type=compare_type,
            compare_server_default=True,
            render_item=render_item,
        )

        with context.begin_transaction():
            context.run_migrations()


run_migrations()
