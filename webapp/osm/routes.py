from dataclasses import dataclass

import requests
from flask import Blueprint, jsonify, make_response, render_template, request
from flask.typing import ResponseReturnValue

bp = Blueprint(
    "osm",
    __name__,
    template_folder="templates",
)


@dataclass
class Page:
    route: str
    file: str
    title: str


PAGES = (
    Page("/", "index.html", "SideQuest"),
    Page("/adventure", "adventure.html", "Map Out Our Adventure"),
)


def _register_page(page: Page) -> None:
    def page_handler() -> ResponseReturnValue:
        return render_template(
            page.file,
            title=page.title,
        )

    name = page.route[1:].replace("/", "_").replace("-", "_") or "home"
    bp.add_url_rule(rule=page.route, endpoint=name, view_func=page_handler)


for page in PAGES:
    _register_page(page)


def _get_json(url: str, params: dict) -> dict | list:
    response = requests.get(
        url,
        params=params,
        timeout=20,
        headers={
            "User-Agent": "SideQuest/1.0",
            "Accept": "application/json",
        },
    )
    response.raise_for_status()
    return response.json()


@bp.get("/api/location-suggestions")
def location_suggestions() -> ResponseReturnValue:
    query = request.args.get("q", "").strip()
    if len(query) < 3:
        response = make_response(jsonify([]), 200)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        return response

    try:
        data = _get_json(
            "https://nominatim.openstreetmap.org/search",
            {
                "q": query,
                "format": "jsonv2",
                "limit": 5,
                "addressdetails": 1,
                "countrycodes": "us",
            },
        )

        suggestions = []
        for item in data:
            display_name = item.get("display_name")
            lat = item.get("lat")
            lon = item.get("lon")
            if display_name and lat and lon:
                suggestions.append(
                    {
                        "label": display_name,
                        "lat": float(lat),
                        "lon": float(lon),
                    }
                )

        response = make_response(jsonify(suggestions), 200)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        return response
    except Exception:
        response = make_response(jsonify([]), 200)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        return response


@bp.get("/api/route-preview")
def route_preview() -> ResponseReturnValue:
    start = request.args.get("start", "").strip()
    end = request.args.get("end", "").strip()

    if not start or not end:
        response = make_response(
            jsonify({"error": "Start and end destinations are required."}),
            400,
        )
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        return response

    try:
        start_results = _get_json(
            "https://nominatim.openstreetmap.org/search",
            {
                "q": start,
                "format": "jsonv2",
                "limit": 1,
                "countrycodes": "us",
            },
        )
        end_results = _get_json(
            "https://nominatim.openstreetmap.org/search",
            {
                "q": end,
                "format": "jsonv2",
                "limit": 1,
                "countrycodes": "us",
            },
        )

        if not start_results or not end_results:
            response = make_response(
                jsonify({"error": "Could not find one or both destinations."}),
                404,
            )
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            return response

        start_place = start_results[0]
        end_place = end_results[0]

        start_lat = float(start_place["lat"])
        start_lon = float(start_place["lon"])
        end_lat = float(end_place["lat"])
        end_lon = float(end_place["lon"])

        route_data = _get_json(
            f"https://router.project-osrm.org/route/v1/driving/{start_lon},{start_lat};{end_lon},{end_lat}",
            {
                "overview": "full",
                "geometries": "geojson",
                "steps": "false",
            },
        )

        routes = route_data.get("routes", [])
        if not routes:
            response = make_response(
                jsonify({"error": "No drivable route was found."}),
                404,
            )
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            return response

        route = routes[0]
        geometry = route["geometry"]
        distance_miles = round(route["distance"] * 0.000621371, 1)
        duration_minutes = round(route["duration"] / 60)

        response = make_response(
            jsonify(
                {
                    "start": {
                        "name": start_place.get("display_name", start),
                        "lat": start_lat,
                        "lon": start_lon,
                    },
                    "end": {
                        "name": end_place.get("display_name", end),
                        "lat": end_lat,
                        "lon": end_lon,
                    },
                    "route": geometry,
                    "distance_miles": distance_miles,
                    "duration_minutes": duration_minutes,
                }
            ),
            200,
        )
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        return response
    except Exception:
        response = make_response(
            jsonify({"error": "Unable to build route preview right now."}),
            500,
        )
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        return response