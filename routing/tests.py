from django.test import TestCase
from routing.services.fuel_optimizer import (
    haversine, plan_fuel_stops, compute_cost,
)


class _Stub:
    def __init__(self, price):
        self.retail_price = price


def n(dist, price):
    return {"station": _Stub(price), "dist_along": dist, "detour": 0.0}


class OptimizerTests(TestCase):
    def test_haversine_known_distance(self):
        # NYC -> LA straight-line is ~2450 miles
        d = haversine(40.71, -74.00, 34.05, -118.24)
        self.assertTrue(2400 < d < 2500)

    def test_hops_never_exceed_range(self):
        near = [n(i * 100, 3.0 + (i % 3) * 0.1) for i in range(1, 30)]
        stops = plan_fuel_stops(near, total_distance=2800, max_range=500, mpg=10)
        positions = [0] + [s["dist_along"] for s in stops] + [2800]
        gaps = [b - a for a, b in zip(positions, positions[1:])]
        self.assertTrue(all(g <= 500 for g in gaps))

    def test_gallons_reconcile(self):
        near = [n(i * 100, 3.0) for i in range(1, 30)]
        stops = plan_fuel_stops(near, 2800, 500, 10)
        cost, gallons, _ = compute_cost(stops, 2800, 10)
        self.assertAlmostEqual(gallons, 280.0)
        self.assertAlmostEqual(cost, 280.0 * 3.0, places=2)
