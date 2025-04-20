import asyncio
import socket
from network_config import read_network_config
import network
from machine import Pin
import json
import time
from neopixel import NeoPixel
from wifi_driver import WiFiDriver
from socket_driver import SocketDriver
from logger import logger


def is_micropython():
    """Returns True if running on MicroPython (ESP32, etc.)"""
    try:
        from machine import Pin
        return True
    except ImportError:
        return False
class AsyncNode:
    def __init__(self, node_name : str="Generic Node", config : dict=None):
        self.drv_str = "Scheduler_Driver"
        self.version = "0.0.1"
        self.node_name : str = node_name
        self.config : dict = config
        self.wifi_driver : WiFiDriver = WiFiDriver(config)
        self.socket_driver : SocketDriver = SocketDriver(config)

        self.data_queue = []
        self.connected = False
        self.server_ip = ["192.168.0.94", "192.168.0.145"]  # Replace with your server's IP address
        self.server_port = 8765 


        self.driver_table_status = {
            "WiFi_Driver": False,
            "Socket_Driver": False,
            "Connection_Monitor": False,
            "Simulate_Sensor_Reading": False,
            "Transmit_Data": False
        }
        self.init_neopixel()
        
    def init_neopixel(self):
        neo_power_pin = Pin(2, Pin.OUT)
        neo_power_pin.value(1)
        self.neopixel = NeoPixel(Pin(0), 1)
        self.neopixel.fill((25,0,0))  # Red indicates not connected
        self.neopixel.write()

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
            if self.data_queue and self.socket_driver.is_connected():
                data = self.data_queue.pop(0)
                # Simulate data transmission
                json_data = json.dumps(data) + '\n'
                print(f'Transmitting data: {json_data} to {self.server_ip}:{self.server_port}')

                self.socket_driver.send_data(json_data)

                resp = self.socket_driver.receive_response()
                print(f'Data received from central compute node @ {resp["timestamp"]}')

    async def connection_monitor(self):
        drv_str = "Connection Monitor"
        while True:
            if not self.wifi_driver.is_connected():
                self.connected = False
                self.neopixel.fill((25,0,0))  # Red indicates disconnected
                self.neopixel.write()
                print(f"{drv_str}: WiFi disconnected, attempting to reconnect...")
                await self.wifi_driver.init_wifi_driver(self.driver_table_status)
                print(f"{drv_str}: WiFi driver reinitialization task completed")
            else:
                if self.neopixel[0] == (0,0,0):
                    self.neopixel.fill((0,25,0))  # Green indicates connected
                else:
                    self.neopixel.fill((0,0,0))  # Green indicates connected
                self.neopixel.write()
            #print(f"{drv_str}: {self.station.isconnected()}")
            await asyncio.sleep(1)
   
       
    async def scheduler_run(self):
        func_str = "scheduler_run"
        # Create tasks for all our async functions
        #connect to wifi
        logger.info(self.drv_str, func_str, f"Starting {self.node_name} scheduler")
        wifi_task = asyncio.create_task(self.wifi_driver.init_wifi_driver(self.driver_table_status))
        logger.info(self.drv_str, func_str, f"Started wifi_driver_init task")
        #wait for wifi to connect
        await wifi_task 
        if not self.driver_table_status['WiFi_Driver']:
            return
        
        logger.info(self.drv_str, func_str, f"wifi_driver_init task completed: status={self.driver_table_status['WiFi_Driver']}\n")

        #setup socket
        logger.info(self.drv_str, func_str, f"starting socket_init task")
        socket_task = asyncio.create_task(self.socket_driver.init_socket_driver(driver_table_status=self.driver_table_status,retry=True))
        await socket_task
        if not self.driver_table_status['Socket_Driver']:
            return
        
        logger.info(self.drv_str, func_str, f"socket_init task completed: status={self.driver_table_status['Socket_Driver']}\n")

        tasks = [
            asyncio.create_task(self.simulate_sensor_reading()),
            asyncio.create_task(self.transmit_data()),
            asyncio.create_task(self.connection_monitor()),
        ]
        logger.info(self.drv_str, func_str, f"starting tasks\n {tasks}")
        await asyncio.gather(*tasks)
        logger.info(self.drv_str, func_str, f"tasks completed")


def main():
    config = read_network_config()
    if config == None:
        print("Please supply a config file")
        return
    version_str = ""
    node = AsyncNode("Generic Node",config=config)
    version_str = f"Running node: {node.node_name} Version: {node.version}"
    if is_micropython():
        version_str += " MicroPython"
    logger.info(node.drv_str, "main", version_str)
    logger.info(node.drv_str, "main", "Starting Scheduler")
    asyncio.run(node.scheduler_run())
    logger.info(node.drv_str, "main", "Scheduler finished")

if __name__ == '__main__':
    main()