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

# Settings
FRIDGE_TYPE = sys.argv[1]
FRIDGE_NUMBER = sys.argv[2]
LOG_INTERVAL = 10
CSV_FILENAME = "sensor_log" + "_" + FRIDGE_TYPE + "_" + FRIDGE_NUMBER + ".csv"
TEMP_OFFSET  = -7

# Database config (optional — set these env vars to enable direct DB writes)
DB_NAME     = os.getenv("DB_NAME")
DB_USER     = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST     = os.getenv("DB_HOST", "localhost")
DB_PORT     = os.getenv("DB_PORT", "5432")

db_conn = None
if DB_NAME:
    try:
        import psycopg2
        db_conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
        )
        db_conn.autocommit = True
        print("Connected to database.")
    except Exception as e:
        print(f"Warning: could not connect to database ({e}). Falling back to CSV only.")
        db_conn = None


def insert_db(timestamp, temperature, humidity, pressure, door, light):
    if db_conn is None:
        return
    with db_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO monitor_sensorreading
                (timestamp, temperature_c, humidity_pct, pressure_hpa,
                 door_status, light_lux, fridge_type, fridge_number, safety_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                timestamp,
                temperature,
                humidity,
                pressure,
                door,
                light,
                FRIDGE_TYPE,
                int(FRIDGE_NUMBER),
                None,  # safety_status classified separately by R script
            ),
        )


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

        insert_db(timestamp, temperature, humidity, pressure, door, light)

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
    if db_conn:
        db_conn.close()
    print("Cleanup done. Data saved to:", CSV_FILENAME)
