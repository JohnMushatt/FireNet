import asyncio
import json
import websockets
import logging
import os
import sys
import time
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("WebSocketServer")

# Store connected clients

class WebSocketServer:
    def __init__(self, host='0.0.0.0', port=8765):
        self.host = host
        self.port = port
        self.server = None
        self.clients = set()

    # Handle WebSocket connections
    async def handle_connection(self, websocket, path):
        esp32_id = None
        try:
            # Add new client to connected set
            self.clients.add(websocket)
            logger.info(f"New client connected. Total clients: {len(self.clients)}")
            
            # Main communication loop
            async for message in websocket:
                # Process registration message
                if message.startswith('REGISTER:'):
                    esp32_id = message.split(':', 1)[1]
                    logger.info(f"ESP32 registered with ID: {esp32_id}")
                    await websocket.send(json.dumps({"status": "registered"}))
                    continue
                    
                # Process regular data
                await self.process_data(message, websocket)
                
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Connection closed for ESP32 {esp32_id or 'unknown'}")
        finally:
            # Remove client when disconnected
            self.clients.remove(websocket)
            logger.info(f"Client disconnected. Remaining clients: {len(self.clients)}")

    # Data processing function

    async def process_data(self, data, websocket) -> bool:
        
        try:
            parsed_data = json.loads(data)
            logger.info(f"Received data: {parsed_data}")
            
            # Example: respond to temperature readings over threshold
            
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received: {data}")
            return False
        return True
    
    async def run(self):
        logger.info(f"Starting WebSocket server on {self.host}:{self.port}")
        server = await websockets.serve(self.handle_connection, "0.0.0.0", 8765)
        logger.info("WebSocket server started on ws://0.0.0.0:8765")
        
        # Server keeps running
        await server.wait_closed()

async def main():
    server = WebSocketServer()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())