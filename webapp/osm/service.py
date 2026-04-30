import re
from math import atan2, cos, radians, sin, sqrt
from typing import Any
from urllib.parse import quote

import requests
from sqlalchemy.orm import Session

from config import config
from core.service.logger import get_logger
from osm.models import SavedRoute

log = get_logger()

_CATEGORY_TAG_FILTERS: dict[str, list[tuple[str, str]]] = {
    "gas": [("amenity", "fuel")],
    "food": [("amenity", "restaurant"), ("amenity", "fast_food"), ("amenity", "cafe")],
    "coffee": [("amenity", "cafe"), ("shop", "coffee")],
    "restroom": [("amenity", "toilets")],
    "hotel": [("tourism", "hotel"), ("tourism", "motel"), ("tourism", "guest_house")],
    "attractions": [("tourism", "museum"), ("tourism", "attraction"), ("tourism", "artwork")],
}

_SCENIC_FILTERS: list[tuple[str, str]] = [
    ("tourism", "viewpoint"),
    ("boundary", "national_park"),
    ("leisure", "nature_reserve"),
    ("protect_class", "~^(2|3|5)$"),
    ("natural", "peak"),
    ("highway", "trailhead"),
]

_GOOGLE_PLACES_TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
_GOOGLE_PLACE_PHOTO_URL = "https://places.googleapis.com/v1"
_google_photo_cache: dict[str, str | None] = {}


def _get_json(url: str, params: dict | None = None, timeout: int = 120) -> dict | list:
    headers = {
        "User-Agent": config.USER_AGENT,
        "Accept": "application/json",
    }
    response = requests.get(url, params=params, timeout=timeout, headers=headers)
    response.raise_for_status()
    return response.json()


def _post_overpass(query: str) -> dict:
    response = requests.post(
        config.OVERPASS_URL,
        data=query,
        timeout=120,
        headers={"User-Agent": config.USER_AGENT},
    )
    response.raise_for_status()
    return response.json()


def _haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    earth_radius_miles = 3958.8
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return earth_radius_miles * c


def _nearest_route_distance_miles(
    stop_lat: float, stop_lon: float, route_coordinates: list[list[float]]
) -> float:
    if not route_coordinates:
        return 0.0
    return round(
        min(_haversine_miles(stop_lat, stop_lon, lat, lon) for lon, lat in route_coordinates), 2
    )


def _sample_route_coordinates(
    route_coordinates: list[list[float]], step: int = 35
) -> list[list[float]]:
    if not route_coordinates:
        return []
    sampled = route_coordinates[::step]
    if route_coordinates[-1] not in sampled:
        sampled.append(route_coordinates[-1])
    return sampled


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
            config.WIKIMEDIA_URL,
            {
                "action": "query",
                "format": "json",
                "titles": clean_title,
                "prop": "imageinfo",
                "iiprop": "url",
                "iiurlwidth": 900,
                "origin": "*",
            },
            timeout=5,
        )
        pages = data.get("query", {}).get("pages", {})  # type: ignore
        for page in pages.values():
            imageinfo = page.get("imageinfo", [])
            if imageinfo:
                return imageinfo[0].get("thumburl") or imageinfo[0].get("url")
    except Exception:
        return None

    return None


def _photo_url_from_tags(tags: dict) -> str | None:
    commons_value = tags.get("wikimedia_commons")
    if commons_value:
        return _commons_thumb_from_title(commons_value)
    return None


def _google_photo_proxy_url(photo_name: str) -> str:
    return "/api/place-photo?name=" + quote(photo_name, safe="")


