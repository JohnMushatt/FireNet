#WiFi support package for our Node System

import socket
import network
from machine import WDT, Timer, Pin
import ubinascii
import os
import json
import hashlib
import binascii
import time
#import urequest
from neopixel import NeoPixel
class WiFi:

    def __init__(self, ssid=None, password=None, server_ip=None,server_port=None, Node_ID=None):
                
        self.init_neopixel()

        self.station = network.WLAN(network.STA_IF)

        self.data_queue = []
        self.reconnect_attempts= 0
        self.max_reconnect_attempts = 5
        self.ssid = None
        self.password = None
        #self.watchdog = WDT(timeout=30000)
        self.Node_ID = 0
        self.save_credentials(ssid, password)
        self.timer = Timer(0)
        #self.timer.init(period=60000, mode=Timer.PERIODIC, callback=self.check_connection)
    def init_neopixel(self):
        #Power pin required to driver power to NeoPixel
        neo_power_pin = Pin(2, Pin.OUT)
        neo_power_pin.value(1)
        self.neopixel = NeoPixel(Pin(0), 1)
        self.neopixel.fill((25,0,0))
        self.neopixel.write()
        print("NeoPixel initialized")
    def load_credentials(self) -> bool:
        print("Loading credentials")
        #
    
        try:
            with open("wifi_config.json", "r") as config_file:
                wifi_config = json.load(config_file)
            
            stored_ssid = wifi_config.get("ssid")
            stored_password = wifi_config.get("password")

            self.ssid = stored_ssid
            self.password = stored_password
            print(f"ssid: {self.ssid}, password: {self.password}")
            return True
        
        except Exception as e:
            print(f"Error loading credentials: {e}")
            return False
    def save_credentials(self, ssid : str, password : str):
        print("Saving credentials")
       
        wifi_config = {
            "ssid": ssid,
            "password": password
        }
        #xprint(f"wifi_config: {wifi_config}")
        with open("wifi_config.json", "w") as config_file:
            json.dump(wifi_config, config_file)
        print("Credentials saved")
    def connect(self) -> bool:
        if not self.station.active():
            self.station.active(True)

        if self.station.isconnected():
            credentials     = self.load_credentials()
            if credentials:
                print(f"Node {self.Node_ID} connecting to {self.ssid}...")
                self.station.connect(self.ssid, self.password) #This will cause error because password is not unhashed/unsalted
            else:
                print("No credentials found")
                return False

        print(f"Network configuration:\n"
              f"SSID: {self.ssid}\n"
              f"IP: {self.station.ifconfig()[0]}\n"
              f"Subnet: {self.station.ifconfig()[1]}\n"
              f"Gateway: {self.station.ifconfig()[2]}\n"
              f"DNS: {self.station.ifconfig()[3]}\n")
        print(f"Node {self.Node_ID} connected to {self.ssid}")

        return True      
    def add_sensor_data(self, interface, sensor_data):
        msg_format = {
            "Node_ID": self.Node_ID,
            "interface": interface,
            "sensor_data": sensor_data,
            "timestamp": time.time()
        }
        self.data_queue.append(msg_format)
        return True
        
    
        
    def disconnect(self):
        self.station.disconnect()
        self.station.active(False)
        print(f"Node {self.Node_ID} disconnected from {self.ssid}")
        

def main():
    wifi = WiFi(ssid="", password="")
    wifi.connect()


if __name__ == "__main__":
    main()

        
        