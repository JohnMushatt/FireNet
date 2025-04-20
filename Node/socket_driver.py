import socket
import json
import asyncio
import time
from logger import logger
import errno
class SocketDriver:
    def __init__(self, config=None):
        self.config = config
        self.socket = None
        self.connected = False
        self.client_id = None
        self.server_ip = ["192.168.0.94", "192.168.0.145"]  # Server IPs to try
        self.server_port = 8765
        self.server_ip_index = 1  # Start with the second IP in the list
        self.drv_str = "Socket Driver"
    async def handle_error(self,e):
        func_str = "handle_error"
        print(f"{self.drv_str}: {func_str}: Error connecting to socket: {e}")

    async def init_socket_driver(self, driver_table_status=None,retry=True):
        func_str = "init_socket_driver"
        """Initialize socket connection to central compute node"""
        self.connected = False
        logger.info(self.drv_str, func_str, f"setting up socket to central compute node")

        # Create socket
        reconnect_count = 0
        #Either no retry and attempt one connection or retry forever
        if retry:
            logger.info(self.drv_str, func_str, f"retry={retry} -> socket driver will retry connection indefinitely")
        else:
            logger.info(self.drv_str, func_str, f"retry={retry} -> socket driver will attempt 1 connection")

        while (not self.connected) and ((not retry and reconnect_count < 1) or (retry)):
            try:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                
                # Get address info for the server
                current_server_ip = self.server_ip[self.server_ip_index]
                self.addrinfo = socket.getaddrinfo(current_server_ip, self.server_port)
                logger.info(self.drv_str, func_str, f"socket connecting to {current_server_ip}:{self.server_port}. Attempt {reconnect_count}")
                
                # Connect to the server
            
                self.socket.connect(self.addrinfo[0][-1])
            
                self.connected = True
                logger.info(self.drv_str, func_str, f"socket connected to {current_server_ip}:{self.server_port}")
           
                
            except Exception as e:
                logger.error(self.drv_str, func_str, f"Error connecting to socket: {e}")

                reconnect_count += 1
                if retry:
                    await asyncio.sleep(1)
                
          
        if driver_table_status:
            driver_table_status["Socket Driver"] = False
        return False
    
    async def send_data(self, data):
        func_str = "send_data"
        """Send data to the central compute node without waiting for response"""
        if not self.connected or not self.socket:
            logger.error(self.drv_str, func_str, f"Cannot send data - not connected")
            return False
        
        try:
            # Convert data to JSON and send
            logger.info(self.drv_str, func_str, f"Transmitting data: {data}")
            self.socket.send(data.encode('utf-8'))
            return True
        except Exception as e:
            logger.error(self.drv_str, func_str, f"Error sending data: {e}")
            self.connected = False
            return False
    async def receive_response(self, timeout=5.0):
        func_str = "receive_response"
        """Receive a response from the server with timeout"""
        if not self.connected or not self.socket:
            return None
        
        try:
            # Set socket to non-blocking mode
            self.socket.setblocking(False)
            
            # Wait for data with timeout using asyncio
            start_time = time.time()
            while (time.time() - start_time) < timeout:
                try:
                    resp = self.socket.recv(1024)
                    if resp:
                        return json.loads(resp)
                except BlockingIOError:
                    # No data available yet
                    await asyncio.sleep(0.1)
                except Exception as e:
                    logger.error(self.drv_str, func_str, f"Error receiving response: {e}")
                    break
                    
            logger.error(self.drv_str, func_str, f"Timeout waiting for response")
            return None
        finally:
            # Reset to blocking mode
            self.socket.setblocking(True)

    """ async def transmit_data(self):
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
            await asyncio.sleep(60) """
    def is_connected(self):
        """Check if socket is connected"""
        return self.connected
    
    def close(self):
        func_str = "close"
        """Close socket connection"""
        if self.socket:
            try:
                self.socket.close()
                logger.info(self.drv_str, func_str, f"Socket connection closed")
            except Exception as e:
                logger.error(self.drv_str, func_str, f"Error closing socket: {e}")
        self.connected = False