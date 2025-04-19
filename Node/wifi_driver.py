import network
import asyncio
from machine import Pin
from neopixel import NeoPixel

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
        self.drv_str = "WiFi Driver"
        
        # Use provided neopixel or create one
        #self.neopixel = neopixel
    def init_network_table(self):
        self.num_networks = len(self.network_interfaces)
        self.current_network = self.network_interfaces[0]

    async def init_wifi_driver(self, driver_table_status : dict[str, bool]):
        """Connect to WiFi network"""
        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(1)
        
        # Check if already connected
        if self.wlan.isconnected():
            print(f"{self.drv_str}: Already connected to WiFi, disconnecting and restarting connection process")
            self.wlan.disconnect()
            await asyncio.sleep(1)
        else:
            print(f"{self.drv_str}: Not connected to WiFi")
        
        print(f"{self.drv_str}: Connecting to WiFi network {self.config[self.current_network]['ssid']}")
        
        # Connect to WiFi
        reconnect_count = 0
        reconnect_count_max = 5
        print(f"{self.drv_str}: Num networks: {self.num_networks}, max reconnects: {reconnect_count_max}")
        self.wlan.active(1)

        while reconnect_count < reconnect_count_max and not self.wlan.isconnected():
            try:
                current_network_ssid = self.config[self.current_network]['ssid']
                current_network_password = self.config[self.current_network]['password']
                self.wlan.connect(current_network_ssid, current_network_password)
                await asyncio.sleep(1)
                
                if self.wlan.isconnected():        
                    print(f'WiFi Driver: Connected to WiFi')
                    self.connected = True
                    driver_table_status[self.drv_str] = True
                    return True
                
            except Exception as e:
                if reconnect_count == 5:
                    print(f"WiFi Driver: Failed to connect to WiFi after {reconnect_count} attempts, swapping networks")
                    if self.network_interface_index == self.num_networks:
                        print(f"WiFi Driver: Failed to connect to WiFi after {reconnect_count} attempts, no more networks to try")
                        driver_table_status[self.drv_str] = False
                        return False
                    else:
                        self.network_interface_index += 1
                        self.current_network = self.network_interfaces[self.network_interface_index]
                        print(f"WiFi Driver: Swapped to network {self.current_network} (self.current_network_index: {self.network_interface_index}/{self.num_networks})")
                
                print(f"WiFi Driver: Error connecting to WiFi: {e} ({reconnect_count}/{reconnect_count_max})")
                reconnect_count += 1
                await asyncio.sleep(1)
        
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
""" async def wifi_driver_init(self):
        drv_str = "WiFi Driver"
        
        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(1)
        #check if already connected
        if self.wlan.isconnected():
            print(f"{drv_str}: Already connected to WiFi, disconnecting and restarting connection process")
            self.wlan.disconnect()
            await asyncio.sleep(1)
        else:
            print(f"{drv_str}: Not connected to WiFi, connecting to {self.ssid}")
        print(f"{drv_str}: Connecting to WiFi network {self.ssid}")
        #connect to wifi
        reconnect_count = 0
        self.wlan.active(1)
        while  reconnect_count < 10 and not self.wlan.isconnected():
            try:
                self.wlan.connect(self.ssid, self.password)
                await asyncio.sleep(1)
                #print(f"Connected? {self.wlan.isconnected()}")
                if self.wlan.isconnected():
                    print("Connected to WiFi")
                    self.neopixel.fill((0,25,0))  # Green indicates connected
                    self.neopixel.write()
                    print(f'{drv_str}: Connected to WiFi')
                    self.connected = True
                    self.driver_table_status[drv_str] = True
                    return True

                
            except Exception as e:
                if reconnect_count == 5:
                    print(f"{drv_str}: Failed to connect to WiFi after {reconnect_count} attempts, attempting to connect" +
                " to hotspot")
                    self.use_hotspot = True
  
                print(f"{drv_str}: Error connecting to WiFi: {e}")
                reconnect_count += 1
                
                await asyncio.sleep(1)
        self.driver_table_status[drv_str] = False
        return False """