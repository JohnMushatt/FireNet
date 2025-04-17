import asyncio
import json
import logging
import os
import sys
import time
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SocketServer")

# Store connected clients
connected_clients = {}
MAX_CLIENTS = 5

async def handle_client(reader, writer):
    """Handle a client connection."""
    # Generate a unique client ID
    client_id = str(uuid.uuid4())
    addr = writer.get_extra_info('peername')
    
    client_info = {
        "reader": reader,
        "writer": writer,
        "addr": addr,
        "connected_at": time.time(),
        "last_message": None,
        "data": []
    }
    
    # Check if we can accept more clients
    if len(connected_clients) >= MAX_CLIENTS:
        logger.warning(f"Maximum clients reached. Rejecting new connection from {addr}")
        writer.write(json.dumps({"status": "error", "message": "Server full"}).encode() + b'\n')
        await writer.drain()
        writer.close()
        await writer.wait_closed()
        return
    
    # Add the client to our dictionary
    connected_clients[client_id] = client_info
    logger.info(f"New client connected from {addr}. ID: {client_id}. Total clients: {len(connected_clients)}")
    
    try:
        # Send welcome message
        writer.write(json.dumps({"status": "connected", "client_id": client_id}).encode() + b'\n')
        await writer.drain()
        
        # Handle messages from the client
        while True:
            data = await reader.readline()
            if not data:  # Client disconnected
                break
                
            try:
                decoded_data = data.decode('utf-8')
                message = json.loads(decoded_data)
                logger.info(f"Received data from {client_id}: {message}")
                
                # Update client info
                client_info["last_message"] = time.time()
                client_info["data"].append(message)
                
                # Process the data (you can customize this part)
                response = {"status": "msg_received", "timestamp": time.time()}
                writer.write(json.dumps(response).encode() + b'\n')
                await writer.drain()
                
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON from client {client_id}")
                writer.write(json.dumps({"status": "error", "message": "Invalid JSON"}).encode() + b'\n')
                await writer.drain()
    
    except Exception as e:
        logger.error(f"Error handling client {client_id}: {e}")
    
    finally:
        # Remove client when they disconnect
        if client_id in connected_clients:
            del connected_clients[client_id]
            logger.info(f"Client {client_id} removed. Total clients: {len(connected_clients)}")
        writer.close()
        await writer.wait_closed()

async def status_monitor():
    """Periodically print server status"""
    while True:
        logger.info(f"Server status: {len(connected_clients)}/{MAX_CLIENTS} clients connected")
        await asyncio.sleep(60)  # Update every minute

async def main():
    # Get local IP address or use localhost
    host = "0.0.0.0"  # Listen on all network interfaces
    port = 8765
    
    # Start the TCP server
    server = await asyncio.start_server(handle_client, host, port)
    
    addr = server.sockets[0].getsockname()
    logger.info(f'TCP server started on {addr}')
    #hostname = server.sockets[0].getsockname()
    ip_address = server.sockets[0].getsockname()
    import socket
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)
    logger.info(f"WebSocket server address: {ip_address} <----- Put this in esp self.server_ip variable")
    # Start status monitor
    monitor_task = asyncio.create_task(status_monitor())
    
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server shutting down")
        sys.exit(0)