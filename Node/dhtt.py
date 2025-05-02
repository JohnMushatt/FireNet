import time
from machine import Pin # type: ignore
import dht # type: ignore

class TempHumidSensor:
    def __init__(self, pin=15):
        self.last_read = time.ticks_ms() - 10000
        
        self.dht = dht.DHT22(Pin(pin))
    
    def update(self, force=False):
        curr_time = time.ticks_ms()
        # limit to 1 read per second (arbitrary, to ease up the pins and make this less blocking)
        if (self.last_read + 4500) >= curr_time:
            # already read within the last second
            return
        
        self.dht.measure()
        # Update last_read
        self.last_read = time.ticks_ms()
    
    def get_temp(self, update=True):
        self.update()
        return self.dht.temperature()
    
    def get_humidity(self, update=True):
        self.update()
        return self.dht.humidity()

d = TempHumidSensor()