def _google_place_photo_name(stop_name: str, address: str, lat: float, lon: float) -> str | None:
    if not config.GOOGLE_PLACES_API_KEY:
        return None

    cache_key = f"{stop_name}|{address}|{round(lat, 4)}|{round(lon, 4)}"

    if cache_key in _google_photo_cache:
        return _google_photo_cache[cache_key]

    text_query = stop_name

    if address and address != "Address not available":
        text_query = f"{stop_name}, {address}"

    payload = {
        "textQuery": text_query,
        "locationBias": {
            "circle": {
                "center": {
                    "latitude": lat,
                    "longitude": lon,
                },
                "radius": 800.0,
            }
        },
        "maxResultCount": 1,
    }

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": config.GOOGLE_PLACES_API_KEY,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location,places.photos.name",
    }

    try:
        response = requests.post(
            _GOOGLE_PLACES_TEXT_SEARCH_URL,
            json=payload,
            headers=headers,
            timeout=8,
        )
        response.raise_for_status()

        data = response.json()
        places = data.get("places", [])

        if not places:
            _google_photo_cache[cache_key] = None
            return None

        place = places[0]
        location = place.get("location", {})
        place_lat = location.get("latitude")
        place_lon = location.get("longitude")

        if place_lat is not None and place_lon is not None:
            distance = _haversine_miles(lat, lon, float(place_lat), float(place_lon))

            if distance > 1.0:
                _google_photo_cache[cache_key] = None
                return None

        photos = place.get("photos", [])

        if not photos:
            _google_photo_cache[cache_key] = None
            return None

        photo_name = photos[0].get("name")
        _google_photo_cache[cache_key] = photo_name
        return photo_name

    except Exception as e:
        log.w(f"Google Places photo lookup failed for {stop_name!r}: {e}")
        _google_photo_cache[cache_key] = None
        return None


def _google_photo_url_for_stop(stop: dict) -> str | None:
    photo_name = _google_place_photo_name(
        str(stop.get("name", "")),
        str(stop.get("address", "")),
        float(stop.get("lat")),  # type: ignore
        float(stop.get("lon")),  # type: ignore
    )

    if not photo_name:
        return None

    return _google_photo_proxy_url(photo_name)


def _attach_google_photos(stops: list[dict]) -> list[dict]:
    if not config.GOOGLE_PLACES_API_KEY:
        return stops

    for stop in stops:
        if stop.get("photo_url"):
            continue

        google_photo_url = _google_photo_url_for_stop(stop)

        if google_photo_url:
            stop["photo_url"] = google_photo_url

    return stops


def get_google_place_photo(photo_name: str) -> tuple[bytes, str]:
    if not config.GOOGLE_PLACES_API_KEY:
        raise ValueError("Google Places API key is not configured.")

    clean_name = photo_name.strip()

    if not clean_name.startswith("places/"):
        raise ValueError("Invalid photo name.")

    response = requests.get(
        f"{_GOOGLE_PLACE_PHOTO_URL}/{clean_name}/media",
        params={
            "maxWidthPx": 900,
            "key": config.GOOGLE_PLACES_API_KEY,
        },
        timeout=15,
    )

    response.raise_for_status()

    content_type = response.headers.get("Content-Type", "image/jpeg")
    return response.content, content_type


def _overpass_clause(key: str, value: str, lat: float, lon: float, radius: int) -> str:
    if value.startswith("~"):
        return f'nwr(around:{radius},{lat},{lon})["{key}"~"{value[1:]}"];'
    return f'nwr(around:{radius},{lat},{lon})["{key}"="{value}"];'


def _tag_matches(tags: dict, key: str, value: str) -> bool:
    actual = tags.get(key)
    if actual is None:
        return False
    if value.startswith("~"):
        return bool(re.match(value[1:], actual))
    return actual == value


def _is_small_local_park(tags: dict) -> bool:
    return tags.get("leisure") == "park" and not any(
        _tag_matches(tags, k, v) for k, v in _SCENIC_FILTERS
    )


def _build_tag_filters(stop_categories: list[str]) -> list[tuple[str, str]]:
    tag_filters: list[tuple[str, str]] = []
    for category in stop_categories:
        if category in _CATEGORY_TAG_FILTERS:
            tag_filters.extend(_CATEGORY_TAG_FILTERS[category])
        elif category == "parks":
            tag_filters.extend(_SCENIC_FILTERS)
    return tag_filters


def _build_address(tags: dict) -> str:
    address_parts = []
    if tags.get("addr:housenumber") and tags.get("addr:street"):
        address_parts.append(f"{tags['addr:housenumber']} {tags['addr:street']}")
    elif tags.get("addr:street"):
        address_parts.append(tags["addr:street"])
    if tags.get("addr:city"):
        address_parts.append(tags["addr:city"])
    return ", ".join(address_parts) if address_parts else "Address not available"


