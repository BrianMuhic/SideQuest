from typing import Any

from flask_wtf import FlaskForm
from sqlalchemy.orm import Session
from wtforms import Field, SubmitField

from core.db.base_model import Base


class BaseForm(FlaskForm):
    submit = SubmitField("Submit")

    xfer_fields: list[Field]
    db: Session

    def __init__(self, db: Session = None, *args: Any, **kw: Any) -> None:  # type: ignore
        super().__init__(*args, **kw)
        self.xfer_fields = [
            field
            for field_name, field in self._fields.items()
            if field_name not in ("csrf_token", "submit")
        ]
        self.db = db

    @staticmethod
    def import_field(record: Base, field: Field) -> None:
        field.data = getattr(record, field.name)

    @staticmethod
    def export_field(record: Base, field: Field) -> None:
        setattr(record, field.name, field.data)

    def import_fields(self, record: Base) -> None:
        for field in self.xfer_fields:
            field.data = getattr(record, field.name)

    def export_fields(self, record: Base) -> None:
        for field in self.xfer_fields:
            setattr(record, field.name, field.data)
