import requests
from django.conf import settings

METERS_PER_MILE = 1609.34


def get_route(start_lat, start_lng, end_lat, end_lng):
    """
    ONE call to the routing API.
    Returns (coords, distance_miles) where coords is [[lng, lat], ...].
    """
    if settings.ROUTING_PROVIDER == "ors":
        return _ors(start_lat, start_lng, end_lat, end_lng)
    return _osrm(start_lat, start_lng, end_lat, end_lng)


def _osrm(start_lat, start_lng, end_lat, end_lng):
    url = (
        f"{settings.OSRM_BASE_URL}/route/v1/driving/"
        f"{start_lng},{start_lat};{end_lng},{end_lat}"
    )
    resp = requests.get(
        url,
        params={"overview": "full", "geometries": "geojson"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != "Ok" or not data.get("routes"):
        raise ValueError("No route found between the given locations.")
    route = data["routes"][0]
    coords = route["geometry"]["coordinates"]
    distance_miles = route["distance"] / METERS_PER_MILE
    return coords, distance_miles


def _ors(start_lat, start_lng, end_lat, end_lng):
    url = "https://api.openrouteservice.org/v2/directions/driving-car/geojson"
    resp = requests.post(
        url,
        json={"coordinates": [[start_lng, start_lat], [end_lng, end_lat]]},
        headers={"Authorization": settings.ORS_API_KEY},
        timeout=30,
    )
    resp.raise_for_status()
    feature = resp.json()["features"][0]
    coords = feature["geometry"]["coordinates"]
    distance_miles = feature["properties"]["summary"]["distance"] / METERS_PER_MILE
    return coords, distance_miles
