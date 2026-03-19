from flask import render_template
from flask.typing import ResponseReturnValue
from sqlalchemy.orm import Session

from account.service import login_required
from core.app.blueprint import BaseBlueprint
from core.db.engine import use_db
from core.service.logger import get_logger

bp = BaseBlueprint("osm")
log = get_logger()


@bp.get("/map")
@login_required
@use_db
def map(db: Session) -> ResponseReturnValue:
    return render_template("index.html", title="SideQuest — Map")
