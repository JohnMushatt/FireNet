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


dhtt_msg = {
    "msg_id": "dhtt_data",
    "timestamp": time.time(),
    "temperature": 0.0,
    "humidity": 0.0,
    "node_name": "DHTT Node"
}
motor_msg = {
    "msg_id": "motor_data",
    "timestamp": time.time(),
    "motor_position": [0,0],
    "node_name": "Motor Node"
}

smoke_msg = {
    "msg_id": "smoke_data",
    "timestamp": time.time(),
    "smoke_level": 0.0,
    "node_name": "Smoke Node"
}



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
            
            if self.node_name == "DHTT Node":
                sensor_data = dhtt_msg
                sensor_data["temperature"] = 20 + (time.time() % 10)
                sensor_data["humidity"] = 50 + (time.time() % 20)
            elif self.node_name == "Motor Node":
                sensor_data = motor_msg
                sensor_data["motor_position"] = [time.time() % 100, time.time() % 100]
            elif self.node_name == "Smoke Node":
                sensor_data = smoke_msg
                sensor_data["smoke_level"] = 0.1 + (time.time() % 0.5)
            else:
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
            if self.data_queue and self.socket_driver.connected:
                data = self.data_queue.pop(0)
                # Simulate data transmission
                json_data = json.dumps(data) + '\n'
                logger.info(self.drv_str, func_str, f'Transmitting data to {self.socket_driver.server_ip[self.socket_driver.server_ip_index]}:{self.server_port}')
                await self.send_message_with_response(json_data)
            else:
                await asyncio.sleep(10)
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
    async def process_messages(self):
        """Process messages from the message queue"""
        func_str = "process_messages"
        
        while True:
            # Non-blocking check for new messages
            message = await self.socket_driver.get_next_message(timeout=0.5)
            
            if message:
                logger.info(self.drv_str, func_str, f"Processing message: {message}")
                msg_id = message.get("msg_id", "unknown")
                
                # Handle different message types
                if msg_id == "command":
                    await self.handle_command(message)
                elif msg_id == "config_update":
                    await self.handle_config_update(message)
                # Add more handlers as needed
                
            await asyncio.sleep(0.1)
    
    async def send_message_with_response(self, message_data, expected_msg_id=None) -> tuple[bool, dict]:
        func_str = "send_message_with_response"
        """Example of sending a command and waiting for a specific response"""
        # This is a blocking call that waits for the specific response
        logger.info(self.drv_str, func_str, f"Data: {message_data} Expected response: {expected_msg_id}")
        response = await self.socket_driver.send_and_receive(
            message_data,
            timeout=10.0,
            expected_msg_id=expected_msg_id
        )
        
        if response:
            debug_str : str
            if response.get("msg_id") == expected_msg_id:
                debug_str = f"Response includes expected msg_id: {expected_msg_id}"
            else:
                debug_str = f"Got response with no specific msg_id: {response.get('msg_id')}"
            logger.info(self.drv_str, func_str, debug_str)
            return True, response
        else:
            logger.error(self.drv_str, func_str, "Command timed out")
            return False, None

    async def send_node_update(self) -> tuple[bool, dict]:
        func_str = "send_node_update"

        data = {
            "msg_id": "node_update",
            "node_name": self.node_name,
        }
        expected_msg_id = "node_update_response"
        logger.info(self.drv_str, func_str, f"Sending node update to central compute node")
        success, resp = await self.send_message_with_response(data, expected_msg_id)
        if success:
            logger.info(self.drv_str, func_str, f"Node update was received by central compute node")
            return True, resp
        else:
            logger.error(self.drv_str, func_str, f"Node update was not received by central compute node")
            return False, None



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
        socket_task = asyncio.create_task(self.socket_driver.init_socket_driver(driver_table_status=self.driver_table_status,retry=True, use_dedicated_server=True))
        await socket_task
        if not self.driver_table_status['Socket_Driver']:
            return
        
        logger.info(self.drv_str, func_str, f"socket_init task completed: status={self.driver_table_status['Socket_Driver']}\n")

        print("\n\n*******************************\n\n")
        logger.info(self.drv_str,func_str, f"Starting main application")

        #send node update to central compute node
        await self.send_node_update()

       

        #start background listener for incoming messages
        #logger.info(self.drv_str, func_str, f"starting background listener for incoming messages")
        #await self.socket_driver.start_background_listener()
        #logger.info(self.drv_str, func_str, f"background listener started")

        logger.info(self.drv_str, func_str, f"scheduler has finished all setup tasks!")

        tasks = [
            asyncio.create_task(self.simulate_sensor_reading()),
            asyncio.create_task(self.transmit_data()),
            #asyncio.create_task(self.connection_monitor()),
            #asyncio.create_task(self.process_messages())
        ]
        logger.info(self.drv_str, func_str, f"starting tasks: {tasks}")
        await asyncio.gather(*tasks)
        logger.info(self.drv_str, func_str, f"tasks completed {tasks}")


def main():
    config = read_network_config()
    if config == None:
        print("Please supply a config file")
        return
    version_str = ""
    node = AsyncNode(node_name="Motor Node",config=config)
    version_str = f"Running node: {node.node_name} Version: {node.version}"
    if is_micropython():
        version_str += " MicroPython"
    logger.info(node.drv_str, "main", version_str)
    logger.info(node.drv_str, "main", "Starting Scheduler")
    asyncio.run(node.scheduler_run())
    logger.info(node.drv_str, "main", "Scheduler finished")

if __name__ == '__main__':
    main()