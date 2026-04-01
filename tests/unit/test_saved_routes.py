from json import loads

from flask.testing import FlaskClient

from tests.util import get, post_json


def _payload() -> dict:
    return {
        "route_name": "Blue Ridge Weekend",
        "start": {"name": "Roanoke, VA", "lat": 37.271, "lon": -79.941},
        "end": {"name": "Asheville, NC", "lat": 35.595, "lon": -82.551},
        "stops": [
            {
                "id": "stop-1",
                "name": "Pilot Mountain",
                "category": "Attraction",
                "lat": 36.34,
                "lon": -80.47,
            }
        ],
        "route_geojson": {
            "type": "LineString",
            "coordinates": [[-79.941, 37.271], [-82.551, 35.595]],
        },
        "total_distance_miles": 221.3,
        "total_duration_minutes": 245,
    }


def test_save_route_requires_login(client: FlaskClient) -> None:
    response = client.post("/api/saved-routes", json=_payload(), content_type="application/json")
    assert response.status_code == 401


def test_user_can_save_and_list_routes(user_client: FlaskClient) -> None:
    post_json(user_client, "/api/saved-routes", _payload())

    response = get(user_client, "/api/saved-routes")
    data = loads(response.data)

    assert len(data) == 1
    saved = data[0]
    assert saved["name"] == "Blue Ridge Weekend"
    assert saved["start"]["name"] == "Roanoke, VA"
    assert saved["end"]["name"] == "Asheville, NC"
    assert saved["total_duration_minutes"] == 245
