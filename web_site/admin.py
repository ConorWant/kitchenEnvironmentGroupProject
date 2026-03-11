from django.contrib import admin

from .models import FridgeReading


@admin.register(FridgeReading)
class FridgeReadingAdmin(admin.ModelAdmin):
    list_display = (
        'timestamp',
        'temperature_c',
        'humidity_pct',
        'pressure_hpa',
        'door_status',
        'light_level',
    )
    list_filter = ('door_status',)
    ordering = ('-timestamp',)
