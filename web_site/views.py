from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

from .models import FridgeReading


def latest_readings(request, count: int = 20):
    # show most recent `count` readings
    readings = FridgeReading.objects.order_by('-timestamp')[:count]
    return render(request, 'web_site/latest.html', {'readings': readings})


@csrf_exempt
def ingest_reading(request):
    """Simple API endpoint that accepts JSON POSTs from the RPis sensor logger."""

    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'malformed json'}, status=400)

    # assume keys temperature, humidity, pressure, door, light
    FridgeReading.objects.create(
        temperature_c=data.get('temperature'),
        humidity_pct=data.get('humidity'),
        pressure_hpa=data.get('pressure'),
        door_status=data.get('door', 'CLOSED'),
        light_level=data.get('light', 0),
    )
    return JsonResponse({'status': 'ok'})
