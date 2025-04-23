import logging

logger = logging.getLogger(__name__)

class MessageParser:
    """Parser for handling different types of messages from client nodes"""
    
    def __init__(self):
        self.handlers = {}
        self.register_default_handlers()
        
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
        self.register_handler("command_response", self.handle_command_response)
        
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
                return {"status": "error", "message": f"Unknown message type: {msg_type}"}
                
        except KeyError as e:
            logger.error(f"Missing required field in message: {e}")
            return {"status": "error", "message": f"Missing required field: {e}"}
        except Exception as e:
            logger.error(f"Error parsing message: {e}")
            return {"status": "error", "message": str(e)}
    
    async def handle_node_update(self, message, client_id):
        """Handle node_update messages"""
        node_name = message.get("node_name", "Unknown Node")
        node_type = message.get("node_type", "Generic")
        version = message.get("version", "Unknown")
        
        # Update client information with node details
        if client_id in connected_clients:
            connected_clients[client_id]["node_name"] = node_name
            connected_clients[client_id]["node_type"] = node_type
            connected_clients[client_id]["version"] = version
            
            # Additional fields if present
            if "capabilities" in message:
                connected_clients[client_id]["capabilities"] = message["capabilities"]
                
            logger.info(f"Node update from {node_name} (ID: {client_id}, Type: {node_type}, Version: {version})")
            
            # Return success response
            return {
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
        if client_id in connected_clients:
            # Store the sensor reading
            if "sensors" not in connected_clients[client_id]:
                connected_clients[client_id]["sensors"] = {}
                
            # Update the sensor data for this sensor type
            connected_clients[client_id]["sensors"][sensor_type] = {
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
    
    def check_sensor_thresholds(self, sensor_type, readings):
        """Check sensor readings against configured thresholds"""
        alerts = []
        
        # Define thresholds based on sensor type
        thresholds = {
            "temperature": {"high": 30, "low": 5},
            "humidity": {"high": 80, "low": 20},
            "smoke": {"high": 50},
            "motion": {"alert_on": True}
        }
        
        # Check each reading against thresholds
        for key, value in readings.items():
            if key in thresholds:
                threshold = thresholds[key]
                
                # Check high threshold
                if "high" in threshold and value > threshold["high"]:
                    alerts.append({
                        "sensor": key,
                        "level": "high",
                        "value": value,
                        "threshold": threshold["high"]
                    })
                
                # Check low threshold
                if "low" in threshold and value < threshold["low"]:
                    alerts.append({
                        "sensor": key,
                        "level": "low",
                        "value": value,
                        "threshold": threshold["low"]
                    })
                    
                # Check boolean alerts (like motion)
                if "alert_on" in threshold and value == threshold["alert_on"]:
                    alerts.append({
                        "sensor": key,
                        "level": "alert",
                        "value": value
                    })
        
        return alerts
    
    async def handle_status_request(self, message, client_id):
        """Handle status request messages"""
        # Return current server and client status
        if client_id in connected_clients:
            return {
                "status": "success",
                "server_time": time.time(),
                "connection_duration": time.time() - connected_clients[client_id]["connected_at"],
                "messages_received": len(connected_clients[client_id]["data"]),
                "client_id": client_id
            }
        else:
            return {"status": "error", "message": "Client not recognized"}
    
    async def handle_command_response(self, message, client_id):
        """Handle responses to commands sent to nodes"""
        command_id = message.get("command_id")
        success = message.get("success", False)
        response_data = message.get("data", {})
        
        logger.info(f"Command response from {client_id} for command {command_id}: {'Success' if success else 'Failed'}")
        
        # Update command status in client data
        if client_id in connected_clients:
            if "commands" not in connected_clients[client_id]:
                connected_clients[client_id]["commands"] = {}
                
            if command_id in connected_clients[client_id]["commands"]:
                connected_clients[client_id]["commands"][command_id]["completed"] = True
                connected_clients[client_id]["commands"][command_id]["success"] = success
                connected_clients[client_id]["commands"][command_id]["response"] = response_data
                
            return {"status": "success", "message": "Command response recorded"}
        else:
            return {"status": "error", "message": "Client not recognized"}
