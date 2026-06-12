from django.conf import settings
from routing.models import FuelStation
from .geocoding import geocode_place
from .routing_api import get_route
from .fuel_optimizer import (
    build_route_points, downsample, stations_near_route,
    plan_fuel_stops, compute_cost,
)


def plan_trip(start, finish):
    s_lat, s_lng = geocode_place(start)
    f_lat, f_lng = geocode_place(finish)

    coords, _ = get_route(s_lat, s_lng, f_lat, f_lng)
    points = build_route_points(coords)
    total_distance = points[-1]["dist"]

    sampled = downsample(points, step_miles=5.0)
    stations = list(FuelStation.objects.exclude(latitude__isnull=True))
    near = stations_near_route(sampled, stations, buffer_miles=5.0)

    stops = plan_fuel_stops(
        near, total_distance,
        max_range=settings.VEHICLE_RANGE_MILES,
        mpg=settings.VEHICLE_MPG,
    )
    total_cost, total_gallons, breakdown = compute_cost(
        stops, total_distance, mpg=settings.VEHICLE_MPG,
    )

    return {
        "start": {"query": start, "lat": s_lat, "lng": s_lng},
        "finish": {"query": finish, "lat": f_lat, "lng": f_lng},
        "total_distance_miles": round(total_distance, 1),
        "vehicle": {
            "range_miles": settings.VEHICLE_RANGE_MILES,
            "mpg": settings.VEHICLE_MPG,
        },
        "total_gallons": total_gallons,
        "total_fuel_cost_usd": total_cost,
        "fuel_stops": [
            {
                "name": s["station"].name,
                "address": s["station"].address,
                "city": s["station"].city,
                "state": s["station"].state,
                "price_per_gallon": round(s["station"].retail_price, 3),
                "distance_along_route_miles": round(s["dist_along"], 1),
                "detour_miles": round(s["detour"], 2),
                "lat": s["station"].latitude,
                "lng": s["station"].longitude,
            }
            for s in stops
        ],
        "cost_breakdown": breakdown,
        "route_geometry": {"type": "LineString", "coordinates": coords},
    }
