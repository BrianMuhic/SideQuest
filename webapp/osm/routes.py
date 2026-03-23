from dataclasses import dataclass
from math import atan2, cos, radians, sin, sqrt

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


def _get_json(url: str, params: dict | None = None) -> dict | list:
    response = requests.get(
        url,
        params=params,
        timeout=30,
        headers={
            "User-Agent": "SideQuest/1.0",
            "Accept": "application/json",
        },
    )
    response.raise_for_status()
    return response.json()


def _post_overpass(query: str) -> dict:
    response = requests.post(
        "https://overpass-api.de/api/interpreter",
        data=query,
        timeout=35,
        headers={
            "User-Agent": "SideQuest/1.0",
        },
    )
    response.raise_for_status()
    return response.json()


def _haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    earth_radius_miles = 3958.8

    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    )
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return earth_radius_miles * c


def _nearest_route_distance_miles(
    stop_lat: float,
    stop_lon: float,
    route_coordinates: list[list[float]],
) -> float:
    closest = None

    for lon, lat in route_coordinates:
        distance = _haversine_miles(stop_lat, stop_lon, lat, lon)
        if closest is None or distance < closest:
            closest = distance

    return round(closest or 0.0, 2)


def _sample_route_coordinates(route_coordinates: list[list[float]], step: int = 35) -> list[list[float]]:
    if not route_coordinates:
        return []

    sampled = route_coordinates[::step]
    if route_coordinates[-1] not in sampled:
        sampled.append(route_coordinates[-1])
    return sampled


def _friendly_detour_text(hours_value: int, minutes_value: int) -> str:
    if hours_value > 0 and minutes_value > 0:
        return f"{hours_value} hr {minutes_value} min"
    if hours_value > 0:
        return f"{hours_value} hr"
    return f"{minutes_value} min"


def _extract_center(element: dict) -> tuple[float | None, float | None]:
    if "lat" in element and "lon" in element:
        return float(element["lat"]), float(element["lon"])

    center = element.get("center")
    if center and "lat" in center and "lon" in center:
        return float(center["lat"]), float(center["lon"])

    return None, None


def _category_label(tags: dict) -> str:
    if tags.get("amenity") == "fuel":
        return "Gas"
    if tags.get("amenity") in {"restaurant", "fast_food"}:
        return "Food"
    if tags.get("amenity") == "cafe" or tags.get("shop") == "coffee":
        return "Coffee"
    if tags.get("amenity") == "toilets":
        return "Restroom"
    if tags.get("tourism") in {"hotel", "motel", "guest_house"}:
        return "Hotel"
    if tags.get("tourism") in {"museum", "attraction", "artwork"}:
        return "Attraction"
    if (
        tags.get("boundary") == "national_park"
        or tags.get("protect_class") in {"2", "3", "5"}
        or tags.get("tourism") in {"viewpoint", "attraction"}
        or tags.get("leisure") in {"nature_reserve"}
    ):
        return "Scenic / Parks"
    return "Stop"


def _commons_thumb_from_title(file_title: str) -> str | None:
    clean_title = file_title.strip()
    if not clean_title:
        return None

    if not clean_title.startswith("File:"):
        clean_title = f"File:{clean_title}"

    try:
        data = _get_json(
            "https://commons.wikimedia.org/w/api.php",
            {
                "action": "query",
                "format": "json",
                "titles": clean_title,
                "prop": "imageinfo",
                "iiprop": "url",
                "iiurlwidth": 900,
                "origin": "*",
            },
        )

        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            imageinfo = page.get("imageinfo", [])
            if imageinfo:
                thumb_url = imageinfo[0].get("thumburl")
                if thumb_url:
                    return thumb_url

                direct_url = imageinfo[0].get("url")
                if direct_url:
                    return direct_url
    except Exception:
        return None

    return None


def _photo_url_from_tags(tags: dict) -> str | None:
    commons_value = tags.get("wikimedia_commons")
    if commons_value:
        return _commons_thumb_from_title(commons_value)
    return None


