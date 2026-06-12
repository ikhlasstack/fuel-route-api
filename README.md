# Fuel Route Optimizer API

A Django 6.0 REST API that plans the most cost-effective fuel stops for a road trip between any two US locations. Give it a start and finish — it returns the full driving route, the cheapest fuel stops along the way, and a full cost breakdown.

---

## How It Works

1. **Geocode** — the two endpoint names are resolved to lat/lng via Nominatim (OpenStreetMap). Results are cached for 24 hours.
2. **One routing call** — a single request to the OSRM routing API returns the full route geometry and total distance. This is the only external call made per request.
3. **Local optimization** — 8,000+ pre-loaded US fuel stations are matched against the route entirely in Python. No further API calls are made.
4. **Greedy stop selection** — within each mandatory refuel window (≤ 500 miles), the cheapest available station is chosen.
5. **Cost breakdown** — total fuel cost is calculated leg by leg and returned alongside the full route geometry.

**Vehicle assumptions:** 500-mile tank range, 10 MPG, starts full at origin.

---

## Stack

| Concern | Choice |
|---|---|
| Framework | Django 6.0.6 (Python 3.12+) |
| API layer | Django REST Framework 3.17 |
| Routing | OSRM public server (free, no key needed) |
| Geocoding | Nominatim / OpenStreetMap (free, no key needed) |
| Station coords | Offline join to SimpleMaps US Cities table (CC BY 4.0) |
| Database | SQLite |
| Map rendering | Folium (interactive Leaflet.js) |
| Caching | Django in-memory cache |

---

## Setup

### 1. Clone the repo

```bash
git clone <your-repo-url>
cd fuel-route-api
```

### 2. Create and activate a virtual environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

Verify Django installed correctly:

```bash
django-admin --version
# Expected: 6.0.6
```

### 4. Place the data files

You need two CSV files inside the `data/` folder:

