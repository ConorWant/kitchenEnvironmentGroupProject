import csv
import json
import subprocess
import tempfile
from pathlib import Path

from django.core.management.base import BaseCommand

from monitor.models import SensorReading

RSCRIPT = "Rscript"  # adjust to full path if needed, e.g. r"C:\Program Files\R\R-4.x.x\bin\Rscript.exe"
R_SCRIPT = Path(__file__).resolve().parents[4] / "kitchen_classifier.R"


class Command(BaseCommand):
    help = "Classify sensor readings using the R Random Forest model"

    def handle(self, *args, **options):
        readings = list(SensorReading.objects.values(
            "id", "timestamp", "temperature_c", "light_lux",
            "fridge_type", "fridge_number"
        ))
        if not readings:
            self.stdout.write("No readings to classify.")
            return

        with tempfile.TemporaryDirectory() as tmpdir:
            input_csv = Path(tmpdir) / "input.csv"
            output_json = Path(tmpdir) / "output.json"

            # Write CSV for R
            with input_csv.open("w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=[
                    "timestamp", "temperature_c", "light_lux",
                    "fridge_type", "fridge_number"
                ])
                writer.writeheader()
                for r in readings:
                    writer.writerow({
                        "timestamp": r["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
                        "temperature_c": r["temperature_c"],
                        "light_lux": r["light_lux"],
                        "fridge_type": r["fridge_type"],
                        "fridge_number": r["fridge_number"],
                    })

            # Run R script
            result = subprocess.run(
                [RSCRIPT, str(R_SCRIPT), str(input_csv), str(output_json)],
                capture_output=True, text=True
            )
            if result.returncode != 0:
                self.stderr.write(f"R error:\n{result.stderr}")
                return

            self.stdout.write(result.stdout.strip())

            # Read output and update DB
            classifications = json.loads(output_json.read_text())
            lookup = {
                (row["timestamp"], row["fridge_type"], int(row["fridge_number"])): row["status"]
                for row in classifications
            }

            to_update = []
            for r in readings:
                key = (
                    r["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
                    r["fridge_type"],
                    r["fridge_number"],
                )
                status = lookup.get(key)
                if status:
                    to_update.append(SensorReading(id=r["id"], safety_status=status))

            SensorReading.objects.bulk_update(to_update, ["safety_status"])
            self.stdout.write(f"Updated {len(to_update)} readings.")
