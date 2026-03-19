import pytest
from flask.testing import FlaskClient
from sqlalchemy.orm import Session

from account.models import User
from core.util.types import Yield

from tests.util import login, logout


class Constant:
    """TODO: DOCSTRING"""

    USERNAME = "gg4fellas"
    PASSWORD = "password!1$"
    BAD_PASSWORD = "invalid_password"


@pytest.fixture(scope="module")
def constant() -> Yield[Constant]:
    """TODO: DOCSTRING"""
    yield Constant()


@pytest.fixture(scope="function")
def user(db: Session, constant: Constant) -> Yield[User]:
    """TODO: DOCSTRING"""
    user = User(
        username=constant.USERNAME,
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
    login(client, user.username, constant.PASSWORD)
    yield client
    logout(client)
