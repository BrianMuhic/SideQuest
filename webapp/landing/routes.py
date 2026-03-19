from flask import render_template
from flask.typing import ResponseReturnValue

from account.service import guest_required
from core.app.blueprint import BaseBlueprint
from core.service.logger import get_logger

bp = BaseBlueprint("landing", url_prefix="/")
log = get_logger()


@bp.get("")
@guest_required
def index() -> ResponseReturnValue:
    """Landing page with login and sign up."""
    return render_template("landing.html", title="SideQuest — Log In")
