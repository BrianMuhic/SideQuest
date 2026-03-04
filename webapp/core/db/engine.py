from contextlib import contextmanager
from functools import wraps
from timeit import default_timer
from typing import (
    Any,
    Callable,
    Concatenate,
    Generator,
    ParamSpec,
    TypeVar,
)

import sqlalchemy
from flask import g, request
from sqlalchemy.engine import Engine
from sqlalchemy.orm import (
    Session,
    sessionmaker,
)
from sqlalchemy.pool import StaticPool
from sqlalchemy_utils import create_database, database_exists

from core.service.logger import get_logger
from core.util.string import strip_digits

P = ParamSpec("P")
R = TypeVar("R")

log = get_logger()

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None
_testing: bool = False

# ==================== Sessions ==================== #


def get_request_session() -> Session:
    """Get or create a request-scoped database session."""
    if _session_factory is None:
        raise RuntimeError("Engine not initialized")

    if "db_session" not in g:
        g.db_session = _session_factory()
        g.db_session_start_time = default_timer()

    return g.db_session


def close_request_session(exception: BaseException | None = None) -> None:
    """Close the request-scoped database session."""
    session = g.pop("db_session", None)
    start_time = g.pop("db_session_start_time", None)

    if session is not None:
        try:
            if exception is None:
                session.commit()
            else:
                session.rollback()
        finally:
            session.close()

        if not _testing and start_time is not None:
            _log_slow_transactions(start_time)


@contextmanager
def db_session() -> Generator[Session, None, None]:
    """Context manager for read-write operations."""
    if _session_factory is None:
        raise RuntimeError("Engine not initialized")
    start_time = default_timer()
    session = _session_factory()

    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    if not _testing:
        _log_slow_transactions(start_time)


# ==================== Session Decorators ==================== #


def use_db(func: Callable[Concatenate[Session, P], R]) -> Callable[P, R]:
    """Decorator that provides a request-scoped database session."""

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        db = get_request_session()
        return func(db, *args, **kwargs)

    return wrapper


# ==================== Engine ==================== #


def init_engine(config_: Any) -> Engine:
    """Initialize the database engine and session factory."""
    global _engine, _session_factory, _testing

    _testing = config_.TESTING

    connection_str = config_.CONNECTION_STRING or connection_string(
        database=config_.ENGINE_DATABASE,
        host=config_.ENGINE_HOST,
        port=int(config_.ENGINE_PORT),
        user=config_.ENGINE_USER,
        password=config_.ENGINE_PASSWORD,
        dialect=config_.ENGINE_DIALECT,
        driver=config_.ENGINE_DRIVER,
        extras=config_.ENGINE_EXTRAS or "",
    )

    engine_kwargs = {
        "pool_pre_ping": True,
        "echo": False,
    }

    if _testing:
        engine_kwargs |= {
            "poolclass": StaticPool,
            "connect_args": {"check_same_thread": False},
        }
    else:
        engine_kwargs |= {
            "isolation_level": "READ COMMITTED",
            "pool_size": 20,
            "max_overflow": 10,
            "pool_recycle": 3600,
            "pool_timeout": 30,
            "pool_use_lifo": True,
        }

    _engine = sqlalchemy.create_engine(connection_str, **engine_kwargs)
    _session_factory = sessionmaker(
        bind=_engine,
        autoflush=True,
        expire_on_commit=False,
    )

    if not database_exists(_engine.url):
        create_database(_engine.url)

    return _engine


def connection_string(
    database: str,
    host: str,
    port: int,
    user: str,
    password: str,
    dialect: str,
    driver: str,
    extras: str,
) -> str:
    """Build a connection string from components."""
    return f"{dialect}+{driver}://{user}:{password}@{host}:{port}/{database}{extras}"


def get_engine() -> Engine:
    if _engine is None:
        raise RuntimeError("Engine not initialized")
    return _engine


# ==================== Monitoring ==================== #


def _log_slow_transactions(start_time: float) -> None:
    """Log slow database transactions."""
    from webapp.config import config

    dt = default_timer() - start_time
    if dt > config.DB_SESSION_TIME_WARN_THRESHOLD:
        route = strip_digits(request.path)
        if (
            dt > config.DB_SESSION_TIME_ERROR_THRESHOLD
            and route not in config.DB_SESSION_TIME_IGNORE
        ):
            log.e(f"DB Session too long: {route}\n\t{request.path} ({dt:0.3f}s)")
        else:
            log.w(f"DB Session too long: {request.path} ({dt:0.3f}s)")


def check_database(config_: Any) -> dict[str, Any]:
    """For running a health-check on the database."""
    db_status = 200

    try:
        if _engine is None:
            raise RuntimeError("Engine is not initialized")
        host = str(_engine.url.host)
        port = str(_engine.url.port)
        database = str(_engine.url.database)
        dialect = str(_engine.url.get_backend_name())
        db_message = f"Connection successful: {config_.ENGINE_HOST}:{config_.ENGINE_PORT}/{config_.ENGINE_DATABASE}"
    except Exception as err:
        db_status = 500
        db_message = f"Error occurred: {err}"
        host = port = database = dialect = ""

    return dict(
        message=db_message,
        status=db_status,
        host=host,
        port=port,
        database=database,
        dialect=dialect,
    )
