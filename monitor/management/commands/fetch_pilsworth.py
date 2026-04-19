import requests
from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_datetime
from django.utils.timezone import make_aware
from monitor.models import SensorReading
from monitor.services import classify_reading

API_BASE = "https://dashboard.pilsworth.org/sensor"
API_HEADERS = {"Authorization": "Bearer Team12FridgeFreezer"}
TABLES = [
    ("fridge", 1),
    ("freezer", 1),
]

class Command(BaseCommand):
    help = "Fetch latest readings from Pilsworth Datasette API"

    def handle(self, *args, **options):
        for fridge_type, fridge_number in TABLES:
            table = f"{fridge_type}_{fridge_number}"
            total_created = 0

            while True:
                latest = SensorReading.objects.filter(
                    fridge_type=fridge_type,
                    fridge_number=fridge_number
                ).order_by("-timestamp").first()

                if latest:
                    after = latest.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                    url = f"{API_BASE}/{table}.json?_shape=array&_order=timestamp&timestamp__gt={after}&_size=1000"
                else:
                    url = f"{API_BASE}/{table}.json?_shape=array&_order=timestamp&_size=1000"

                try:
                    self.stdout.write(f"[URL] {url}")
                    r = requests.get(url, headers=API_HEADERS, timeout=10)
                    r.raise_for_status()
                    rows = r.json()
                except Exception as e:
                    self.stderr.write(f"[FAIL] {table}: {e}")
                    break

                if not rows:
                    break

                for row in rows:
                    ts = parse_datetime(row["timestamp"])
                    if ts is None:
                        continue
                    if ts.tzinfo is None:
                        ts = make_aware(ts)
                    SensorReading.objects.create(
                        timestamp=ts,
                        temperature_c=row["temperature_c"],
                        humidity_pct=row["humidity_pct"],
                        pressure_hpa=row["pressure_hpa"],
                        door_status=row["door_status"],
                        light_lux=row["light_lux"],
                        fridge_type=fridge_type,
                        fridge_number=fridge_number,
                        safety_status=classify_reading(row["temperature_c"], row["light_lux"]),
                    )
                    total_created += 1

                self.stdout.write(f"[OK] {table}: {total_created} rows so far...")

                if len(rows) < 1000:
                    break  # last page

            self.stdout.write(f"[DONE] {table}: {total_created} total new readings saved")