import asyncio
import network
from machine import Pin
import json
import time
from neopixel import NeoPixel
from mqtt import MQTT_Handler
class AsyncNode:
    def __init__(self, ssid=None, password=None):
        self.station = network.WLAN(network.STA_IF)
        self.ssid = ssid
        self.password = password
        self.data_queue = []
        self.connected = False
        self.init_neopixel()
        
    def init_neopixel(self):
        neo_power_pin = Pin(2, Pin.OUT)
        neo_power_pin.value(1)
        self.neopixel = NeoPixel(Pin(0), 1)
        self.neopixel.fill((25,0,0))  # Red indicates not connected
        self.neopixel.write()

    async def connect_wifi(self):
        drv_str = "WiFi Driver"
        print(f"{drv_str}: Connecting to WiFi")
        print(f"{drv_str}: Station is connected: {self.station.isconnected()}")
        if self.station.isconnected():
            print(f"{drv_str}: Already connected to WiFi")
            self.connected = True
            self.neopixel.fill((0,25,0))  # Green indicates connected
            self.neopixel.write()
            return True
        if not self.station.active():
            self.station.active(True)
            print(f"{drv_str}: initialized")
        
        while not self.station.isconnected():
            print(f'{drv_str}: Connecting to {self.ssid}...')
            try:
                self.station.connect(self.ssid, self.password)
            except Exception as e:
                print(f"{drv_str}: Error connecting to WiFi: {e}")
                self.neopixel.fill((25,0,0))  # Red indicates disconnected
                self.neopixel.write()
            

            # Wait for connection with timeout
            max_wait = 20
            while max_wait > 0:
                if self.station.isconnected():
                    break
                max_wait -= 1
                await asyncio.sleep(1)
            
            if self.station.isconnected():
                self.connected = True
                self.neopixel.fill((0,25,0))  # Green indicates connected
                self.neopixel.write()
                print(f'{drv_str}: Connected to WiFi')
                print(f'{drv_str}: Network config: {self.station.ifconfig()}')
            else:
                print(f'{drv_str}: Failed to connect')
                return False
        print(f"{drv_str}: Initialized")
        return True

    async def simulate_sensor_reading(self):
        while True:
            # Simulate reading from different sensors
            sensor_data = {
                'temperature': 20 + (time.time() % 10),
                'humidity': 50 + (time.time() % 20),
                'pressure': 1000 + (time.time() % 50)
            }
            self.data_queue.append(sensor_data)
            await asyncio.sleep(5)  # Read every 5 seconds

    async def transmit_data(self):
        while True:
            if self.data_queue and self.connected:
                data = self.data_queue.pop(0)
                # Simulate data transmission
                print(f'Transmitting data: {data}')
                # Here you would typically send the data to your server
                # using a protocol of your choice (MQTT, HTTP, etc.)
            await asyncio.sleep(1)

    async def connection_monitor(self):
        drv_str = "Connection Monitor"
        while True:
            if not self.station.isconnected():
                self.connected = False
                self.neopixel.fill((25,0,0))  # Red indicates disconnected
                self.neopixel.write()
                print(f"{drv_str}: WiFi disconnected, attempting to reconnect...")
                await self.connect_wifi()
            else:
                if self.neopixel[0] == (0,0,0):
                    self.neopixel.fill((0,25,0))  # Green indicates connected
                else:
                    self.neopixel.fill((0,0,0))  # Green indicates connected
                self.neopixel.write()
            #print(f"{drv_str}: {self.station.isconnected()}")
            await asyncio.sleep(1)
    async def mqtt_handler(self):
        drv_str = "MQTT Handler"
        mqtt_handler = MQTT_Handler(client_id="node_1", broker="N/A", port=1883, user="N/A", password="N/A")
        print(f"{drv_str}: MQTT handler initialized")
    async def run(self):
        drv_str = "Scheduler"
        # Create tasks for all our async functions
        wifi_task = asyncio.create_task(self.connect_wifi())
        print(f"{drv_str}: started wifi task")
        await wifi_task  # Wait for initial connection
        print(f"{drv_str}: wifi task completed")
        if self.connected:
            tasks = [
                asyncio.create_task(self.simulate_sensor_reading()),
                asyncio.create_task(self.transmit_data()),
                asyncio.create_task(self.connection_monitor()),
                asyncio.create_task(self.mqtt_handler())
            ]
            print(f"{drv_str}: starting tasks\n {tasks}")
            await asyncio.gather(*tasks)
            print(f"{drv_str}: tasks completed")
    

def main():
    node = AsyncNode(ssid="Tilins Nightclub", password="engineers123")
    print("Starting Scheduler")
    asyncio.run(node.run())
    print("Scheduler finished")

if __name__ == '__main__':
    main()