"""
Core routing for the webapp. This should be routing only,
and call functionality from external modules.
"""

from enum import StrEnum
from typing import Any

from account.service import get_user
from core.app import endpoint
from core.service.logger import get_logger
from core.ui.navbar import Menu, Navbar

log = get_logger()


class NavbarType(StrEnum):
    GUEST = "guest"
    ADMIN = "admin"
    USER = "user"


NAVS: dict[NavbarType, Navbar] = {}


def init_navbars() -> None:
    # -------------------- Menus -------------------- #
    home_menu = Menu("", endpoint.home, icon="fas fa-home")

    guest_menu = Menu(
        "Account",
        submenus=(
            Menu("Login", endpoint.account_login),
            Menu("Sign Up", endpoint.account_register),
            Menu("Forgot Password", endpoint.account_forgot_password),
        ),
    )

    user_menu = Menu(
        "Account",
        submenus=(
            Menu("Profile", endpoint.account_edit_registration),
            Menu("Logout", endpoint.account_logout),
        ),
    )

    # -------------------- Navbars -------------------- #
    NAVS[NavbarType.GUEST] = Navbar(left_menus=(home_menu,), right_menus=(guest_menu,))
    NAVS[NavbarType.ADMIN] = Navbar(left_menus=(home_menu,), right_menus=(user_menu,))
    NAVS[NavbarType.USER] = Navbar(left_menus=(home_menu,), right_menus=(user_menu,))


def get_navbar(current_menu: Menu | None = None) -> Navbar:
    if not NAVS:
        init_navbars()

    kw: dict[str, Any] = dict(
        active_menu=current_menu,
    )

    user = get_user()

    if not user:
        return NAVS[NavbarType.GUEST](**kw)

    if user.is_admin:
        return NAVS[NavbarType.ADMIN](**kw)

    return NAVS[NavbarType.USER](**kw)
