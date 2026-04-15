import csv
import re
from datetime import datetime
from pathlib import Path

from .models import SensorReading

#TEMPERATURE_MIN = 0
#TEMPERATURE_MAX = 8
#PRESSURE_MIN = 950
#PRESSURE_MAX = 1050
#HUMIDITY_MIN = 20
#HUMIDITY_MAX = 80

CSV_DIR = Path(__file__).resolve().parent.parent / "sensor_logger"
CSV_PATTERN = re.compile(r"sensor_log_(fridge|freezer)_(\d+)\.csv$")


def _source_slug(fridge_type, fridge_number):
    return f"{fridge_type}_{fridge_number}"


def _source_label(fridge_type, fridge_number):
    return f"{fridge_type.capitalize()} {fridge_number}"


def classify_reading(temp_c, lux):
    return "Unsafe" if (temp_c > 8.0 or lux > 200.0) else "Safe"


def _parse_csv_reading(row, fridge_type, fridge_number):
    temp_c = float(row["temperature_c"])
    lux = float(row["light_lux"])
    return {
        "timestamp": datetime.strptime(row["timestamp"], "%Y-%m-%d %H:%M:%S"),
        "temperature_c": temp_c,
        "humidity_pct": float(row["humidity_pct"]),
        "pressure_hpa": float(row["pressure_hpa"]),
        "door_status": row["door_status"],
        "light_lux": lux,
        "fridge_type": fridge_type,
        "fridge_number": int(fridge_number),
        "safety_status": classify_reading(temp_c, lux),
    }


def _db_readings(selected_source, sort_order, door_filter):
    qs = SensorReading.objects.all()

    if selected_source != "all":
        fridge_type, fridge_number = selected_source.split("_", maxsplit=1)
        qs = qs.filter(fridge_type=fridge_type, fridge_number=int(fridge_number))

    if door_filter != "all":
        qs = qs.filter(door_status__iexact=door_filter)

    order_by = "timestamp" if sort_order == "asc" else "-timestamp"
    readings = list(
        qs.order_by(order_by).values(
            "timestamp",
            "temperature_c",
            "humidity_pct",
            "pressure_hpa",
            "door_status",
            "light_lux",
            "fridge_type",
            "fridge_number",
            "safety_status",
        )
    )

    sources = sorted(
        {
            _source_slug(item["fridge_type"], item["fridge_number"])
            for item in SensorReading.objects.values("fridge_type", "fridge_number").distinct()
        }
    )

    return readings, sources


def _csv_readings(selected_source, sort_order, door_filter):
    readings = []
    sources = set()

    for csv_path in CSV_DIR.glob("sensor_log_*.csv"):
        match = CSV_PATTERN.match(csv_path.name)
        if not match:
            continue

        fridge_type, fridge_number = match.group(1), int(match.group(2))
        current_slug = _source_slug(fridge_type, fridge_number)
        sources.add(current_slug)

        if selected_source != "all" and current_slug != selected_source:
            continue

        with csv_path.open(newline="", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                parsed = _parse_csv_reading(row, fridge_type, fridge_number)
                if door_filter != "all" and parsed["door_status"].upper() != door_filter.upper():
                    continue
                readings.append(parsed)

    readings.sort(key=lambda row: row["timestamp"], reverse=sort_order != "asc")
    return readings, sorted(sources)


def get_readings(selected_source="all", sort_order="desc", door_filter="all", limit=None):
    has_db_data = SensorReading.objects.exists()

    if has_db_data:
        readings, sources = _db_readings(selected_source, sort_order, door_filter)
        using_csv = False
    else:
        readings, sources = _csv_readings(selected_source, sort_order, door_filter)
        using_csv = True

    if limit is not None:
        readings = readings[:limit]

    source_options = [{"slug": "all", "label": "All Units"}] + [
        {"slug": slug, "label": _source_label(*slug.split("_", maxsplit=1))} for slug in sources
    ]

    return {
        "readings": readings,
        "sources": source_options,
        "using_csv": using_csv,
        "has_data": bool(readings),
    }


def build_summary(readings):
    if not readings:
        return {
            "latest": None,
            "avg_temp": None,
            "avg_humidity": None,
            "avg_pressure": None,
            "open_events": 0,
        }

    latest = readings[0]
    count = len(readings)

    return {
        "latest": latest,
        "avg_temp": sum(r["temperature_c"] for r in readings) / count,
        "avg_humidity": sum(r["humidity_pct"] for r in readings) / count,
        "avg_pressure": sum(r["pressure_hpa"] for r in readings) / count,
        "open_events": sum(1 for r in readings if str(r["door_status"]).upper() == "OPEN"),
        "latest_status": readings[0].get("safety_status") if readings else None,
    }

#def is_anomalous(reading):
    #return (
       # reading.temperature_c < TEMPERATURE_MIN or reading.temperature_c > TEMPERATURE_MAX or
       # reading.pressure_hpa < PRESSURE_MIN or reading.pressure_hpa > PRESSURE_MAX or
       # reading.humidity_pct < HUMIDITY_MIN or reading.humidity_pct > HUMIDITY_MAX
    #)