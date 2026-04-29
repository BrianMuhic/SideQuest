import secrets
from functools import wraps
from typing import Any, Callable, cast

from flask import (
    session,
)
from flask.typing import ResponseReturnValue
from flask_login import (
    current_user,
    login_user,
    logout_user,
)
from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from werkzeug.exceptions import Forbidden, Unauthorized

from account.models import User
from config import config
from core.app import endpoint
from core.app.extensions import login_manager
from core.db.engine import use_db
from core.service.emailer import send_email
from core.service.logger import get_logger
from core.util.date import now_utc

log = get_logger()


# ============================== Login Manager ============================== #


@login_manager.user_loader
@use_db
def load_user(db: Session, user_id: int) -> User | None:
    """Get user record for login_manager."""
    selection = select(User).filter_by(id=user_id)
    return db.scalar(selection)


@login_manager.unauthorized_handler
def handle_unauthorized() -> ResponseReturnValue:
    """Called when a route uses @login_required from flask_login and not this file"""
    raise Unauthorized


def get_user() -> User | None:
    """Get current logged-in user or None if not authenticated."""
    if current_user.is_authenticated:
        return cast(User, current_user)
    return None


def get_user_by_login(db, login):
    return db.scalar(select(User).where(or_(User.username == login, User.email == login)))


def require_user() -> User:
    """Get current logged-in user.

    Raises:
        Unauthorized: If the user is not authenticated
    """
    user = get_user()
    if not user:
        raise Unauthorized
    return user


def guest_required(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator to require unauthenticated users for a view function.

    Ensures that the current user is NOT authenticated before allowing access
    to the decorated view. If the user is authenticated, redirect them to the index page.

    Example::

        @app.route("/register")
        @guest_required
        def user_register():
            return render_template("register.html")
    """

    @wraps(func)
    def decorated_function(*args, **kwargs):
        if get_user():
            return endpoint.index.redirect()
        return func(*args, **kwargs)

    return decorated_function


def login_required(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator to require user authentication for a view function.

    Ensures that the current user is authenticated before allowing access
    to the decorated view. If the user is not authenticated, raises an
    Unauthorized (401) exception which should be handled by app error handlers.

    Raises:
        Unauthorized: If the user is not authenticated

    Example::

        @app.route("/profile")
        @login_required
        def user_profile():
            return render_template("profile.html")
    """

    @wraps(func)
    def decorated_function(*args, **kwargs):
        require_user()
        return func(*args, **kwargs)

    return decorated_function


def admin_required(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Require admin privileges for a view function.

    Ensures that the current user is both authenticated and has admin
    privileges (user.admin == True) before allowing access to the decorated
    view. This decorator implies @login_required - you don't need both.

    Raises:
        Unauthorized: If the user is not authenticated
        Forbidden: If the user is authenticated but not an admin

    Example::

        @app.route("/admin/dashboard")
        @admin_required  # No need for @login_required
        def admin_dashboard():
            return render_template("admin_dashboard.html")
    """

    @wraps(func)
    def decorated_function(*args, **kwargs):
        user = require_user()

        # TODO: admin token

        if not user.is_admin:
            raise Forbidden

        return func(*args, **kwargs)

    return decorated_function


# ============================== Authentication ============================== #


def login(user: User) -> None:
    log.i(f"Login {user}")
    login_user(user=user, remember=False)

    user.last_login_at = now_utc()
    user.num_logins += 1


def logout() -> None:
    log.i(f"Logout {get_user()}")
    logout_user()


def user_session_timeout() -> None:
    """
    The session.permanent flag and the app.permanent_session_lifetime
    allow Flask to know that you want the session to expire.
    With just these two, the session will expire every 20 minutes
    regardless of whether the user has been active.

    Realistically you would want the session to expire after 20 minutes of inactivity,
    which is what the flask.session.modified flag is for.
    Each time there is a request the flag gets set to True which effectively resets the session timeout timer.

    Note: Flask-Login has a "remember me" functionality that is set at login time,
    Ensure that the flag is set to False or it will override the timeout.
        flask_login.login_user(user, remember=False)
    """

    session.permanent = True
    session.modified = True


# ============================== User Management ============================== #


def forgot_password(db: Session, login: str) -> None:

    user = get_user_by_login(db, login)

    if not user:
        return

    token = secrets.token_hex(16)
    user.access_token = token

    reset_link = f"{config.APP_URL}/account/reset_password/{token}"

    send_email(
        db=db,
        to=[user.email],
        subject="Reset your password",
        body=f"""
        Click the link to reset your password:
        {reset_link}
        """,
    )


def reset_password(db: Session, access_token: str, password: str) -> None:
    user = db.scalar(select(User).filter_by(access_token=access_token.strip()))

    if user is None:
        raise ValueError("Invalid or expired access token")

    log.i(f"Reset password for {user}")

    user.set_password(password)
    user.access_token = None


# def change_password(user: User, new_password: str) -> None:
#     user.set_password(new_password)
#     log.i(f"Change password for {user}")
