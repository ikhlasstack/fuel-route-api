import csv
from django.core.management.base import BaseCommand, CommandError
from routing.models import FuelStation


def first(row, *names):
    """Return the first present, non-empty value among candidate header names."""
    for n in names:
        if n in row and row[n]:
            return row[n]
    return ""


class Command(BaseCommand):
    help = "Load fuel-price CSV and geocode each station via an offline US-cities table."

    def add_arguments(self, parser):
        parser.add_argument("--fuel", default="data/fuel-prices-for-be-assessment.csv")
        parser.add_argument("--cities", default="data/uscities.csv")

    def handle(self, *args, **opts):
        # 1) Build {(city_lower, STATE): (lat, lng)} from the offline cities table.
        city_lookup = {}
        try:
            with open(opts["cities"], newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    try:
                        key = (row["city"].strip().lower(), row["state_id"].strip().upper())
                        city_lookup[key] = (float(row["lat"]), float(row["lng"]))
                    except (KeyError, ValueError):
                        continue
        except FileNotFoundError:
            raise CommandError(f"Cities file not found: {opts['cities']}")
        self.stdout.write(f"Loaded {len(city_lookup)} city coordinates.")

        # 2) Read the fuel CSV and build FuelStation rows.
        FuelStation.objects.all().delete()
        objs, matched, missed = [], 0, 0
        try:
            f = open(opts["fuel"], newline="", encoding="utf-8-sig")
        except FileNotFoundError:
            raise CommandError(f"Fuel file not found: {opts['fuel']}")

        with f:
            for raw in csv.DictReader(f):
                row = {(k or "").strip().lower(): (v or "").strip() for k, v in raw.items()}

                price_raw = first(row, "retail price", "price", "retail_price")
                try:
                    price = float(price_raw)
                except ValueError:
                    continue

                city = first(row, "city")
                state = first(row, "state")
                lat = lng = None
                coords = city_lookup.get((city.lower(), state.upper()))
                if coords:
                    lat, lng = coords
                    matched += 1
                else:
                    missed += 1

                objs.append(FuelStation(
                    opis_id=first(row, "opis truckstop id", "opis_id"),
                    name=first(row, "truckstop name", "name"),
                    address=first(row, "address"),
                    city=city,
                    state=state,
                    rack_id=first(row, "rack id", "rack_id"),
                    retail_price=price,
                    latitude=lat,
                    longitude=lng,
                ))

        FuelStation.objects.bulk_create(objs, batch_size=1000)
        self.stdout.write(self.style.SUCCESS(
            f"Created {len(objs)} stations. Geocoded {matched}, missed {missed}."
        ))