def _build_general_filters(stop_categories: list[str]) -> list[str]:
    filters = []

    if "gas" in stop_categories:
        filters.append('nwr(around:RADIUS,LAT,LON)["amenity"="fuel"];')

    if "food" in stop_categories:
        filters.extend(
            [
                'nwr(around:RADIUS,LAT,LON)["amenity"="restaurant"];',
                'nwr(around:RADIUS,LAT,LON)["amenity"="fast_food"];',
                'nwr(around:RADIUS,LAT,LON)["amenity"="cafe"];',
            ]
        )

    if "coffee" in stop_categories:
        filters.extend(
            [
                'nwr(around:RADIUS,LAT,LON)["amenity"="cafe"];',
                'nwr(around:RADIUS,LAT,LON)["shop"="coffee"];',
            ]
        )

    if "restroom" in stop_categories:
        filters.append('nwr(around:RADIUS,LAT,LON)["amenity"="toilets"];')

    if "hotel" in stop_categories:
        filters.extend(
            [
                'nwr(around:RADIUS,LAT,LON)["tourism"="hotel"];',
                'nwr(around:RADIUS,LAT,LON)["tourism"="motel"];',
                'nwr(around:RADIUS,LAT,LON)["tourism"="guest_house"];',
            ]
        )

    if "attractions" in stop_categories:
        filters.extend(
            [
                'nwr(around:RADIUS,LAT,LON)["tourism"="museum"];',
                'nwr(around:RADIUS,LAT,LON)["tourism"="attraction"];',
                'nwr(around:RADIUS,LAT,LON)["tourism"="artwork"];',
            ]
        )

    return filters


def _build_scenic_filters() -> list[str]:
    return [
        'nwr(around:RADIUS,LAT,LON)["tourism"="viewpoint"];',
        'nwr(around:RADIUS,LAT,LON)["boundary"="national_park"];',
        'nwr(around:RADIUS,LAT,LON)["leisure"="nature_reserve"];',
        'nwr(around:RADIUS,LAT,LON)["protect_class"~"^(2|3|5)$"];',
        'nwr(around:RADIUS,LAT,LON)["natural"="peak"];',
        'nwr(around:RADIUS,LAT,LON)["highway"="trailhead"];',
    ]


def _is_small_local_park(tags: dict) -> bool:
    leisure_value = tags.get("leisure")
    boundary_value = tags.get("boundary")
    protect_class = tags.get("protect_class")
    tourism_value = tags.get("tourism")
    natural_value = tags.get("natural")
    highway_value = tags.get("highway")

    if tourism_value == "viewpoint":
        return False
    if boundary_value == "national_park":
        return False
    if protect_class in {"2", "3", "5"}:
        return False
    if leisure_value == "nature_reserve":
        return False
    if natural_value == "peak":
        return False
    if highway_value == "trailhead":
        return False

    if leisure_value == "park":
        return True

    return False


def _find_real_stops_along_route(
    route_geometry: dict,
    stop_categories: list[str],
    allowed_detour_minutes: int,
) -> list[dict]:
    route_coordinates = route_geometry.get("coordinates", [])
    sampled_points = _sample_route_coordinates(route_coordinates)

    if not sampled_points or not stop_categories:
        return []

    detour_radius_meters = max(1600, min(18000, allowed_detour_minutes * 700))
    results_by_key: dict[str, dict] = {}

    general_filters = _build_general_filters(stop_categories)
    scenic_filters = _build_scenic_filters() if "parks" in stop_categories else []

    for lon, lat in sampled_points[:8]:
        current_filters = []

        current_filters.extend(
            item.replace("RADIUS", str(detour_radius_meters))
            .replace("LAT", str(lat))
            .replace("LON", str(lon))
            for item in general_filters
        )

        current_filters.extend(
            item.replace("RADIUS", str(detour_radius_meters))
            .replace("LAT", str(lat))
            .replace("LON", str(lon))
            for item in scenic_filters
        )

        if not current_filters:
            continue

        query = f"""
[out:json][timeout:20];
(
{"".join(current_filters)}
);
out center tags 16;
"""

        try:
            overpass_data = _post_overpass(query)
        except Exception:
            continue

        for element in overpass_data.get("elements", []):
            tags = element.get("tags", {})
            name = tags.get("name")
            if not name:
                continue

            if "parks" in stop_categories and _is_small_local_park(tags):
                continue

            stop_lat, stop_lon = _extract_center(element)
            if stop_lat is None or stop_lon is None:
                continue

            distance_off_route = _nearest_route_distance_miles(
                stop_lat,
                stop_lon,
                route_coordinates,
            )

            key = f"{name}-{round(stop_lat, 5)}-{round(stop_lon, 5)}"
            if key in results_by_key:
                continue

            address_parts = []
            if tags.get("addr:housenumber") and tags.get("addr:street"):
                address_parts.append(f'{tags["addr:housenumber"]} {tags["addr:street"]}')
            elif tags.get("addr:street"):
                address_parts.append(tags["addr:street"])

            if tags.get("addr:city"):
                address_parts.append(tags["addr:city"])

            results_by_key[key] = {
                "id": key,
                "name": name,
                "category": _category_label(tags),
                "lat": stop_lat,
                "lon": stop_lon,
                "distance_off_route_miles": distance_off_route,
                "description": tags.get("description")
                or tags.get("tourism")
                or tags.get("amenity")
                or tags.get("leisure")
                or tags.get("boundary")
                or "Interesting stop near your route",
                "address": ", ".join(address_parts) if address_parts else "Address not available",
                "photo_url": _photo_url_from_tags(tags),
            }

    sorted_results = sorted(
        results_by_key.values(),
        key=lambda item: (item["distance_off_route_miles"], item["name"].lower()),
    )

    return sorted_results[:20]


