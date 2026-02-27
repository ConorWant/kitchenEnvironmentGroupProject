import csv
import time
import os
from datetime import datetime
import RPi.GPIO as GPIO
from smbus2 import SMBus
from bme280 import BME280

LOG_INTERVAL = 30
CSV_FILENAME = "sensor_log.csv"

GPIO.setmode(GPIO.BCM)
GPIO.setup(5, GPIO.IN, pull_up_down=GPIO.PUD_UP)

i2c_bus = SMBus(1)
bme280 = BME280(i2c_dev=i2c_bus)

file_exists = os.path.exisits(CSV_FILENAME)
csv_file = open(CSV_FILENAME, "a", newline="")
writer = csv.writer(csv_file)

if not file_exists:

    writer.writerow([
        "timestamp",
        "temperature_c",
        "humidity_pct",
        "pressure_hpa",
	"door_status",
	#"light_lux", DELETE COMMENT WHEN LIGHT SENSOR IS WORKING
    ])
    print("Created new log file:", CSV_FILENAME)
else:
    print("Appending to existing log file:", CSV_FILENAME)


def read_door_status(GPIO_pin):
	if GPIO.input(pin) ==  0:
		return "CLOSED"
	else:
		return "OPEN"

def read_bme_sensor:
	pass
	#BME sensor code goes here

def read_light_sensor:
	pass
	#Light sensor code goes here

# Main Loop goes here

# Cleanup code goes here
