from dataclasses import InitVar, dataclass, field
from typing import Any, Sequence

from typing_extensions import Self

from core.app.endpoint import Endpoint


@dataclass
class Menu:
    """
    Menu item that either links to an endpoint OR contains submenus.
    """

    name: str

    endpoint: InitVar[Endpoint | str | None] = None  # Input parameter
    endpoint_name: str | None = field(init=False, default=None)
    endpoint_args: dict[str, Any] = field(default_factory=dict)
    submenus: Sequence[Self] = field(default_factory=tuple)

    icon: str | None = None
    image: str | None = None
    active_flag: str = ""
    hide: bool = False

    def __post_init__(self, endpoint: Endpoint | str | None) -> None:
        """Convert Endpoint to string and validate menu configuration."""
        # Convert Endpoint to string if needed
        if isinstance(endpoint, Endpoint):
            self.endpoint_name = endpoint.route
        else:
            self.endpoint_name = endpoint

        # Validate that either endpoint or submenus is provided
        if not self.endpoint_name and not self.submenus:
            raise ValueError(f"Menu '{self.name}' must have either an endpoint or submenus")
        if self.endpoint_name and self.submenus:
            raise ValueError(f"Menu '{self.name}' cannot have both endpoint and submenus")


class Navbar:
    def __init__(
        self,
        left_menus: Sequence[Menu] = tuple(),
        right_menus: Sequence[Menu] = tuple(),
    ) -> None:
        self.left_menus = left_menus
        self.right_menus = right_menus

    def __call__(
        self,
        active_menu: Menu | None = None,
    ) -> Self:
        for menu in self.left_menus:
            menu.active_flag = "active" if menu is active_menu else ""
        for menu in self.right_menus:
            menu.active_flag = "active" if menu is active_menu else ""
        return self

    def find(self, menu_name: str) -> Menu | None:
        for menu in (*self.left_menus, *self.right_menus):
            for submenu in menu.submenus or []:
                if submenu.name == menu_name:
                    return submenu
            if menu.name == menu_name:
                return menu
        return None
