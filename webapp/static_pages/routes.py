from dataclasses import dataclass

from flask.templating import render_template
from flask.typing import ResponseReturnValue

from account.service import admin_required, login_required
from core.app import endpoint
from core.app.custom_blueprint import CustomBlueprint
from core.app.endpoint import Endpoint
from core.service.logger import get_logger

log = get_logger()

bp = CustomBlueprint(
    "static",
    __name__,
)


@dataclass
class Page:
    route: str  # Route for static page
    file: str  # HTML filename
    title: str  # Title to pass to template
    login: bool = False  # Login required to view page
    admin: bool = False  # Admin required to view page


PAGES = (Page("/", "index.html", "Flask Template"),)


def _register_page(page: Page) -> None:
    def page_handler() -> ResponseReturnValue:
        return render_template(
            page.file,
            title=page.title,
        )

    view_func = page_handler
    if page.admin:
        view_func = admin_required(page_handler)
    elif page.login:
        view_func = login_required(page_handler)

    name = page.route[1:].replace("/", "_").replace("-", "_") or "home"
    bp.add_url_rule(rule=page.route, endpoint=name, view_func=view_func)
    endpoint.add_variable_to_module(name, Endpoint(name, bp.name))


for page in PAGES:
    _register_page(page)
