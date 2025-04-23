import time
import network # type: ignore
import asyncio
from machine import Pin # type: ignore
from neopixel import NeoPixel # type: ignore
from logger import logger

class WiFiDriver:
    def __init__(self, config):
        # Initialize with configuration
        self.config = config
        self.network_interfaces = list(config.keys())
        self.network_interface_index = 0
        self.current_network = None
        self.init_network_table()
        self.connected = False
        self.wlan = None
        self.drv_str = "WiFi_Driver"
        
        # Use provided neopixel or create one
        #self.neopixel = neopixel
    def init_network_table(self):
        self.num_networks = len(self.network_interfaces)
        self.current_network = self.network_interfaces[0]

    async def init_wifi_driver(self, driver_table_status : dict[str, bool]):
        func_str = "init_wifi_driver"
        """Connect to WiFi network"""

        logger.info(self.drv_str, func_str, f"Num networks: {self.num_networks}")

        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(1)
        
        # Check if already connected
        if self.wlan.isconnected():
            logger.info(self.drv_str, func_str, "Already connected to WiFi, disconnecting and restarting connection process")
            self.wlan.disconnect()
            await asyncio.sleep(1)
        else:
            logger.info(self.drv_str, func_str, "Not connected to WiFi")
        
        

        self.wlan.active(1)
        reconnect_count_max = 2
        time_start = time.time()
        while (self.network_interface_index < self.num_networks and not self.wlan.isconnected()):
            self.current_network = self.network_interfaces[self.network_interface_index]
            logger.info(self.drv_str, func_str, f"Attempting to connect to WiFi network {self.current_network}")

            reconnect_count = 0 
            current_network_ssid = self.config[self.current_network]['ssid']
            current_network_password = self.config[self.current_network]['password']

            while reconnect_count < reconnect_count_max and not self.wlan.isconnected():

                try:
                    self.wlan.connect(current_network_ssid, current_network_password)
                    timeout = 0
                    timeout_max = 5
                    while not self.wlan.isconnected() and timeout < timeout_max:
                        await asyncio.sleep(1)
                        logger.info(self.drv_str, func_str, f"Waiting for WiFi connection: {timeout}/{timeout_max} seconds")
                        timeout += 1
                    if self.wlan.isconnected():
                        logger.info(self.drv_str, func_str, f"Connected to WiFi network {self.current_network} in {timeout} seconds")
                        self.connected = True
                        driver_table_status[self.drv_str] = True
                        logger.info(self.drv_str, func_str, f"WiFi driver state: [Connected={self.connected},driver_table_status={driver_table_status[self.drv_str]}]")
                        return True
                    else:
                        logger.error(self.drv_str, func_str, f"Failed to connect to WiFi network {self.current_network} after {timeout} seconds")
                        reconnect_count += 1
                except Exception as e:
                    if e is OSError:
                        logger.error(self.drv_str, func_str, f"Error connecting to WiFi network {self.current_network}: {e}")
                    else:
                        logger.error(self.drv_str, func_str, f"Error connecting to WiFi network {self.current_network}: {e}")
                    reconnect_count += 1

                    
                await asyncio.sleep(1)

            if not self.wlan.isconnected():
                self.network_interface_index += 1
        time_end = time.time()
        logger.warning(self.drv_str, func_str, f"Failed to connect to WiFi after trying {self.num_networks} networks in {time_end - time_start} seconds")
        driver_table_status[self.drv_str] = False
        return False
    
    def is_connected(self):
        """Check if WiFi is connected"""
        if self.wlan:
            return self.wlan.isconnected()
        return False

    async def monitor_connection(self):
        """Monitor WiFi connection and reconnect if needed"""
        while True:
            if not self.is_connected():
                self.connected = False
                if self.neopixel:
                    self.neopixel.fill((25,0,0))  # Red indicates disconnected
                    self.neopixel.write()
                print(f"Connection Monitor: WiFi disconnected, attempting to reconnect...")
                await self.connect()
            else:
                if self.neopixel:
                    if self.neopixel[0] == (0,0,0):
                        self.neopixel.fill((0,25,0))  # Green indicates connected
                    else:
                        self.neopixel.fill((0,0,0))
                    self.neopixel.write()
            
            await asyncio.sleep(1)