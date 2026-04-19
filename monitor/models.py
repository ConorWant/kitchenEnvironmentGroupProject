from django.db import models


class SensorReading(models.Model):
    FRIDGE_TYPE_CHOICES = [
        ("fridge", "Fridge"),
        ("freezer", "Freezer"),
    ]

    timestamp = models.DateTimeField()
    temperature_c = models.FloatField()
    humidity_pct = models.FloatField()
    pressure_hpa = models.FloatField()
    door_status = models.CharField(max_length=16)
    light_lux = models.FloatField()
    fridge_type = models.CharField(max_length=16, choices=FRIDGE_TYPE_CHOICES)
    fridge_number = models.PositiveSmallIntegerField(default=1)
    safety_status = models.CharField(max_length=10, null=True, blank=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["fridge_type", "fridge_number", "-timestamp"]),
            models.Index(fields=["timestamp"]),
        ]

    def __str__(self):
        return (
            f"{self.timestamp:%Y-%m-%d %H:%M:%S} "
            f"{self.fridge_type}_{self.fridge_number} "
            f"{self.temperature_c:.2f}C"
        )


UNIT_TYPE_CHOICES = [
    ("fridge", "Fridge"),
    ("freezer", "Freezer"),
    ("fermentation_room", "Fermentation Room"),
    ("wine_cooler", "Wine Cooler"),
    ("dry_store", "Dry Store"),
    ("blast_chiller", "Blast Chiller"),
]


class MonitoredUnit(models.Model):
    unit_type = models.CharField(max_length=32, choices=UNIT_TYPE_CHOICES)
    unit_number = models.PositiveSmallIntegerField()
    datasette_table = models.CharField(max_length=64, unique=True)
    active = models.BooleanField(default=True)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("unit_type", "unit_number")
        ordering = ["unit_type", "unit_number"]

    def __str__(self):
        return f"{self.get_unit_type_display()} {self.unit_number} ({self.datasette_table})"