@bp.route("/adventure", methods=["GET", "POST"])
def adventure() -> ResponseReturnValue:
    if request.method == "POST":
        start_location = request.form.get("start_location", "").strip()
        end_location = request.form.get("end_location", "").strip()
        duration_text = request.form.get("duration_text", "").strip()
        distance_text = request.form.get("distance_text", "").strip()

        return render_template(
            "adventure.html",
            title="Trip Preferences",
            start_location=start_location,
            end_location=end_location,
            duration_text=duration_text,
            distance_text=distance_text,
        )

    return render_template(
        "adventure.html",
        title="Trip Preferences",
        start_location="",
        end_location="",
        duration_text="",
        distance_text="",
    )


@bp.route("/phase-3", methods=["POST"])
def phase_3() -> ResponseReturnValue:
    start_location = request.form.get("start_location", "").strip()
    end_location = request.form.get("end_location", "").strip()
    duration_text = request.form.get("duration_text", "").strip()
    distance_text = request.form.get("distance_text", "").strip()
    latest_arrival_time = request.form.get("latest_arrival_time", "").strip()
    allowed_detour_hours = request.form.get("allowed_detour_hours", "0").strip()
    allowed_detour_minutes = request.form.get("allowed_detour_minutes", "0").strip()
    stop_categories = request.form.getlist("stop_categories")

    try:
        detour_hours_value = int(allowed_detour_hours) if allowed_detour_hours else 0
    except ValueError:
        detour_hours_value = 0

    try:
        detour_minutes_value = int(allowed_detour_minutes) if allowed_detour_minutes else 0
    except ValueError:
        detour_minutes_value = 0

    total_detour_minutes = (detour_hours_value * 60) + detour_minutes_value
    allowed_detour_text = _friendly_detour_text(detour_hours_value, detour_minutes_value)

    recommended_stops = []
    route_geojson = None

    try:
        start_results = _get_json(
            "https://nominatim.openstreetmap.org/search",
            {
                "q": start_location,
                "format": "jsonv2",
                "limit": 1,
                "countrycodes": "us",
            },
        )
        end_results = _get_json(
            "https://nominatim.openstreetmap.org/search",
            {
                "q": end_location,
                "format": "jsonv2",
                "limit": 1,
                "countrycodes": "us",
            },
        )

        if start_results and end_results:
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
            if routes:
                route_geojson = routes[0]["geometry"]
                recommended_stops = _find_real_stops_along_route(
                    route_geojson,
                    stop_categories,
                    total_detour_minutes,
                )
    except Exception:
        recommended_stops = []

    return render_template(
        "stop_selection.html",
        title="Recommended Stops",
        start_location=start_location,
        end_location=end_location,
        duration_text=duration_text,
        distance_text=distance_text,
        latest_arrival_time=latest_arrival_time,
        allowed_detour_text=allowed_detour_text,
        total_detour_minutes=total_detour_minutes,
        stop_categories=stop_categories,
        recommended_stops=recommended_stops,
        route_geojson=route_geojson,
    )


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