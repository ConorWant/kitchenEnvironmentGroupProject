import board
import busio
import adafruit_bme280.basic as adafruit_bme280

i2c = busio.I2C(board.SCL, board.SDA)

sensor = adafruit_bme280.Adafruit_BME280_I2C(i2c, address=0x76)

print("Temperature: ", sensor.temperature)
print("Humidity: " , sensor.humidity)
print("pressure: ", sensor.pressure)
