import pytest
from flask import Flask
from flask.testing import FlaskClient

from config import config
from core.app.factory import create_app
from core.db.base_model import Base
from core.db.engine import db_session, init_engine
from core.util.types import Yield

pytest_plugins = [
    "fixtures.account",
]


@pytest.fixture(scope="session")
def app() -> Yield[Flask]:
    """TODO: DOCSTRING"""
    config.DEBUG = True
    config.TESTING = True
    config.WTF_CSRF_ENABLED = False

    config.IS_PRODUCTION = False
    config.MAIL_REDIRECT_TO_DEVELOPER = False

    yield create_app()


@pytest.fixture(scope="function")
def client(app: Flask) -> Yield[FlaskClient]:
    """Fresh Flask test client per test - avoids session/cookie leakage between tests."""
    with app.test_client() as client:
        yield client


def _initialize_database() -> None:
    """TODO: DOCSTRING"""
    # Do custom db initialization steps here
    with db_session() as _db:
        pass


@pytest.fixture(scope="function")
def db():
    """TODO: DOCSTRING"""
    with db_session() as session:
        yield session


@pytest.fixture(scope="function", autouse=True)
def reset_db(app: Flask) -> Yield[None]:
    """TODO: DOCSTRING"""
    engine = init_engine(app.config)
    Base.metadata.create_all(engine)
    _initialize_database()

    yield
    engine.dispose()
