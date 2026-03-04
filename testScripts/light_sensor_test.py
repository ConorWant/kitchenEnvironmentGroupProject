import spidev
import time

spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 500000
spi.mode = 0b00

def read_light():
    resp = spi.xfer2([0x00, 0x00])
    raw = (resp[0] << 8) | resp[1]
    value = (raw >> 2) & 0x3FF   # correct alignment
    return value

while True:
    lux = read_light()
    print(f"Light Level: {lux}")
    time.sleep(0.5)

