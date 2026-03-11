# Fridge Environment Project

This repository collects sensor data from a Raspberry Pi and provides a Django web interface for viewing it.

## Python / Django setup

1. Create & activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate   # or venv\Scripts\activate on Windows
   ```
2. Install dependencies:
   ```bash
   pip install django smbus2 spidev bme280 RPi.GPIO
   ```
3. Run migrations and create a superuser:
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```
4. Start the development server:
   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```

The web application will be available at `http://<pi-ip>:8000/`; the admin site is at `/admin`.

## Data ingestion

The `sensor_logger/sensor_logger.py` script writes readings to `sensor_log.csv` at regular
intervals. You can push those readings into Django by either:

* modifying `sensor_logger.py` to POST JSON to `http://localhost:8000/api/ingest/`
  after each measurement (see example below), or
* writing a Django management command that parses the CSV and creates `FridgeReading`
  records periodically.

### Example POST snippet

```python
import requests

def send_reading(temp, hum, pres, door, light):
    payload = {
        'temperature': temp,
        'humidity': hum,
        'pressure': pres,
        'door': door,
        'light': light,
    }
    requests.post('http://localhost:8000/api/ingest/', json=payload)
```

## Web interface

* The homepage `/` displays the latest 20 readings in a simple HTML table.
* You can extend `web_site/templates/web_site/latest.html` to add graphs (e.g. Chart.js)
  or implement filtering.
* The Django admin lets you inspect, filter and delete records once you've created a
  superuser.

Happy hacking!
