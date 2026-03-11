from django.db import models


class FridgeReading(models.Model):
    """A single sensor snapshot from the refrigerator."""

    timestamp = models.DateTimeField(auto_now_add=True)
    temperature_c = models.DecimalField(max_digits=5, decimal_places=2)
    humidity_pct = models.DecimalField(max_digits=5, decimal_places=2)
    pressure_hpa = models.DecimalField(max_digits=7, decimal_places=2)
    door_status = models.CharField(
        max_length=10,
        choices=[('OPEN', 'OPEN'), ('CLOSED', 'CLOSED')],
        default='CLOSED',
    )
    light_level = models.IntegerField()

    def __str__(self):
        return f"{self.timestamp.isoformat()} {self.temperature_c}°C"
