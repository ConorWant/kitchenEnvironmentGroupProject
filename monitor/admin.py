from django.contrib import admin

from .models import SensorReading


@admin.register(SensorReading)
class SensorReadingAdmin(admin.ModelAdmin):
    list_display = (
        "timestamp",
        "fridge_type",
        "fridge_number",
        "temperature_c",
        "humidity_pct",
        "pressure_hpa",
        "door_status",
        "light_lux",
    )
    list_filter = ("fridge_type", "fridge_number", "door_status", "timestamp")
    search_fields = ("door_status",)
    ordering = ("-timestamp",)