| File | Description |
|---|---|
| `data/fuel-prices-for-be-assessment.csv` | Supplied fuel price data (~8,000 US stations) |
| `data/uscities.csv` | Free US cities lat/lng table from [SimpleMaps](https://simplemaps.com/data/us-cities) (Basic, CC BY 4.0) |

### 5. Run migrations

```bash
python manage.py migrate
```

### 6. Load the fuel station data (one-time)

```bash
python manage.py load_fuel_data
```

Expected output:
```
Loaded 31186 city coordinates.
Created 8151 stations. Geocoded 6934, missed 1217.
```

### 7. Run the tests

```bash
python manage.py test
```

Expected output:
```
Ran 3 tests in 0.005s
OK
```

### 8. Start the server

```bash
python manage.py runserver
```

The API is now available at `http://127.0.0.1:8000/`.

---

## API Reference

### `GET /api/route/`

Returns a JSON response with the optimized fuel stop plan.

**Query parameters:**

| Parameter | Required | Example |
|---|---|---|
| `start` | Yes | `New York, NY` |
| `finish` | Yes | `Los Angeles, CA` |

**Example request:**

```bash
curl "http://127.0.0.1:8000/api/route/?start=New York, NY&finish=Los Angeles, CA"
```

**Example response:**

```json
{
  "start": { "query": "New York, NY", "lat": 40.7127, "lng": -74.006 },
  "finish": { "query": "Los Angeles, CA", "lat": 34.0537, "lng": -118.2428 },
  "total_distance_miles": 2793.9,
  "vehicle": { "range_miles": 500.0, "mpg": 10.0 },
  "total_gallons": 279.39,
  "total_fuel_cost_usd": 868.05,
  "fuel_stops": [
    {
      "name": "SHEETZ #639",
      "address": "I-80 Exit 223",
      "city": "Youngstown",
      "state": "OH",
      "price_per_gallon": 3.059,
      "distance_along_route_miles": 391.6,
      "detour_miles": 4.23,
      "lat": 41.0993,
      "lng": -80.6463
    }
  ],
  "cost_breakdown": [
    {
      "from_mile": 0.0,
      "to_mile": 391.6,
      "gallons": 39.16,
      "price_per_gallon": 3.059,
      "leg_cost_usd": 119.79
    }
  ],
  "route_geometry": {
    "type": "LineString",
    "coordinates": [[-74.006, 40.7127], "..."]
  }
}
```

---

### `GET /api/route/map/`

Returns an interactive HTML map (open in a browser). Same query parameters as above.

```
http://127.0.0.1:8000/api/route/map/?start=New York, NY&finish=Los Angeles, CA
```

Shows the full route as a polyline with:
- Green marker — start
- Red marker — finish
- Blue markers — each fuel stop (hover to see name and price)

---

## Testing

### Browser

```
http://127.0.0.1:8000/api/route/?start=New York, NY&finish=Los Angeles, CA
http://127.0.0.1:8000/api/route/map/?start=Chicago, IL&finish=Houston, TX
```

### curl

```bash
curl "http://127.0.0.1:8000/api/route/?start=Chicago, IL&finish=Dallas, TX"
```

### Postman

1. New request → **GET**
2. URL: `http://127.0.0.1:8000/api/route/`
3. Params tab → add `start` and `finish`
4. Send

### Example routes to try

```
New York, NY       → Los Angeles, CA
Chicago, IL        → Dallas, TX
Seattle, WA        → Miami, FL
Boston, MA         → Phoenix, AZ
Denver, CO         → Nashville, TN
```

---

## Error Responses

| Scenario | Status | Response |
|---|---|---|
| Missing start or finish | 400 | `{"error": "Provide both 'start' and 'finish' query parameters."}` |
| Location not recognised | 400 | `{"error": "Could not geocode location: ..."}` |
| No station within range | 400 | `{"error": "No fuel station within range on this stretch..."}` |
| Route not found | 400 | `{"error": "No route found between the given locations."}` |

---

## Project Structure

```
fuel-route-api/
├── manage.py
├── requirements.txt
├── data/
│   ├── fuel-prices-for-be-assessment.csv   ← supplied fuel price data
│   └── uscities.csv                        ← SimpleMaps US cities lat/lng
├── fuelroute/
│   ├── settings.py                         ← Django config + vehicle settings
│   └── urls.py                             ← root URL router
└── routing/
    ├── models.py                           ← FuelStation model
    ├── views.py                            ← RouteAPIView, RouteMapView
    ├── urls.py                             ← /api/route/ and /api/route/map/
    ├── tests.py                            ← 3 unit tests
    ├── services/
    │   ├── geocoding.py                    ← Nominatim with 24h cache
    │   ├── routing_api.py                  ← single OSRM call (ORS fallback)
    │   ├── fuel_optimizer.py               ← haversine, grid index, greedy planner
    │   └── trip.py                         ← orchestrates all services per request
    └── management/commands/
        └── load_fuel_data.py               ← one-time CSV loader + offline geocoding
```

---

## Configuration

All vehicle and routing settings are in `fuelroute/settings.py`:

```python
VEHICLE_RANGE_MILES = 500.0   # max distance on a full tank
VEHICLE_MPG = 10.0            # fuel economy
ROUTING_PROVIDER = "osrm"     # "osrm" (default, free) or "ors" (needs API key)
```

To switch to OpenRouteService (more reliable, needs a free key):

```python
ROUTING_PROVIDER = "ors"
ORS_API_KEY = "your-key-here"
```

---

## Performance

- **First request** (cold): ~2–4 seconds (one OSRM call + two Nominatim calls)
- **Repeat request** (cached): ~200ms, zero external API calls
- **Geocodes** cached 24 hours per place name
- **Full route results** cached 1 hour per (start, finish) pair
- **Station matching** uses a spatial grid index — near-linear speed with 8,000+ stations

---

## Data Attribution

US city coordinates provided by [SimpleMaps US Cities Database](https://simplemaps.com/data/us-cities) (Basic edition), licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
