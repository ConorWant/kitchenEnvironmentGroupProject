#!/usr/bin/env python3

import csv
import time
import os
from datetime import datetime
import RPi.GPIO as GPIO
from smbus2 import SMBus
from bme280 import BME280
from ltr559 import LTR559

# Settings
LOG_INTERVAL = 10
CSV_FILENAME = "sensor_log.csv"
TEMP_OFFSET  = -7

# Sensor initialization
GPIO.setmode(GPIO.BCM)
GPIO.setup(5, GPIO.IN, pull_up_down=GPIO.PUD_UP)

i2c_bus = SMBus(1)
bme280  = BME280(i2c_dev=i2c_bus)
ltr559  = LTR559()

# Sets up output file
file_exists = os.path.exists(CSV_FILENAME)
csv_file    = open(CSV_FILENAME, "a", newline="")
writer      = csv.writer(csv_file)

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
        temperature, humidity, pressure = read_bme_sensor()
        door  = read_door_status(5)
        light = read_light_sensor()

        writer.writerow([timestamp, temperature, humidity, pressure, door, light])
        csv_file.flush()

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
