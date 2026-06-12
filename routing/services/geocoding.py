import requests
from django.conf import settings
from django.core.cache import cache

NOMINATIM = "https://nominatim.openstreetmap.org/search"


def geocode_place(query):
    """Return (lat, lng). Accepts 'lat,lng' directly, otherwise geocodes a US place name."""
    query = query.strip()

    parts = query.split(",")
    if len(parts) == 2:
        try:
            return float(parts[0]), float(parts[1])
        except ValueError:
            pass

    cache_key = f"geocode:{query.lower()}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    resp = requests.get(
        NOMINATIM,
        params={"q": query, "format": "json", "countrycodes": "us", "limit": 1},
        headers={"User-Agent": settings.GEOCODER_USER_AGENT},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if not data:
        raise ValueError(f"Could not geocode location: {query}")

    result = (float(data[0]["lat"]), float(data[0]["lon"]))
    cache.set(cache_key, result, 60 * 60 * 24)
    return result
