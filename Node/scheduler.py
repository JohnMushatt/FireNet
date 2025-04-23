import asyncio
import socket
from network_config import read_network_config # type: ignore
import network # type: ignore
from machine import Pin # type: ignore
import json
import time
from neopixel import NeoPixel # type: ignore
from wifi_driver import WiFiDriver
from socket_driver import SocketDriver
from logger import logger


def is_micropython():
    """Returns True if running on MicroPython (ESP32, etc.)"""
    try:
        from machine import Pin # type: ignore
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
                'node_name': self.node_name,
                'msg_id': 'sensor_data',
                'timestamp': time.time(),
                'temperature': 20 + (time.time() % 10),
                'humidity': 50 + (time.time() % 20),
                'pressure': 1000 + (time.time() % 50)
            }
            self.data_queue.append(sensor_data)
            await asyncio.sleep(5)  # Read every 5 seconds

    async def transmit_data(self):
        func_str = "transmit_data"
        while True:
            if self.data_queue and self.socket_driver.is_connected():
                data = self.data_queue.pop(0)
                # Simulate data transmission
                json_data = json.dumps(data) + '\n'
                logger.info(self.drv_str, func_str, f'Transmitting data to {self.socket_driver.server_ip[self.socket_driver.server_ip_index]}:{self.server_port}')

                self.socket_driver.send_data(json_data)
                logger.info(self.drv_str, func_str, f'Data sent to {self.socket_driver.server_ip[self.socket_driver.server_ip_index]}:{self.server_port}')
                resp = await self.socket_driver.receive_data()
                logger.info(self.drv_str, func_str, f'Data received from central compute node @ {resp}')
    async def send_data(self, data):
        func_str = "send_data"
        logger.info(self.drv_str, func_str, f'Sending data to {self.socket_driver.server_ip[self.socket_driver.server_ip_index]}:{self.server_port}')
        try:    
            await self.socket_driver.send_data(data)
            logger.info(self.drv_str, func_str, f'Data sent to {self.socket_driver.server_ip[self.socket_driver.server_ip_index]}:{self.server_port}')
        except Exception as e:
            logger.error(self.drv_str, func_str, f'Error sending data: {e}')
    async def receive_data(self) -> dict:
        func_str = "receive_data"
        try:
            logger.info(self.drv_str, func_str, f'Receiving data from {self.socket_driver.server_ip[self.socket_driver.server_ip_index]}:{self.server_port}')
            resp = await self.socket_driver.receive_data()
            logger.info(self.drv_str, func_str, f'Data received from central compute node @ {resp}')
            return resp
        except Exception as e:
            logger.error(self.drv_str, func_str, f'Error receiving data: {e}')
            return None
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
    async def send_node_update(self):
        func_str = "send_node_update"

        data = {
            "msg_id": "node_update",
            "node_name": self.node_name,
        }
        json_data = json.dumps(data) + '\n'
        logger.info(self.drv_str, func_str, f"sending node info to central compute node: {json_data}")
        await self.send_data(json_data)

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


        logger.info(self.drv_str, func_str, f"sending node update to central compute node")
        await self.send_node_update()
        logger.info(self.drv_str, func_str, f"receiving node acknowledgement from central compute node")
        resp = await self.receive_data()
        logger.info(self.drv_str, func_str, f"node acknowledgement received from central compute node: {resp}")
        if resp["msg_id"] == "node_update_ack" and resp["status"] == "ok":
            logger.info(self.drv_str, func_str, f"node update acknowledgement received from central compute node: {resp}")
        else:
            logger.error(self.drv_str, func_str, f"node update acknowledgement not received from central compute node: {resp}")

        logger.info(self.drv_str, func_str, f"scheduler has finished all setup tasks!")

        tasks = [
            asyncio.create_task(self.simulate_sensor_reading()),
            asyncio.create_task(self.transmit_data()),
            asyncio.create_task(self.connection_monitor()),
        ]
        logger.info(self.drv_str, func_str, f"starting tasks {tasks}")
        await asyncio.gather(*tasks)
        logger.info(self.drv_str, func_str, f"tasks completed {tasks}")


def main():
    config = read_network_config()
    if config == None:
        print("Please supply a config file")
        return
    version_str = ""
    node = AsyncNode(node_name="Generic Node",config=config)
    version_str = f"Running node: {node.node_name} Version: {node.version}"
    if is_micropython():
        version_str += " MicroPython"
    logger.info(node.drv_str, "main", version_str)
    logger.info(node.drv_str, "main", "Starting Scheduler")
    asyncio.run(node.scheduler_run())
    logger.info(node.drv_str, "main", "Scheduler finished")

if __name__ == '__main__':
    main()