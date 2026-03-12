#!/usr/bin/env python3

# =====================================================================
# LTR-559 LIGHT & PROXIMITY SENSOR - TEST SCRIPT
# =====================================================================
# This script reads light level (lux) and proximity from the LTR-559
# every second and prints it to the screen.
#
# WIRING:
#   The LTR-559 uses I2C - just plug it into one of the I2C slots
#   on the Breakout Garden and it will work automatically.
#
# If you see lux values changing as you cover/uncover the sensor,
# and proximity values changing as you move your hand close,
# it is working correctly.
#
# Install the library first:
#   pip3 install ltr559 --break-system-packages
# =====================================================================

import time
from ltr559 import LTR559

# Create an LTR559 object - this initialises the sensor
ltr559 = LTR559()

print("LTR-559 Test - reading light and proximity every second.")
print("Cover the sensor with your hand to see values change.")
print("Press Ctrl+C to stop.\n")

try:
    while True:

        # update_sensor() reads fresh data from the sensor
        ltr559.update_sensor()

        # get_lux() returns the light level in lux
        # lux is a standard unit of light - 0 is dark, 64000 is very bright
        lux = ltr559.get_lux()

        # get_proximity() returns a proximity value
        # 0 = nothing nearby, higher values = something is close
        proximity = ltr559.get_proximity()

        # Simple visual bar to make changes easy to see
        bar = "#" * min(40, int(lux / 100))

        print(f"Lux: {lux:8.2f} | Proximity: {proximity:4d} | {bar}")

        time.sleep(1)

except KeyboardInterrupt:
    print("\nStopped.")
