import folium
from django.core.cache import cache
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response

from routing.services.trip import plan_trip


class RouteAPIView(APIView):
    """GET /api/route/?start=<place>&finish=<place>"""

    def get(self, request):
        start = request.query_params.get("start")
        finish = request.query_params.get("finish")
        if not start or not finish:
            return Response(
                {"error": "Provide both 'start' and 'finish' query parameters."},
                status=400,
            )

        cache_key = f"route:{start.lower()}|{finish.lower()}"
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        try:
            result = plan_trip(start, finish)
        except ValueError as e:
            return Response({"error": str(e)}, status=400)

        cache.set(cache_key, result, 60 * 60)
        return Response(result)


class RouteMapView(APIView):
    """GET /api/route/map/?start=<place>&finish=<place> -> interactive HTML map"""

    def get(self, request):
        start = request.query_params.get("start")
        finish = request.query_params.get("finish")
        if not start or not finish:
            return HttpResponse("Provide 'start' and 'finish'.", status=400)

        try:
            result = plan_trip(start, finish)
        except ValueError as e:
            return HttpResponse(str(e), status=400)

        line = [[lat, lng] for lng, lat in result["route_geometry"]["coordinates"]]
        mid = line[len(line) // 2]

        fmap = folium.Map(location=mid, zoom_start=5)
        folium.PolyLine(line, weight=4, opacity=0.8).add_to(fmap)
        folium.Marker(line[0], tooltip="Start",
                      icon=folium.Icon(color="green")).add_to(fmap)
        folium.Marker(line[-1], tooltip="Finish",
                      icon=folium.Icon(color="red")).add_to(fmap)
        for i, stop in enumerate(result["fuel_stops"], 1):
            folium.Marker(
                [stop["lat"], stop["lng"]],
                tooltip=(f"Stop {i}: {stop['name']} "
                         f"(${stop['price_per_gallon']}/gal)"),
                icon=folium.Icon(color="blue", icon="tint", prefix="fa"),
            ).add_to(fmap)

        return HttpResponse(fmap._repr_html_())
