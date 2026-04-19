#!/usr/bin/env python3
import csv
import time
import os
from datetime import datetime
import RPi.GPIO as GPIO
from smbus2 import SMBus
from bme280 import BME280
from ltr559 import LTR559
import sys
import requests

# Settings
FRIDGE_TYPE = sys.argv[1]
FRIDGE_NUMBER = sys.argv[2]
LOG_INTERVAL = 10
CSV_FILENAME = f"logs/sensor_log_{FRIDGE_TYPE}_{FRIDGE_NUMBER}.csv"
ERROR_LOG = f"error/error_log_{FRIDGE_TYPE}_{FRIDGE_NUMBER}.txt"
TEMP_OFFSET = -4

# API config
API_BASE = "https://dashboard.pilsworth.org/-/insert"
API_HEADERS = {
    "Authorization": "Bearer Team12FridgeFreezer",
    "Content-Type": "application/json"
}
API_ENDPOINT = f"sensor/{FRIDGE_TYPE}_{FRIDGE_NUMBER}"

# Error logging
def log_error(source, error):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = f"{timestamp} | [{source}] {error}\n"
    print(message.strip())
    with open(ERROR_LOG, "a") as f:
        f.write(message)

# Sensor initialisation
GPIO.setmode(GPIO.BCM)
GPIO.setup(5, GPIO.IN, pull_up_down=GPIO.PUD_UP)

try:
    i2c_bus = SMBus(1)
    bme280 = BME280(i2c_dev=i2c_bus)
    ltr559 = LTR559()
except Exception as e:
    log_error("INIT ERROR", e)
    sys.exit(1)

# Sets up output file
try:
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
            "light_lux",
        ])
        print("Created new log file:", CSV_FILENAME)
    else:
        print("Appending to existing log file:", CSV_FILENAME)
except Exception as e:
    log_error("CSV ERROR", e)
    sys.exit(1)

# Helper functions
def post_to_api(timestamp, temperature, humidity, pressure, door, light):
    payload = [{
        "timestamp": timestamp,
        "recorded_at": timestamp[:16],
        "temperature_c": temperature,
        "humidity_pct": humidity,
        "pressure_hpa": pressure,
        "door_status": door,
        "light_lux": light
    }]
    try:
        r = requests.post(API_BASE + "/" + API_ENDPOINT, headers=API_HEADERS, json=payload, timeout=10)
        r.raise_for_status()
        print(f"[API OK] Posted to {API_ENDPOINT}")
    except requests.RequestException as e:
        log_error("API FAIL", e)

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
    ltr559.update_sensor()
    lux = round(ltr559.get_lux(), 2)
    return lux

# Throws away first reading as it is unreliable
bme280.get_temperature()
time.sleep(2)

# Main loop
try:
    while True:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            temperature, humidity, pressure = read_bme_sensor()
            door = read_door_status(5)
            light = read_light_sensor()
        except Exception as e:
            log_error("SENSOR ERROR", e)
            time.sleep(LOG_INTERVAL)
            continue

        writer.writerow([timestamp, temperature, humidity, pressure, door, light])
        csv_file.flush()

        post_to_api(timestamp, temperature, humidity, pressure, door, light)

        print(f"{timestamp} | Door Status: {door} | "
              f"Temp: {temperature}C | Humidity: {humidity}% | "
              f"Pressure: {pressure}hPa | Light: {light} lux")

        time.sleep(LOG_INTERVAL)

# Cleanup
except KeyboardInterrupt:
    print("\nStopped.")
finally:
    csv_file.close()
    GPIO.cleanup()
    print("Cleanup done. Data saved to:", CSV_FILENAME)
