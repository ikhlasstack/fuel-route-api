import math

EARTH_RADIUS_MILES = 3958.8


def haversine(lat1, lng1, lat2, lng2):
    """Great-circle distance in miles between two lat/lng points."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_MILES * math.asin(math.sqrt(a))


def build_route_points(coords):
    """coords: [[lng, lat], ...] -> [{lat, lng, dist}] with cumulative miles from start."""
    points, cumulative, prev = [], 0.0, None
    for lng, lat in coords:
        if prev is not None:
            cumulative += haversine(prev[1], prev[0], lat, lng)
        points.append({"lat": lat, "lng": lng, "dist": cumulative})
        prev = (lng, lat)
    return points


def downsample(points, step_miles=5.0):
    """Keep ~1 point every step_miles to speed up station matching."""
    sampled, last = [points[0]], 0.0
    for p in points[1:]:
        if p["dist"] - last >= step_miles:
            sampled.append(p)
            last = p["dist"]
    if sampled[-1] is not points[-1]:
        sampled.append(points[-1])
    return sampled


def stations_near_route(sampled, stations, buffer_miles=5.0):
    """
    Return stations within buffer_miles of the route, tagged with dist-along-route.
    Uses a grid index so each station only checks nearby route points.
    """
    cell = 0.5
    grid = {}
    for p in sampled:
        key = (round(p["lat"] / cell), round(p["lng"] / cell))
        grid.setdefault(key, []).append(p)

    near = []
    for s in stations:
        if s.latitude is None:
            continue
        ck = (round(s.latitude / cell), round(s.longitude / cell))
        best = None
        for dlat in (-1, 0, 1):
            for dlng in (-1, 0, 1):
                for p in grid.get((ck[0] + dlat, ck[1] + dlng), []):
                    d = haversine(s.latitude, s.longitude, p["lat"], p["lng"])
                    if best is None or d < best[0]:
                        best = (d, p["dist"])
        if best and best[0] <= buffer_miles:
            near.append({"station": s, "dist_along": best[1], "detour": best[0]})

    near.sort(key=lambda x: x["dist_along"])
    return near


def plan_fuel_stops(near, total_distance, max_range, mpg):
    """
    Greedy cost-effective fuel plan: within each must-refuel window, pick the cheapest
    reachable station. Every hop is guaranteed <= max_range.
    """
    stops = []
    position = 0.0
    while total_distance - position > max_range:
        window = [n for n in near if position < n["dist_along"] <= position + max_range]
        if not window:
            raise ValueError(
                "No fuel station within range on this stretch of the route; "
                "cannot complete the trip with the available data."
            )
        cheapest = min(window, key=lambda n: n["station"].retail_price)
        stops.append(cheapest)
        position = cheapest["dist_along"]
    return stops


def compute_cost(stops, total_distance, mpg):
    """
    Total fuel = total_distance / mpg gallons.
    Each leg is billed at the price of the station that fueled that leg.
    The initial leg is billed at the first stop's price (assumed top-up on arrival).
    """
    total_gallons = total_distance / mpg
    if not stops:
        return 0.0, total_gallons, []

    boundaries = [0.0] + [s["dist_along"] for s in stops] + [total_distance]
    prices = [stops[0]["station"].retail_price] + [s["station"].retail_price for s in stops]

    total_cost, breakdown = 0.0, []
    for i in range(len(boundaries) - 1):
        leg = boundaries[i + 1] - boundaries[i]
        gallons = leg / mpg
        cost = gallons * prices[i]
        total_cost += cost
        breakdown.append({
            "from_mile": round(boundaries[i], 1),
            "to_mile": round(boundaries[i + 1], 1),
            "gallons": round(gallons, 2),
            "price_per_gallon": round(prices[i], 3),
            "leg_cost_usd": round(cost, 2),
        })
    return round(total_cost, 2), round(total_gallons, 2), breakdown
