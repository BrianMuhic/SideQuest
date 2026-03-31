from flask.testing import FlaskClient
from sqlalchemy.orm import Session

from account.models import User

from tests.fixtures.account import Constant as AccountConstant
from tests.util import login, logout, post

# ============================== Helpers ============================== #


def _assert_logged_in(client: FlaskClient) -> None:
    """Check if user is logged in by inspecting session"""
    with client.session_transaction() as session:
        assert "_user_id" in session


def _assert_not_logged_in(client: FlaskClient) -> None:
    """Check if user is not logged in by inspecting session"""
    with client.session_transaction() as session:
        assert "_user_id" not in session


def _login_successfully(
    client: FlaskClient,
    username: str = AccountConstant.USERNAME,
    password: str = AccountConstant.PASSWORD,
):
    """TODO: DOCSTRING"""
    login(client, username, password)
    _assert_logged_in(client)


def _login_unsuccessfully(
    client: FlaskClient,
    username: str = AccountConstant.USERNAME,
    password: str = AccountConstant.BAD_PASSWORD,
):
    """TODO: DOCSTRING"""
    post(
        client,
        "/account/login",
        {"username": username, "password": password},
        expect_fail=True,
    )
    _assert_not_logged_in(client)


def _logout_successfully(client: FlaskClient):
    """TODO: DOCSTRING"""
    logout(client)
    _assert_not_logged_in(client)


# ============================== Tests ============================== #


def test_logout_user(client: FlaskClient, user: User):
    """TODO: DOCSTRING"""
    _login_successfully(client, user.username)
    _logout_successfully(client)


def test_register_user_creates_db_record(client: FlaskClient, db: Session) -> None:
    username = "new_sidequest_user"
    payload = {
        "username": username,
        "password": "password123",
        "verify_password": "password123",
    }

    post(client, "/account/register", payload)
    _assert_logged_in(client)

    with client.session_transaction() as session:
        user_id = int(session["_user_id"])

    user = User.with_username(db, username)
    assert user is not None
    assert user.id == user_id


def test_login_requires_valid_password(client: FlaskClient, user: User) -> None:
    _login_unsuccessfully(client, user.username, AccountConstant.BAD_PASSWORD)
