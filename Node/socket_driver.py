import socket
import json
import asyncio
import time
from collections import deque
from logger import logger
import errno
class SocketDriver:
    def __init__(self, config=None):
        self.version_str = "1.0.0"
        self.config = config
        self.socket = None
        self.connected = False
        self.client_id = None
        self.server_ip = ["192.168.0.94", "192.168.0.145", "192.168.0.95"]  # Server IPs to try
        self.dedicated_server_ip = "68.8.86.82"
        self.server_port = 8765
        self.server_ip_index = 1  # Start with the second IP in the list
        self.drv_str = "Socket_Driver"
        func_str = "__init__"
        self.message_queue = deque([],20)
        self._listening_task = None
        self._stop_listening = False
        logger.info(self.drv_str, func_str, f"Socket driver version {self.version_str}")



    async def handle_error(self,e):
        func_str = "handle_error"
        print(f"{self.drv_str}: {func_str}: Error connecting to socket: {e}")

    async def init_socket_driver(self, driver_table_status=None,retry=True, use_dedicated_server=True):
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
                self.socket.settimeout(3)
                # Get address info for the server
                if use_dedicated_server:
                    current_server_ip = self.dedicated_server_ip
                else:
                    current_server_ip = self.server_ip[self.server_ip_index]
                self.addrinfo = socket.getaddrinfo(current_server_ip, self.server_port)
                logger.info(self.drv_str, func_str, f"socket connecting to {current_server_ip}:{self.server_port}")
                
                # Connect to the server
            
                self.socket.connect(self.addrinfo[0][-1])
            
                self.connected = True
                logger.info(self.drv_str, func_str, f"socket connected to {current_server_ip}:{self.server_port}")
                driver_table_status["Socket_Driver"] = True
                return True

            except Exception as e:
                if e.errno == errno.ECONNREFUSED:
                    pass
                elif e.errno == errno.ETIMEDOUT:
                    logger.error(self.drv_str, func_str, f"Socket connection timed out")
                    if use_dedicated_server:
                        logger.error(self.drv_str, func_str, f"Socket connection timed out to dedicated server")
                        pass
                    else:
                        self.server_ip_index = (self.server_ip_index + 1) % len(self.server_ip)
                if retry:
                    await asyncio.sleep(1)
                else:
                    logger.error(self.drv_str, func_str, f"Socket connection failed")

                
          
        if driver_table_status:
            driver_table_status["Socket Driver"] = False
        return False
    
    async def send_data(self, data):
        """Send data to the server"""
        func_str = "send_data"
        if not self.connected or not self.socket:
            logger.error(self.drv_str, func_str, "Cannot send data: not connected")
            return False
        
        try:
            # If data is a string, encode it
            if isinstance(data, str):
                data_bytes = data.encode('utf-8')
            # If data is a dict, convert to JSON string and encode
            elif isinstance(data, dict):
                data_bytes = (json.dumps(data) + '\n').encode('utf-8')
            # If data is already bytes, use it directly
            elif isinstance(data, bytes):
                data_bytes = data
            else:
                data_bytes = str(data).encode('utf-8')
            
            # Ensure the data ends with a newline
            if not data_bytes.endswith(b'\n'):
                data_bytes += b'\n'
            
            # Send the data
            self.socket.send(data_bytes)
            logger.info(self.drv_str, func_str, f"Sent {len(data_bytes)} bytes")
            return True
        except Exception as e:
            logger.error(self.drv_str, func_str, f"Error sending data: {e}")
            self.connected = False
            return False
    
    async def receive_data(self, timeout=3):
        """Receive data from the server"""
        func_str = "receive_data"
        if not self.connected or not self.socket:
            logger.error(self.drv_str, func_str, "Cannot receive data: not connected")
            return None
        logger.info(self.drv_str, func_str, f"Receiving data from server with timeout {timeout} seconds")
        try:
            # Set timeout for this operation
            #original_timeout = self.socket.gettimeout()
            self.socket.settimeout(timeout)
            
            # Wait for data
            data = b""
            try:
                chunk = self.socket.recv(4096)
                if chunk:
                    data += chunk
                else:
                    # Empty chunk means connection closed
                    logger.warning(self.drv_str, func_str, "Connection closed by server")
                    self.connected = False
                    return None
            except Exception as e:
                if e.errno == errno.ETIMEDOUT:
                    logger.warning(self.drv_str, func_str, "Socket receive timeout")
                    return None
            
            # Restore original timeout
            #self.socket.settimeout(original_timeout)
            
            # Process received data
            if data:
                try:
                    # Decode and parse JSON
                    decoded = data.decode('utf-8').strip()
                    parsed = json.loads(decoded)
                    logger.info(self.drv_str, func_str, f"Received JSON data: {str(parsed)[:50]}...")
                    return parsed
                except json.JSONDecodeError:
                    # Not JSON, return as string
                    decoded = data.decode('utf-8').strip()
                    logger.info(self.drv_str, func_str, f"Received text data: {decoded[:50]}...")
                    return decoded
                except UnicodeError:
                    # Can't decode as UTF-8, return raw bytes
                    logger.info(self.drv_str, func_str, f"Received binary data: {len(data)} bytes")
                    return data
            
            return None
        except Exception as e:
            pass
            #logger.error(self.drv_str, func_str, f"Error receiving data: {e}")
            #return None
    
    async def start_background_listener(self):
        """Start a background task to listen for incoming messages"""
        func_str = "start_background_listener"
        if self._listening_task is not None:
            logger.warning(self.drv_str, func_str, "Background listener already running")
            return
        
        self._stop_listening = False
        self._listening_task = asyncio.create_task(self._background_listener())
        logger.info(self.drv_str, func_str, "Started background listener task")
    
    async def stop_background_listener(self):
        """Stop the background listening task"""
        func_str = "stop_background_listener"
        if self._listening_task is None:
            logger.warning(self.drv_str, func_str, "No background listener to stop")
            return
        
        self._stop_listening = True
        await asyncio.sleep(0.1)  # Give the task a chance to clean up
        
        if self._listening_task is not None:
            self._listening_task.cancel()
            try:
                await self._listening_task
            except asyncio.CancelledError:
                pass
            self._listening_task = None
        
        logger.info(self.drv_str, func_str, "Stopped background listener task")
    
    async def _background_listener(self):
        """Background task that continuously listens for messages"""
        func_str = "_background_listener"
        logger.info(self.drv_str, func_str, "Background listener started")
        
        while not self._stop_listening and self.connected:
            try:
                # Non-blocking socket operation
                self.socket.setblocking(False)
                
                try:
                    data = b""
                    chunk = self.socket.recv(4096)
                    if chunk:
                        data += chunk
                    else:
                        # Connection closed
                        logger.warning(self.drv_str, func_str, "Connection closed by server")
                        self.connected = False
                        break
                    
                    # Process data if received
                    if data:
                        try:
                            # Try to parse as JSON
                            decoded = data.decode('utf-8').strip()
                            parsed = json.loads(decoded)
                            logger.debug(self.drv_str, func_str, f"Queued message: {str(parsed)[:50]}...")
                            self.message_queue.append(parsed)
                        except json.JSONDecodeError:
                            # Not JSON, queue as string
                            decoded = data.decode('utf-8').strip()
                            logger.debug(self.drv_str, func_str, f"Queued text message: {decoded[:50]}...")
                            self.message_queue.append(decoded)
                        except UnicodeError:
                            # Binary data
                            logger.debug(self.drv_str, func_str, f"Queued binary message: {len(data)} bytes")
                            self.message_queue.append(data)
                            
                except BlockingIOError:
                    # No data available, this is normal
                    pass
                except Exception as e:
                    logger.error(self.drv_str, func_str, f"Error in background listener: {e}")
                
                # Restore blocking mode
                self.socket.setblocking(True)
                
                # Small delay to prevent CPU hogging
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(self.drv_str, func_str, f"Background listener error: {e}")
                await asyncio.sleep(1)  # Longer delay after error
                
        logger.info(self.drv_str, func_str, "Background listener stopped")
    
    async def get_next_message(self, timeout=0):
        """Get the next message from the queue if available"""
        func_str = "get_next_message"
        
        if not self.message_queue:
            if timeout > 0:
                # Wait for a message if timeout specified
                start_time = time.time()
                while not self.message_queue and time.time() - start_time < timeout:
                    await asyncio.sleep(0.1)
            
            # Return None if no message
            if not self.message_queue:
                return None
        
        # Return and remove the first message
        message = self.message_queue.popleft()
        logger.debug(self.drv_str, func_str, f"Retrieved message from queue, {len(self.message_queue)} remaining")
        return message
    
    async def send_and_receive(self, data, timeout=5.0, expected_msg_id=None):
        """Send data and wait for a specific response"""
        func_str = "send_and_receive"
        
        # Send the data
        if not await self.send_data(data):
            logger.error(self.drv_str, func_str, "Failed to send data")
            return None
        
        # Wait for response
        start_time = time.time()
        while time.time() - start_time < timeout:
            # Try to receive data
            response = await self.receive_data(timeout=1)
            
            if response:
                logger.info(self.drv_str, func_str, f"Received response: {response}")
                # If we're not looking for a specific message ID, return any response
                if not expected_msg_id:
                    return response
                
                # If we have a dict response with matching msg_id, return it
                if isinstance(response, dict) and response.get("msg_id") == expected_msg_id:
                    return response
                
                # Otherwise keep waiting for the right response
                logger.debug(self.drv_str, func_str, f"Received response but not the expected message ID")
            
            # Small delay between attempts
            await asyncio.sleep(0.1)
        
        # Timeout occurred
        logger.warning(self.drv_str, func_str, f"Timeout waiting for response after {timeout} seconds")
        return None