def _process_overpass_element(
    element: dict, route_coordinates: list[list[float]], stop_categories: list[str]
) -> tuple[str, dict] | None:
    tags = element.get("tags", {})
    name = tags.get("name")

    if not name:
        return None

    if "parks" in stop_categories and _is_small_local_park(tags):
        return None

    stop_lat, stop_lon = _extract_center(element)

    if stop_lat is None or stop_lon is None:
        return None

    key = f"{name}-{round(stop_lat, 5)}-{round(stop_lon, 5)}"
    address = _build_address(tags)

    stop = {
        "id": key,
        "name": name,
        "category": _category_label(tags),
        "lat": stop_lat,
        "lon": stop_lon,
        "distance_off_route_miles": _nearest_route_distance_miles(
            stop_lat, stop_lon, route_coordinates
        ),
        "detour_minutes": None,
        "detour_miles": None,
        "description": (
            tags.get("description")
            or tags.get("tourism")
            or tags.get("amenity")
            or tags.get("leisure")
            or tags.get("boundary")
            or "Interesting stop near your route"
        ),
        "address": address,
        "photo_url": _photo_url_from_tags(tags),
    }

    return key, stop


def _find_stops_along_route(
    route_geometry: dict,
    stop_categories: list[str],
    allowed_detour_minutes: int,
    quick: bool = False,
) -> list[dict]:
    route_coordinates = route_geometry.get("coordinates", [])
    sampled_points = _sample_route_coordinates(route_coordinates)

    if not sampled_points or not stop_categories:
        return []

    detour_radius_meters = max(1600, min(32000, allowed_detour_minutes * 800))
    tag_filters = _build_tag_filters(stop_categories)

    if not tag_filters:
        return []

    if quick:
        query_points = sampled_points[:2]
    else:
        max_points = max(8, min(20, 32 // max(1, len(tag_filters) // 4)))
        if len(sampled_points) > max_points:
            stride = (len(sampled_points) - 1) / (max_points - 1)
            query_points = [sampled_points[round(i * stride)] for i in range(max_points)]
        else:
            query_points = sampled_points

    clauses = [
        _overpass_clause(key, value, lat, lon, detour_radius_meters)
        for lon, lat in query_points
        for key, value in tag_filters
    ]

    query = f"[out:json][timeout:60];\n(\n{''.join(clauses)}\n);\nout center tags 500;\n"

    try:
        log.d(f"Overpass query: {len(clauses)} clauses, {len(query)} chars")
        result = _post_overpass(query)
        log.d(f"Overpass returned {len(result.get('elements', []))} elements")
    except Exception as e:
        log.w(f"Overpass query failed: {e}")
        result = {"elements": []}

    results_by_key: dict[str, dict] = {}

    for element in result.get("elements", []):
        processed = _process_overpass_element(element, sampled_points, stop_categories)

        if processed is None or processed[0] in results_by_key:
            continue

        key, stop = processed
        results_by_key[key] = stop

    def _segment_index(stop: dict) -> int:
        nearest = min(
            range(len(sampled_points)),
            key=lambda i: _haversine_miles(
                stop["lat"], stop["lon"], sampled_points[i][1], sampled_points[i][0]
            ),
        )
        return min(2, nearest * 3 // max(1, len(sampled_points)))

    stops_by_segment: list[list[dict]] = [[], [], []]

    for stop in results_by_key.values():
        stops_by_segment[_segment_index(stop)].append(stop)

    per_segment_quota = 14
    selected: list[dict] = []

    for bucket in stops_by_segment:
        bucket.sort(key=lambda s: (s["distance_off_route_miles"], s["name"].lower()))
        selected.extend(bucket[:per_segment_quota])

    def _route_position_index(stop: dict) -> int:
        return min(
            range(len(sampled_points)),
            key=lambda i: _haversine_miles(
                stop["lat"], stop["lon"], sampled_points[i][1], sampled_points[i][0]
            ),
        )

    selected.sort(key=_route_position_index)
    selected = selected[:40]

    return selected


def _enrich_and_filter_stops(
    stops: list[dict],
    start_lon: float,
    start_lat: float,
    end_lon: float,
    end_lat: float,
    base_duration_seconds: float,
    base_distance_meters: float,
    allowed_detour_minutes: int,
) -> list[dict]:
    if not stops:
        return stops

    coords = f"{start_lon},{start_lat}"
    for s in stops:
        coords += f";{s['lon']},{s['lat']}"
    coords += f";{end_lon},{end_lat}"

    end_idx = len(stops) + 1

    table_url = config.OSRM_URL.replace("/route/v1/driving", "/table/v1/driving")

    try:
        data = _get_json(
            f"{table_url}/{coords}",
            {"annotations": "duration,distance"},
        )
        durations = data.get("durations", [])  # type: ignore
        distances = data.get("distances", [])  # type: ignore
    except Exception as e:
        log.w(f"OSRM table call failed: {e}")
        return stops

    allowed_seconds = allowed_detour_minutes * 60
    filtered = []

    for i, stop in enumerate(stops):
        stop_idx = i + 1

        detour_duration = durations[0][stop_idx] + durations[stop_idx][end_idx]
        detour_distance = distances[0][stop_idx] + distances[stop_idx][end_idx]

        actual_extra_seconds = detour_duration - base_duration_seconds
        actual_extra_miles = round((detour_distance - base_distance_meters) * 0.000621371, 1)

        if actual_extra_seconds > allowed_seconds:
            continue

        stop["detour_minutes"] = max(0, round(actual_extra_seconds / 60))
        stop["detour_miles"] = max(0.0, actual_extra_miles)
        filtered.append(stop)

    return filtered


def _geocode(location: str) -> dict | None:
    results = _get_json(
        config.NOMINATIM_URL,
        {"q": location, "format": "jsonv2", "limit": 1, "countrycodes": "us"},
    )
    return results[0] if results else None


def _get_route(start_lon: float, start_lat: float, end_lon: float, end_lat: float) -> dict | None:
    route_data = _get_json(
        f"{config.OSRM_URL}/{start_lon},{start_lat};{end_lon},{end_lat}",
        {"overview": "full", "geometries": "geojson", "steps": "false"},
    )
    routes = route_data.get("routes", [])  # type: ignore
    return routes[0] if routes else None


def friendly_detour_text(hours_value: int, minutes_value: int) -> str:
    if hours_value > 0 and minutes_value > 0:
        return f"{hours_value} hr {minutes_value} min"
    if hours_value > 0:
        return f"{hours_value} hr"
    return f"{minutes_value} min"


def find_stops(
    start_location: str,
    end_location: str,
    stop_categories: list[str],
    total_detour_minutes: int,
    quick: bool = False,
) -> tuple[list[dict], dict | None]:
    log.i(f"Find stops: {start_location!r} -> {end_location!r}, categories={stop_categories}")
    start_place = _geocode(start_location)
    end_place = _geocode(end_location)

    if not start_place or not end_place:
        log.w(f"Geocoding failed for {start_location!r} or {end_location!r}")
        return [], None

    route = _get_route(
        float(start_place["lon"]),
        float(start_place["lat"]),
        float(end_place["lon"]),
        float(end_place["lat"]),
    )

    if not route:
        log.w(f"No route found: {start_location!r} -> {end_location!r}")
        return [], None

    base_duration_seconds = route["duration"]
    base_distance_meters = route["distance"]

    stops = _find_stops_along_route(
        route["geometry"], stop_categories, total_detour_minutes, quick=quick
    )

    stops = _enrich_and_filter_stops(
        stops,
        float(start_place["lon"]),
        float(start_place["lat"]),
        float(end_place["lon"]),
        float(end_place["lat"]),
        base_duration_seconds,
        base_distance_meters,
        total_detour_minutes,
    )

    stops = _attach_google_photos(stops)

    log.i(f"Found {len(stops)} stops: {start_location!r} -> {end_location!r}")
    return stops, route["geometry"]


def get_location_suggestions(query: str) -> list[dict]:
    log.i(f"Location suggestions: {query!r}")
    data = _get_json(
        config.NOMINATIM_URL,
        {"q": query, "format": "jsonv2", "limit": 5, "addressdetails": 1, "countrycodes": "us"},
    )

    suggestions = [
        {"label": item["display_name"], "lat": float(item["lat"]), "lon": float(item["lon"])}
        for item in data
        if item.get("display_name") and item.get("lat") and item.get("lon")
    ]

    log.i(f"Location suggestions: found {len(suggestions)} for {query!r}")
    return suggestions


def get_route_legs(waypoints: list[dict]) -> dict:
    coords = ";".join(f"{wp['lon']},{wp['lat']}" for wp in waypoints)
    log.i(f"Route legs: {len(waypoints)} waypoints")

    route_data = _get_json(
        f"{config.OSRM_URL}/{coords}",
        {"overview": "full", "geometries": "geojson", "steps": "false"},
    )
    routes = route_data.get("routes", [])  # type: ignore

    if not routes:
        log.w("No route found for waypoints")
        raise ValueError("No drivable route was found for the given waypoints.")

    legs = []
    total_distance = 0.0
    total_duration = 0.0

    for leg in routes[0].get("legs", []):
        miles = round(leg["distance"] * 0.000621371, 1)
        minutes = round(leg["duration"] / 60)
        legs.append({"distance_miles": miles, "duration_minutes": minutes})
        total_distance += miles
        total_duration += minutes

    log.i(
        f"Route legs: {len(legs)} legs, {round(total_distance, 1)} mi, {round(total_duration)} min"
    )

    return {
        "legs": legs,
        "total_distance_miles": round(total_distance, 1),
        "total_duration_minutes": round(total_duration),
        "route_geojson": routes[0].get("geometry"),
    }


def get_route_preview(start: str, end: str) -> dict:
    log.i(f"Route preview: {start!r} -> {end!r}")
    start_place = _geocode(start)
    end_place = _geocode(end)

    if not start_place or not end_place:
        log.w(f"Geocoding failed for {start!r} or {end!r}")
        raise ValueError("Could not find one or both destinations.")

    start_lat, start_lon = float(start_place["lat"]), float(start_place["lon"])
    end_lat, end_lon = float(end_place["lat"]), float(end_place["lon"])

    route = _get_route(start_lon, start_lat, end_lon, end_lat)

    if not route:
        log.w(f"No route found: {start!r} -> {end!r}")
        raise ValueError("No drivable route was found.")

    distance_miles = round(route["distance"] * 0.000621371, 1)
    duration_minutes = round(route["duration"] / 60)

    log.i(f"Route preview: {distance_miles} mi, {duration_minutes} min")

    return {
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
        "route": route["geometry"],
        "distance_miles": distance_miles,
        "duration_minutes": duration_minutes,
    }


def _normalize_point(point: dict[str, Any], label: str) -> tuple[str, float, float]:
    name = str(point.get("name", "")).strip()

    if not name:
        raise ValueError(f"{label} location name is required.")

    try:
        lat = float(point["lat"])
        lon = float(point["lon"])
    except (KeyError, TypeError, ValueError) as err:
        raise ValueError(f"{label} location coordinates are invalid.") from err

    return name, lat, lon


def _normalize_stops(stops: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []

    for stop in stops:
        if not isinstance(stop, dict):
            continue

        try:
            lat = float(stop["lat"])
            lon = float(stop["lon"])
        except (KeyError, TypeError, ValueError):
            continue

        normalized.append(
            {
                "id": str(stop.get("id", "")),
                "name": str(stop.get("name", "")).strip(),
                "category": str(stop.get("category", "")).strip(),
                "lat": lat,
                "lon": lon,
            }
        )

    return normalized


def save_route_for_user(
    db: Session,
    user_id: int,
    route_name: str,
    start: dict[str, Any],
    end: dict[str, Any],
    stops: list[dict[str, Any]],
    route_geojson: dict[str, Any],
    total_distance_miles: float,
    total_duration_minutes: int,
) -> SavedRoute:
    start_name, start_lat, start_lon = _normalize_point(start, "Start")
    end_name, end_lat, end_lon = _normalize_point(end, "Destination")

    if not isinstance(route_geojson, dict):
        raise ValueError("Route geometry is invalid.")

    name = route_name.strip() or f"{start_name} to {end_name}"

    record = SavedRoute(
        user_id=user_id,
        name=name[:256],
        start_name=start_name[:256],
        start_lat=start_lat,
        start_lon=start_lon,
        end_name=end_name[:256],
        end_lat=end_lat,
        end_lon=end_lon,
        stops=_normalize_stops(stops),
        route_geojson=route_geojson,
        total_distance_miles=float(total_distance_miles),
        total_duration_minutes=max(0, int(total_duration_minutes)),
    )

    record.add(db, flush=True)
    log.i(f"Saved route {record.id} for user {user_id}")
    return record


def list_saved_routes_for_user(db: Session, user_id: int) -> list[dict[str, Any]]:
    routes = SavedRoute.for_user(db, user_id)

    return [
        {
            "id": route.id,
            "name": route.name,
            "start": {
                "name": route.start_name,
                "lat": route.start_lat,
                "lon": route.start_lon,
            },
            "end": {
                "name": route.end_name,
                "lat": route.end_lat,
                "lon": route.end_lon,
            },
            "stops": route.stops,
            "route_geojson": route.route_geojson,
            "total_distance_miles": route.total_distance_miles,
            "total_duration_minutes": route.total_duration_minutes,
            "created_date": route.created_date.isoformat(),
        }
        for route in routes
    ]
