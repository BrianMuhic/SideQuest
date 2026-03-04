import pytest
from flask.testing import FlaskClient
from sqlalchemy.orm import Session

from account.models import Role, User
from core.util.types import Yield

from tests.util import login, logout


class Constant:
    """TODO: DOCSTRING"""

    EMAIL = "email@test.com"
    PASSWORD = "password"
    BAD_PASSWORD = "invalid_password"
    FIRST_NAME = "John"
    LAST_NAME = "Doe"


@pytest.fixture(scope="module")
def constant() -> Yield[Constant]:
    """TODO: DOCSTRING"""
    yield Constant()


@pytest.fixture(scope="function")
def user(db: Session, constant: Constant) -> Yield[User]:
    """TODO: DOCSTRING"""
    user = User(
        email=constant.EMAIL,
        first_name=constant.FIRST_NAME,
        last_name=constant.LAST_NAME,
        role=Role.USER,
    )
    user.set_password(constant.PASSWORD)
    user.add(db, flush=True)
    yield user


@pytest.fixture(scope="function")
def user_client(
    client: FlaskClient,
    constant: Constant,
    user: User,
) -> Yield[FlaskClient]:
    """TODO: DOCSTRING"""
    login(client, user.email, constant.PASSWORD)
    yield client
    logout(client)
