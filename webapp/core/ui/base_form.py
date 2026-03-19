from http import HTTPStatus
from typing import Literal

from flask_wtf import FlaskForm
from sqlalchemy.orm import Session
from wtforms import SubmitField


class BaseForm(FlaskForm):
    submit = SubmitField("Submit")

    db: Session

    def __init__(self, db: Session = None, *args, **kw) -> None:  # type: ignore
        super().__init__(*args, **kw)
        self.db = db

    @property
    def status_code(self) -> Literal[HTTPStatus.OK, HTTPStatus.UNPROCESSABLE_ENTITY]:
        if self.errors:
            return HTTPStatus.UNPROCESSABLE_ENTITY
        return HTTPStatus.OK
