import asyncio
import socket
import network
from machine import Pin
import json
import time
from neopixel import NeoPixel
def is_micropython():
    """Returns True if running on MicroPython (ESP32, etc.)"""
    try:
        from machine import Pin
        return True
    except ImportError:
        return False
class AsyncNode:
    def __init__(self, ssid=None, password=None):
        self.wlan= network.WLAN(network.STA_IF)
        self.ssid = ssid
        self.password = password
        self.data_queue = []
        self.connected = False
        self.server_ip = "192.168.0.94"  # Replace with your server's IP address
        self.server_port = 8765 
        self.init_neopixel()
        
    def init_neopixel(self):
        neo_power_pin = Pin(2, Pin.OUT)
        neo_power_pin.value(1)
        self.neopixel = NeoPixel(Pin(0), 1)
        self.neopixel.fill((25,0,0))  # Red indicates not connected
        self.neopixel.write()

    async def wifi_driver_init(self):
        drv_str = "WiFi Driver"
        

        #check if already connected
        if self.wlan.isconnected():
            print(f"{drv_str}: Already connected to WiFi, disconnecting and restarting connection process")
            self.wlan.disconnect()
            time.sleep(1)
        print(f"{drv_str}: Connecting to WiFi network {self.ssid}")
        #connect to wifi
        reconnect_count = 0
        while  reconnect_count < 5 and not self.wlan.isconnected():
            self.wlan.connect(self.ssid, self.password)
            time.sleep(1)
            #print(f"Connected? {self.wlan.isconnected()}")
            if self.wlan.isconnected():
                print("Connected to WiFi")
                self.neopixel.fill((0,25,0))  # Green indicates connected
                self.neopixel.write()
                print(f'{drv_str}: Connected to WiFi')
                self.connected = True
                return True
            else:
                print(f'{drv_str}: Failed to connect')
                reconnect_count += 1
        print(f'{drv_str}: Failed to connect to WiFi after {reconnect_count} attempts')
        return False

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
                json_data = json.dumps(data) + '\n'
                print(f'Transmitting data: {json_data} to {self.server_ip}:{self.server_port}')

                self.socket.send(json_data.encode('utf-8'))

                resp = self.socket.recv(1024)
                resp = json.loads(resp)
                if resp['status'] == 'msg_received':
                    print(f'Data received from central compute node @ {resp["timestamp"]}')
                else:
                    print(f'Data not received from central compute node')
                # Here you would typically send the data to your server
                # using a protocol of your choice (MQTT, HTTP, etc.)
            await asyncio.sleep(5)

    async def connection_monitor(self):
        drv_str = "Connection Monitor"
        while True:
            if not self.wlan.isconnected():
                self.connected = False
                self.neopixel.fill((25,0,0))  # Red indicates disconnected
                self.neopixel.write()
                print(f"{drv_str}: WiFi disconnected, attempting to reconnect...")
                await self.wifi_driver_init()
            else:
                if self.neopixel[0] == (0,0,0):
                    self.neopixel.fill((0,25,0))  # Green indicates connected
                else:
                    self.neopixel.fill((0,0,0))  # Green indicates connected
                self.neopixel.write()
            #print(f"{drv_str}: {self.station.isconnected()}")
            await asyncio.sleep(1)
   
    async def socket_driver_init(self):
        drv_str = "Socket Driver"
        print(f"{drv_str}: setting up socket to central compute node")

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.addrinfo = socket.getaddrinfo(self.server_ip, self.server_port)
        self.socket.connect(self.addrinfo[0][-1])
        print(f"{drv_str}: socket connected to {self.server_ip}:{self.server_port}")
        #covert to json
        resp = self.socket.recv(1024)
        resp = json.loads(resp)
        if resp['client_id']:
            self.client_id = resp['client_id']
            print(f"{drv_str}: received client id from central compute node: {self.client_id}")
        if resp['status']:
            self.connected = True
            print(f"{drv_str}: central compute acknoledged connection")
        else:
            print(f"{drv_str}: central compute did not acknowledge connection")
       
    async def run(self):
        drv_str = "Scheduler"
        # Create tasks for all our async functions
        #connect to wifi
        wifi_task = asyncio.create_task(self.wifi_driver_init())
        print(f"{drv_str}: started wifi_driver_init task")
        #wait for wifi to connect
        await wifi_task 
        print(f"{drv_str}: wifi_driver_init task completed")

        #setup socket
        print(f"{drv_str}: starting socket_init task")
        socket_task = asyncio.create_task(self.socket_driver_init())
        await socket_task
        print(f"{drv_str}: socket_init task completed")

        if self.connected:
            tasks = [
                asyncio.create_task(self.simulate_sensor_reading()),
                asyncio.create_task(self.transmit_data()),
                #asyncio.create_task(self.connection_monitor()),
            ]
            print(f"{drv_str}: starting tasks\n {tasks}")
            await asyncio.gather(*tasks)
            print(f"{drv_str}: tasks completed")
    

def main():
    if is_micropython():
        print("micro p")
    node = AsyncNode(ssid="Tilin's nightclub", password="engineers123")
    print("Starting Scheduler")
    asyncio.run(node.run())
    print("Scheduler finished")

if __name__ == '__main__':
    main()