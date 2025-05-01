import logging
import time

logger = logging.getLogger(__name__)
class MessageParser:
    """Parser for handling different types of messages from client nodes"""
    
    def __init__(self, connected_clients):
        self.handlers = {}
        self.register_default_handlers()
        self.connected_clients = connected_clients
        
    def register_handler(self, msg_type, handler_func):
        """Register a new message handler function"""
        self.handlers[msg_type] = handler_func
        logger.info(f"Registered handler for message type: {msg_type}")
        
    def register_default_handlers(self):
        """Register the built-in message handlers"""
        # Register built-in handlers
        self.register_handler("node_update", self.handle_node_update)
        self.register_handler("sensor_data", self.handle_sensor_data)
        self.register_handler("status_request", self.handle_status_request)
        self.register_handler("default", self.default_handler)
        self.register_handler("dhtt_data", self.handle_dhtt_sensor)
    async def parse_message(self, message, client_id):
        """Parse incoming message and route to appropriate handler"""
        try:
            # Determine message type
            msg_type = message.get("msg_id", "unknown")
            
            # Log the message type and source
            logger.info(f"Processing {msg_type} message from {client_id}")
            
            # Check if we have a handler for this message type
            if msg_type in self.handlers:
                # Call the appropriate handler
                return await self.handlers[msg_type](message, client_id)
            else:
                # Handle unknown message type
                logger.warning(f"No handler for message type: {msg_type}")
                return await self.default_handler(message, client_id)
                
        except KeyError as e:
            logger.error(f"Missing required field in message: {e}")
            return {"status": "error", "message": f"Missing required field: {e}"}
        except Exception as e:
            logger.error(f"Error parsing message: {e}")
            return {"status": "error", "message": str(e)}
    async def default_handler(self, message, client_id):
        """Handle unknown message types"""
        logger.warning(f"No handler for message type: {message.get('msg_id', 'unknown')}")
        resp = {"msg_id": "unknown_message_type", "status": "error", "message": f"Unknown message type: {message.get('msg_id', 'unknown')}"}
        return resp
    async def handle_dhtt_sensor(self,message, client_id):
        """Handle DHT11 sensor data messages"""

        """ {'timestamp': 799274659, 'temperature': 25.7, 'humidity': 42.6, 'node_name': 'DHTT Node', 'msg_id': 'dhtt_data'} """
        timestamp = message.get("timestamp", time.time())
        temperature = message.get("temperature", 0.0)
        humidity = message.get("humidity", 0.0)
        node_name = message.get("node_name", "Unknown Node")

        logger.info(f"DHTT sensor data from {node_name} (ID: {client_id}): {temperature}C, {humidity}%")
        
        
    async def handle_node_update(self, message, client_id):
        """Handle node_update messages"""
        node_name = message.get("node_name", "Unknown Node")
        node_type = message.get("node_type", "Generic")
        version = message.get("version", "Unknown")
        
        # Update client information with node details
        if client_id in self.connected_clients:
            self.connected_clients[client_id]["node_name"] = node_name
            self.connected_clients[client_id]["node_type"] = node_type
            self.connected_clients[client_id]["version"] = version
            
            # Additional fields if present
            if "capabilities" in message:
                self.connected_clients[client_id]["capabilities"] = message["capabilities"]
                
            logger.info(f"Node update from {node_name} (ID: {client_id}, Type: {node_type}, Version: {version})")
            
            # Return success response
            return {
                "msg_id": "node_update_response",
                "status": "success", 
                "message": "Node update received",
                "timestamp": time.time()
            }
        else:
            logger.warning(f"Received node_update from unknown client ID: {client_id}")
            return {"status": "error", "message": "Client not recognized"}
    
    async def handle_sensor_data(self, message, client_id):
        """Handle sensor data messages"""
        # Extract sensor data fields
        sensor_type = message.get("sensor_type", "unknown")
        timestamp = message.get("timestamp", time.time())
        readings = message.get("readings", {})
        
        if not readings:
            logger.warning(f"Empty sensor readings from {client_id}")
            return {"status": "error", "message": "No sensor readings provided"}
            
        # Process different sensor types
        if client_id in self.connected_clients:
            # Store the sensor reading
            if "sensors" not in self.connected_clients[client_id]:
                self.connected_clients[client_id]["sensors"] = {}
                
            # Update the sensor data for this sensor type
            self.connected_clients[client_id]["sensors"][sensor_type] = {
                "last_reading": timestamp,
                "data": readings
            }
            
            # Log the sensor data
            logger.info(f"Sensor data from {client_id} ({sensor_type}): {readings}")
            
            # Check for any threshold alerts
            alerts = self.check_sensor_thresholds(sensor_type, readings)
            
            # Return success response
            response = {
                "status": "success", 
                "message": "Sensor data received",
                "timestamp": time.time()
            }
            
            # If there are alerts, include them in the response
            if alerts:
                response["alerts"] = alerts
                
            return response
        else:
            logger.warning(f"Sensor data from unknown client ID: {client_id}")
            return {"status": "error", "message": "Client not recognized"}
    
    
    
    async def handle_status_request(self, message, client_id):
        """Handle status request messages"""
        # Return current server and client status
        if client_id in self.connected_clients:
            return {
                "status": "success",
                "server_time": time.time(),
                "connection_duration": time.time() - self.connected_clients[client_id]["connected_at"],
                "messages_received": len(self.connected_clients[client_id]["data"]),
                "client_id": client_id
            }
        else:
            return {"status": "error", "message": "Client not recognized"}
    
    
