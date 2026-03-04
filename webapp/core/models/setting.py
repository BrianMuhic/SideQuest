from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import JSON, select
from sqlalchemy.orm import Session, mapped_column

from constant import UTC_ZONEINFO
from core.db.base_model import BaseAudit
from core.db.mapped_types import Json, Str


class Setting(BaseAudit):
    __tablename__ = "settings"

    name: Str = mapped_column(unique=True)
    value: Json

    @classmethod
    def get(cls, db: Session, name: str, default: Any = None) -> Any:  # type: ignore
        setting = db.scalar(select(cls).filter_by(name=name))
        if setting is None:
            if default is not None:
                db.add(cls(name=name, value=cls._json_serialize(default)))
            return default
        value = cls._json_deserialize(setting.value)
        if value is None:
            if default is not None:
                setting.value = cls._json_serialize(default)
            return default

        return value

    @classmethod
    def set(cls, db: Session, name: str, data: Any) -> None:
        if data is None:
            return

        value = cls._json_serialize(data)
        if record := db.scalar(select(cls).filter_by(name=name)):
            record.value = value
        else:
            db.add(cls(name=name, value=value))

    @classmethod
    def _json_serialize(cls, obj: Any) -> JSON:
        return obj if isinstance(obj, dict) else dict(value=obj)  # type: ignore

    @classmethod
    def _json_deserialize(cls, json: JSON | None) -> Any:
        if json is None:
            return None

        if isinstance(json, (list, tuple)):
            return [cls._json_deserialize(item) for item in json]

        if not isinstance(json, dict):
            return json

        if all(key in json for key in ("month", "day")):
            year = json.get("year", datetime.now(UTC_ZONEINFO).year)
            month = json["month"]
            day = json["day"]

            if "hour" in json:
                hour = json["hour"]
                minute = json.get("minute", 0)
                second = json.get("second", 0)
                return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)

            return date(year, month, day)

        if "value" in json:
            return cls._json_deserialize(json["value"])

        return json or None
