import json
from http import HTTPStatus
from typing import Any

from flask import render_template
from flask.typing import ResponseReturnValue
from werkzeug import Response
from werkzeug.exceptions import BadRequest, NotFound

from core.app.blueprint import BaseBlueprint
from core.util.request_params import get_json, get_param, require_json
from osm import service

bp = BaseBlueprint("osm")


@bp.get("/")
def home() -> ResponseReturnValue:
    return render_template("index.html", title="SideQuest")


@bp.get("/route")
def route_detail() -> ResponseReturnValue:
    return render_template("route_detail.html", title="Your Route — SideQuest")


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


@bp.post("/api/find-stops")
def find_stops() -> ResponseReturnValue:
    start_location = require_json("start_location", str)
    end_location = require_json("end_location", str)
    stop_categories = get_json("stop_categories", list, [])
    latest_arrival_time = get_json("latest_arrival_time", str, "")
    detour_hours = get_json("allowed_detour_hours", int, 0)
    detour_minutes = get_json("allowed_detour_minutes", int, 0)

    total_detour_minutes = (detour_hours * 60) + detour_minutes
    allowed_detour_text = service.friendly_detour_text(detour_hours, detour_minutes)

    try:
        stops, route_geojson = service.find_stops(
            start_location, end_location, stop_categories, total_detour_minutes
        )
    except Exception:
        stops, route_geojson = [], None

    data = {
        "stops": stops,
        "route_geojson": route_geojson,
        "allowed_detour_text": allowed_detour_text,
        "latest_arrival_time": latest_arrival_time,
    }
    return _api_response(data)


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

    try:
        suggestions = service.get_location_suggestions(query)
    except Exception:
        suggestions = []

    return _api_response(suggestions, cache=False)


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
