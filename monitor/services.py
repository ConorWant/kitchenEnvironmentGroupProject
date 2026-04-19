import csv
import re
from datetime import datetime
from pathlib import Path
from django.utils.timezone import is_aware, make_naive
from .models import MonitoredUnit, SensorReading

CSV_DIR = Path(__file__).resolve().parent.parent / "sensor_logger"
CSV_PATTERN = re.compile(r"sensor_log_(.+)_(\d+)\.csv$")

UNIT_THRESHOLDS = {
    "fridge": {
        "temp_min": 0, "temp_max": 8,
        "humidity_min": None, "humidity_max": None,
        "lux_max": 200,
    },
    "freezer": {
        "temp_min": -25, "temp_max": -12,
        "humidity_min": None, "humidity_max": None,
        "lux_max": 200,
    },
    "blast_chiller": {
        "temp_min": -2, "temp_max": 5,
        "humidity_min": None, "humidity_max": None,
        "lux_max": 200,
    },
    "wine_cooler": {
        "temp_min": 7, "temp_max": 18,
        "humidity_min": 50, "humidity_max": 80,
        "lux_max": 50,
    },
    "fermentation_room": {
        "temp_min": 10, "temp_max": 35,
        "humidity_min": 40, "humidity_max": 80,
        "lux_max": 50,
    },
    "dry_store": {
        "temp_min": 5, "temp_max": 21,
        "humidity_min": 30, "humidity_max": 60,
        "lux_max": 200,
    },
}


def classify_reading(temp_c, lux, humidity=None, unit_type="fridge"):
    thresholds = UNIT_THRESHOLDS.get(unit_type, UNIT_THRESHOLDS["fridge"])

    if temp_c < thresholds["temp_min"] or temp_c > thresholds["temp_max"]:
        return "Unsafe"
    if thresholds["lux_max"] is not None and lux > thresholds["lux_max"]:
        return "Unsafe"
    if humidity is not None:
        if thresholds["humidity_min"] is not None and humidity < thresholds["humidity_min"]:
            return "Unsafe"
        if thresholds["humidity_max"] is not None and humidity > thresholds["humidity_max"]:
            return "Unsafe"
    return "Safe"


def _source_label(fridge_type, fridge_number):
    label_map = {
        "fridge": "Fridge",
        "freezer": "Freezer",
        "fermentation_room": "Fermentation Room",
        "wine_cooler": "Wine Cooler",
        "dry_store": "Dry Store",
        "blast_chiller": "Blast Chiller",
    }
    label = label_map.get(fridge_type, fridge_type.replace("_", " ").title())
    return f"{label} {fridge_number}"


def _parse_csv_reading(row, fridge_type, fridge_number):
    temp_c = float(row["temperature_c"])
    lux = float(row["light_lux"])
    humidity = float(row["humidity_pct"])
    return {
        "timestamp": datetime.strptime(row["timestamp"], "%Y-%m-%d %H:%M:%S"),
        "temperature_c": temp_c,
        "humidity_pct": humidity,
        "pressure_hpa": float(row["pressure_hpa"]),
        "door_status": row["door_status"],
        "light_lux": lux,
        "fridge_type": fridge_type,
        "fridge_number": int(fridge_number),
        "safety_status": classify_reading(temp_c, lux, humidity, fridge_type),
    }


def _csv_readings_for_unit(fridge_type, fridge_number):
    readings = []
    csv_path = CSV_DIR / f"sensor_log_{fridge_type}_{fridge_number}.csv"
    if not csv_path.exists():
        csv_path = CSV_DIR / "logs" / f"sensor_log_{fridge_type}_{fridge_number}.csv"
    if not csv_path.exists():
        return readings
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            readings.append(_parse_csv_reading(row, fridge_type, fridge_number))
    return readings


def _get_readings_for_unit(fridge_type, fridge_number, sort_order, door_filter):
    qs = SensorReading.objects.filter(
        fridge_type=fridge_type,
        fridge_number=fridge_number,
    )
    if door_filter != "all":
        qs = qs.filter(door_status__iexact=door_filter)

    if qs.exists():
        order_by = "timestamp" if sort_order == "asc" else "-timestamp"
        return list(qs.order_by(order_by).values(
            "timestamp", "temperature_c", "humidity_pct", "pressure_hpa",
            "door_status", "light_lux", "fridge_type", "fridge_number", "safety_status",
        )), False
    else:
        readings = _csv_readings_for_unit(fridge_type, fridge_number)
        if door_filter != "all":
            readings = [r for r in readings if r["door_status"].upper() == door_filter.upper()]
        readings.sort(key=lambda r: r["timestamp"], reverse=sort_order != "asc")
        return readings, True


def _normalize_ts(ts):
    if hasattr(ts, 'tzinfo') and is_aware(ts):
        return make_naive(ts)
    return ts


def get_readings(selected_source="all", sort_order="desc", door_filter="all", limit=None):
    all_units = MonitoredUnit.objects.filter(active=True).order_by("unit_type", "unit_number")

    if selected_source == "all":
        units_to_fetch = [(u.unit_type, u.unit_number) for u in all_units]
    else:
        fridge_type, fridge_number = selected_source.rsplit("_", maxsplit=1)
        units_to_fetch = [(fridge_type, int(fridge_number))]

    all_readings = []
    using_csv = False

    for fridge_type, fridge_number in units_to_fetch:
        readings, from_csv = _get_readings_for_unit(fridge_type, fridge_number, sort_order, door_filter)
        all_readings.extend(readings)
        if from_csv:
            using_csv = True

    all_readings.sort(
        key=lambda r: _normalize_ts(r["timestamp"]),
        reverse=sort_order != "asc"
    )

    if limit is not None and limit > 0:
        all_readings = all_readings[:limit]
    elif limit == 0:
        all_readings = []

    source_options = [{"slug": "all", "label": "All Units"}] + [
        {
            "slug": f"{u.unit_type}_{u.unit_number}",
            "label": f"{u.get_unit_type_display()} {u.unit_number}",
        }
        for u in all_units
    ]

    return {
        "readings": all_readings,
        "sources": source_options,
        "using_csv": using_csv,
        "has_data": bool(all_readings),
    }


def build_summary(readings):
    if not readings:
        return {
            "latest": None,
            "avg_temp": None,
            "avg_humidity": None,
            "avg_pressure": None,
            "open_events": 0,
            "latest_status": None,
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