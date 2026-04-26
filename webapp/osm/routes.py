import json
from http import HTTPStatus
from typing import Any

from flask import render_template
from flask.typing import ResponseReturnValue
from sqlalchemy.orm import Session
from werkzeug import Response
from werkzeug.exceptions import BadRequest, NotFound

from account import service as account_service
from account.service import login_required
from core.app.blueprint import BaseBlueprint
from core.db.engine import use_db
from core.util.request_params import get_json, get_param, require_json
from osm import service

bp = BaseBlueprint("osm")


@bp.get("/")
def home() -> ResponseReturnValue:
    return render_template("index.html", title="SideQuest")


# ============================== API ============================== #

_CACHE_HEADER = "public, max-age=3600"
_NO_CACHE_HEADER = "no-store, no-cache, must-revalidate, max-age=0"


def _api_response(
    content: Any, status: int = HTTPStatus.OK, cache: bool = True
) -> ResponseReturnValue:
    headers = {
        "Content-Type": "application/json",
        "Cache-Control": _CACHE_HEADER if cache else _NO_CACHE_HEADER,
    }
    return Response(
        response=json.dumps(content),
        status=status,
        headers=headers,
    )


def get_stop_image(category: str | None) -> str:
    category = (category or "").lower()

    if "coffee" in category or "cafe" in category:
        return "https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?auto=format&fit=crop&w=900&q=80"

    if "restaurant" in category or "food" in category:
        return "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?auto=format&fit=crop&w=900&q=80"

    if "park" in category or "hike" in category or "trail" in category:
        return "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=900&q=80"

    if "museum" in category:
        return "https://images.unsplash.com/photo-1565060169187-6f5f06e1f3ec?auto=format&fit=crop&w=900&q=80"

    if "attraction" in category or "landmark" in category:
        return "https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?auto=format&fit=crop&w=900&q=80"

    if "shopping" in category or "store" in category:
        return "https://images.unsplash.com/photo-1441986300917-64674bd600d8?auto=format&fit=crop&w=900&q=80"

    if "hotel" in category or "lodging" in category:
        return "https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=900&q=80"

    return "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=900&q=80"


def add_stop_images(stops: list[dict[str, Any]]) -> list[dict[str, Any]]:
    updated_stops = []

    for stop in stops:
        updated_stop = dict(stop)

        category = (
            updated_stop.get("category")
            or updated_stop.get("type")
            or updated_stop.get("amenity")
            or updated_stop.get("tourism")
            or ""
        )

        if not updated_stop.get("image_url"):
            updated_stop["image_url"] = get_stop_image(str(category))

        updated_stops.append(updated_stop)

    return updated_stops


@bp.post("/api/find-stops")
def find_stops() -> ResponseReturnValue:
    start_location = require_json("start_location", str)
    end_location = require_json("end_location", str)
    stop_categories = get_json("stop_categories", list, [])
    detour_hours = get_json("allowed_detour_hours", int, 0)
    detour_minutes = get_json("allowed_detour_minutes", int, 0)

    total_detour_minutes = (detour_hours * 60) + detour_minutes
    stage = get_json("stage", str, "full")

    stops, route_geojson = service.find_stops(
        start_location,
        end_location,
        stop_categories,
        total_detour_minutes,
        quick=(stage == "quick"),
    )

    stops = add_stop_images(stops)

    data = {
        "stops": stops,
        "route_geojson": route_geojson,
        "allowed_detour_text": service.friendly_detour_text(detour_hours, detour_minutes),
    }

    return _api_response(data, cache=False)


@bp.post("/api/route-legs")
def route_legs() -> ResponseReturnValue:
    waypoints = require_json("waypoints", list)

    if len(waypoints) < 2:
        raise BadRequest("At least two waypoints are required.")

    try:
        data = service.get_route_legs(waypoints)
    except ValueError as e:
        raise NotFound(str(e))

    return _api_response(data, cache=False)


@bp.get("/api/location-suggestions")
def location_suggestions() -> ResponseReturnValue:
    query = get_param("q", str, "")

    if len(query) < 3:
        return _api_response([], cache=False)

    return _api_response(service.get_location_suggestions(query), cache=False)


@bp.get("/api/place-photo")
def place_photo() -> ResponseReturnValue:
    photo_name = get_param("name", str, "")

    if not photo_name:
        raise BadRequest("Photo name is required.")

    try:
        image_bytes, content_type = service.get_google_place_photo(photo_name)
    except ValueError as e:
        raise NotFound(str(e))

    return Response(
        response=image_bytes,
        status=HTTPStatus.OK,
        headers={
            "Content-Type": content_type,
            "Cache-Control": _CACHE_HEADER,
        },
    )


@bp.get("/api/route-preview")
def route_preview() -> ResponseReturnValue:
    start = get_param("start", str)
    end = get_param("end", str)

    if not start or not end:
        raise BadRequest("Start and end destinations are required.")

    try:
        preview = service.get_route_preview(start, end)
    except ValueError as e:
        raise NotFound(str(e))

    return _api_response(preview)


@bp.post("/api/saved-routes")
@login_required
@use_db
def save_route(db: Session) -> ResponseReturnValue:
    user = account_service.require_user()
    route_name = get_json("route_name", str, "")
    start = require_json("start", dict)
    end = require_json("end", dict)
    stops = get_json("stops", list, [])
    route_geojson = require_json("route_geojson", dict)
    total_distance_miles = get_json("total_distance_miles", float, 0.0)
    total_duration_minutes = get_json("total_duration_minutes", int, 0)

    stops = add_stop_images(stops)

    try:
        record = service.save_route_for_user(
            db=db,
            user_id=user.id,
            route_name=route_name,
            start=start,
            end=end,
            stops=stops,
            route_geojson=route_geojson,
            total_distance_miles=total_distance_miles,
            total_duration_minutes=total_duration_minutes,
        )
    except ValueError as err:
        raise BadRequest(str(err))

    return _api_response(
        {
            "id": record.id,
            "name": record.name,
            "message": "Route saved.",
        },
        cache=False,
    )


@bp.get("/api/saved-routes")
@login_required
@use_db
def list_saved_routes(db: Session) -> ResponseReturnValue:
    user = account_service.require_user()
    saved_routes = service.list_saved_routes_for_user(db, user.id)
    return _api_response(saved_routes, cache=False)