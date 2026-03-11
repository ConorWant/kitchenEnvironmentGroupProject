#!/usr/bin/env python3

import csv
import time
import os
from datetime import datetime
import RPi.GPIO as GPIO
from smbus2 import SMBus
from bme280 import BME280
import spidev

# optional: push data directly to the Django site
try:
    import requests
except ImportError:
    requests = None

API_URL = os.environ.get('DJANGO_API_URL', 'http://localhost:8000/api/ingest/')


def post_to_django(payload: dict):
    if requests is None:
        return
    try:
        requests.post(API_URL, json=payload, timeout=2)
    except Exception as exc:
        print('failed to send to django:', exc)

#Settings
LOG_INTERVAL = 10
CSV_FILENAME = "sensor_log.csv"
TEMP_OFFSET = -4

# Sensor initialization
GPIO.setmode(GPIO.BCM)
GPIO.setup(5, GPIO.IN, pull_up_down=GPIO.PUD_UP)

i2c_bus = SMBus(1)
bme280 = BME280(i2c_dev=i2c_bus)

spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 1000000
spi.mode = 0b00

# Sets up output file
file_exists = os.path.exists(CSV_FILENAME)
csv_file = open(CSV_FILENAME, "a", newline="")
writer = csv.writer(csv_file)

if not file_exists:
    writer.writerow([
        "timestamp",
        "temperature_c",
        "humidity_pct",
        "pressure_hpa",
        "door_status",
        "light_level",
    ])
    print("Created new log file:", CSV_FILENAME)
else:
    print("Appending to existing log file:", CSV_FILENAME)

# Helper functions
def read_door_status(pin):
    if GPIO.input(pin) == 0:
        return "CLOSED"
    else:
        return "OPEN"


def read_bme_sensor():
    temperature = round(bme280.get_temperature() + TEMP_OFFSET, 2)
    humidity    = round(bme280.get_humidity(), 2)
    pressure    = round(bme280.get_pressure(), 2)
    return temperature, humidity, pressure


def read_light_sensor():
    resp = spi.xfer2([0x00, 0x00])
    raw = ((resp[0] & 0x1F) << 8 | resp[1]) >> 1
    light = min(255, int(raw / 4096 * 255))
    return light


# Throws away first reading as it is unreliable
bme280.get_temperature()
time.sleep(2)
# Main loop
try:
    while True:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        temperature, humidity, pressure = read_bme_sensor()
        door = read_door_status(5)
        light = read_light_sensor()
        writer.writerow([timestamp, door, temperature, humidity, pressure, light])
        csv_file.flush()

        # optionally push the same reading into the Django database
        post_to_django({
            'temperature': temperature,
            'humidity': humidity,
            'pressure': pressure,
            'door': door,
            'light': light,
        })

        print(f"{timestamp} | Door Status: {door} | "
              f"Temp: {temperature}C | Humidity: {humidity}% | Pressure: {pressure}hPa | Light: {light}")
        time.sleep(LOG_INTERVAL)
# Cleanup
except KeyboardInterrupt:
    print("\nStopped.")

finally:
    csv_file.close()
    GPIO.cleanup()
    spi.close()
