import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM) # Use BCM chip numbering instead of physical numbering
GPIO.setup(5, GPIO.IN, pull_up_down=GPIO.PUD_UP) # Sets gpio 5 is the input, it reads 1 by default, ans 0 when door is closed

try:
    while True:
        sensor = GPIO.input(5)
        print(f"Door sensor: {'CLOSED' if sensor == 0 else 'OPEN'}", end='\r')
        time.sleep(0.1)
except KeyboardInterrupt:
    GPIO.cleanup() # Resets pins on ctrl-c 
