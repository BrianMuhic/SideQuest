from math import atan2, cos, radians, sin, sqrt

import requests

from core.service.logger import get_logger

log = get_logger()

_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
_OVERPASS_URL = "https://overpass-api.de/api/interpreter"
_OSRM_URL = "https://router.project-osrm.org/route/v1/driving"
_WIKIMEDIA_URL = "https://commons.wikimedia.org/w/api.php"
_USER_AGENT_HEADER = {"User-Agent": "SideQuest/1.0"}
_HTTP_HEADERS = _USER_AGENT_HEADER | {"Accept": "application/json"}


# ============================== HTTP Helpers ============================== #


def _get_json(url: str, params: dict | None = None) -> dict | list:
    response = requests.get(url, params=params, timeout=120, headers=_HTTP_HEADERS)
    response.raise_for_status()
    return response.json()


def _post_overpass(query: str) -> dict:
    response = requests.post(
        _OVERPASS_URL,
        data=query,
        timeout=120,
        headers=_USER_AGENT_HEADER,
    )
    response.raise_for_status()
    return response.json()


# ============================== Geo Utilities ============================== #


def _haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    earth_radius_miles = 3958.8
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
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


def _sample_route_coordinates(
    route_coordinates: list[list[float]], step: int = 35
) -> list[list[float]]:
    if not route_coordinates:
        return []
    sampled = route_coordinates[::step]
    if route_coordinates[-1] not in sampled:
        sampled.append(route_coordinates[-1])
    return sampled


# ============================== OSM Data Helpers ============================== #


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
            _WIKIMEDIA_URL,
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
        pages = data.get("query", {}).get("pages", {})  # type: ignore[unresolved-attribute]
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
    if tags.get("tourism") == "viewpoint":
        return False
    if tags.get("boundary") == "national_park":
        return False
    if tags.get("protect_class") in {"2", "3", "5"}:
        return False
    if tags.get("leisure") == "nature_reserve":
        return False
    if tags.get("natural") == "peak":
        return False
    if tags.get("highway") == "trailhead":
        return False
    if tags.get("leisure") == "park":
        return True
    return False


def _find_stops_along_route(
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
        current_filters = [
            item.replace("RADIUS", str(detour_radius_meters))
            .replace("LAT", str(lat))
            .replace("LON", str(lon))
            for item in general_filters + scenic_filters
        ]

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
        except Exception as e:
            log.w(f"Overpass query failed at ({lat}, {lon}): {e}")
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

            key = f"{name}-{round(stop_lat, 5)}-{round(stop_lon, 5)}"
            if key in results_by_key:
                continue

            address_parts = []
            if tags.get("addr:housenumber") and tags.get("addr:street"):
                address_parts.append(f"{tags['addr:housenumber']} {tags['addr:street']}")
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
                "distance_off_route_miles": _nearest_route_distance_miles(
                    stop_lat, stop_lon, route_coordinates
                ),
                "description": (
                    tags.get("description")
                    or tags.get("tourism")
                    or tags.get("amenity")
                    or tags.get("leisure")
                    or tags.get("boundary")
                    or "Interesting stop near your route"
                ),
                "address": ", ".join(address_parts) if address_parts else "Address not available",
                "photo_url": _photo_url_from_tags(tags),
            }

    return sorted(
        results_by_key.values(),
        key=lambda item: (item["distance_off_route_miles"], item["name"].lower()),
    )[:20]


def _geocode(location: str) -> dict | None:
    results = _get_json(
        _NOMINATIM_URL, {"q": location, "format": "jsonv2", "limit": 1, "countrycodes": "us"}
    )
    return results[0] if results else None


def _get_route(start_lon: float, start_lat: float, end_lon: float, end_lat: float) -> dict | None:
    route_data = _get_json(
        f"{_OSRM_URL}/{start_lon},{start_lat};{end_lon},{end_lat}",
        {"overview": "full", "geometries": "geojson", "steps": "false"},
    )
    routes = route_data.get("routes", [])  # type: ignore[unresolved-attribute]
    return routes[0] if routes else None


# ============================== Public Service Functions ============================== #


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

    stops = _find_stops_along_route(route["geometry"], stop_categories, total_detour_minutes)
    log.i(f"Found {len(stops)} stops: {start_location!r} -> {end_location!r}")
    return stops, route["geometry"]


def get_location_suggestions(query: str) -> list[dict]:
    log.i(f"Location suggestions: {query!r}")
    data = _get_json(
        _NOMINATIM_URL,
        {"q": query, "format": "jsonv2", "limit": 5, "addressdetails": 1, "countrycodes": "us"},
    )
    suggestions = [
        {"label": item["display_name"], "lat": float(item["lat"]), "lon": float(item["lon"])}
        for item in data
        if item.get("display_name") and item.get("lat") and item.get("lon")
    ]
    log.i(f"Location suggestions: found {len(suggestions)} for {query!r}")
    return suggestions


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
        "end": {"name": end_place.get("display_name", end), "lat": end_lat, "lon": end_lon},
        "route": route["geometry"],
        "distance_miles": distance_miles,
        "duration_minutes": duration_minutes,
    }
