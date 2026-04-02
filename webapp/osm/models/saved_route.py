from sqlalchemy import select
from sqlalchemy.orm import Session

from core.db.base_model import BaseAudit, fk_to, relationship_to
from core.db.mapped_types import Float, Int, Json, Str


class SavedRoute(BaseAudit):
    __tablename__ = "saved_routes"

    user_id: Int = fk_to("users")
    user = relationship_to("User", fk=user_id)

    name: Str
    start_name: Str
    start_lat: Float
    start_lon: Float
    end_name: Str
    end_lat: Float
    end_lon: Float
    stops: Json
    route_geojson: Json
    total_distance_miles: Float
    total_duration_minutes: Int

    @classmethod
    def for_user(cls, db: Session, user_id: int) -> list["SavedRoute"]:
        selection = select(cls).where(cls.user_id == user_id).order_by(cls.created_date.desc())
        return list(db.scalars(selection))
