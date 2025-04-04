import time
from machine import Pin
import dht

class TempHumidSensor:
    def __init__(self):
        self.last_read = time.ticks_ms()
        
        self.dht = dht.DHT22(Pin(15))
    
    def update(self, force=False):
        curr_time = time.ticks_ms()
        # limit to 1 read per second (arbitrary, to ease up the pins and make this less blocking)
        if (self.last_read + 10000) >= curr_time:
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
