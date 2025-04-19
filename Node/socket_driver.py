import socket
import json
import asyncio

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
    
    async def init_socket_driver(self, driver_table_status=None):
        """Initialize socket connection to central compute node"""
        print(f"{self.drv_str}: setting up socket to central compute node")

        # Create socket
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Get address info for the server
            current_server_ip = self.server_ip[self.server_ip_index]
            self.addrinfo = socket.getaddrinfo(current_server_ip, self.server_port)
            print(f"{self.drv_str}: socket connecting to {current_server_ip}:{self.server_port}")
            
            # Connect to the server
            self.socket.connect(self.addrinfo[0][-1])
            print(f"{self.drv_str}: socket connected to {current_server_ip}:{self.server_port}")
            
            # Receive initial response from server
            resp = self.socket.recv(1024)
            resp = json.loads(resp)
            
            # Process client ID from response
            if 'client_id' in resp:
                self.client_id = resp['client_id']
                print(f"{self.drv_str}: received client id from central compute node: {self.client_id}")
            
            # Check connection status
            if resp.get('status') == 'connected':
                self.connected = True
                print(f"{self.drv_str}: central compute acknowledged connection")
                if driver_table_status:
                    driver_table_status["Socket Driver"] = True
                return True
            else:
                print(f"{self.drv_str}: central compute did not acknowledge connection")
                if driver_table_status:
                    driver_table_status["Socket Driver"] = False
                return False
                
        except Exception as e:
            print(f"{self.drv_str}: Error connecting to socket: {e}")
            if driver_table_status:
                driver_table_status["Socket Driver"] = False
            return False
    
    def send_data(self, data):
        """Send data to the central compute node"""
        if not self.connected or not self.socket:
            print(f"{self.drv_str}: Cannot send data - not connected")
            return False
        
        try:
            # Convert data to JSON and send
            json_data = json.dumps(data) + '\n'
            print(f'{self.drv_str}: Transmitting data: {json_data} to {self.server_ip[self.server_ip_index]}:{self.server_port}')
            self.socket.send(json_data.encode('utf-8'))
            
            # Receive response
            resp = self.socket.recv(1024)
            resp = json.loads(resp)
            
            if resp.get('status') == 'msg_received':
                print(f'{self.drv_str}: Data received from central compute node @ {resp.get("timestamp", "unknown")}')
                return True
            else:
                print(f'{self.drv_str}: Data not received from central compute node')
                return False
                
        except Exception as e:
            print(f"{self.drv_str}: Error sending data: {e}")
            self.connected = False
            return False
    
    def is_connected(self):
        """Check if socket is connected"""
        return self.connected
    
    def close(self):
        """Close socket connection"""
        if self.socket:
            try:
                self.socket.close()
                print(f"{self.drv_str}: Socket connection closed")
            except Exception as e:
                print(f"{self.drv_str}: Error closing socket: {e}")
        self.connected = False