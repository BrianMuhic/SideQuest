from flask.testing import FlaskClient

from account.models import User
from util import login, logout

from tests.fixtures.account import Constant as AccountConstant

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
    email: str = AccountConstant.EMAIL,
    password: str = AccountConstant.PASSWORD,
):
    """TODO: DOCSTRING"""
    login(client, email, password)
    _assert_logged_in(client)


def _login_unsuccessfully(
    client: FlaskClient,
    email: str = AccountConstant.EMAIL,
    password: str = AccountConstant.BAD_PASSWORD,
):
    """TODO: DOCSTRING"""
    login(client, email, password)
    _assert_not_logged_in(client)


def _logout_successfully(client: FlaskClient):
    """TODO: DOCSTRING"""
    logout(client)
    _assert_not_logged_in(client)


# ============================== Tests ============================== #


def test_logout_user(client: FlaskClient, user: User):
    """TODO: DOCSTRING"""
    _login_successfully(client, user.email)
    _logout_successfully(client)
