import asyncio
import json
import logging
import os
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import socket
import uuid
from message_parser import MessageParser
# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ServerUI")

# Store connected clients
connected_clients = {}
MAX_CLIENTS = 5

class ServerUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Network Server Control")
        self.root.geometry("900x600")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.server_running = False
        self.server_thread = None
        self.loop = None
        self.server = None
        self.message_parser = MessageParser()
        self.setup_ui()
        self.update_status_display()
        
    def setup_ui(self):
        # Create notebook (tabs)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create tabs
        self.server_tab = ttk.Frame(self.notebook)
        self.clients_tab = ttk.Frame(self.notebook)
        self.message_tab = ttk.Frame(self.notebook)
        self.simulate_tab = ttk.Frame(self.notebook)  # New tab

        self.notebook.add(self.server_tab, text="Server Control")
        self.notebook.add(self.clients_tab, text="Clients")
        self.notebook.add(self.message_tab, text="Message Builder")
        self.notebook.add(self.simulate_tab, text="Simulate")
        
        # Server Control Tab
        self.setup_server_tab()
        
        # Clients Tab
        self.setup_clients_tab()
        
        # Message Builder Tab
        self.setup_message_tab()
        
        # Simulate Tab
        self.setup_simulate_tab()
    
    def setup_server_tab(self):
        # Server Control Frame
        control_frame = ttk.LabelFrame(self.server_tab, text="Server Control")
        control_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Server start/stop button
        self.server_button = ttk.Button(control_frame, text="Start Server", command=self.toggle_server)
        self.server_button.pack(padx=10, pady=10)
        
        # Server status frame
        status_frame = ttk.LabelFrame(control_frame, text="Server Status")
        status_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # IP and Port display
        ip_frame = ttk.Frame(status_frame)
        ip_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(ip_frame, text="Server IP:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.ip_var = tk.StringVar(value="Not running")
        ttk.Label(ip_frame, textvariable=self.ip_var).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(ip_frame, text="Server Port:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.port_var = tk.StringVar(value="Not running")
        ttk.Label(ip_frame, textvariable=self.port_var).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Connected clients count
        ttk.Label(ip_frame, text="Connected Clients:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.client_count_var = tk.StringVar(value="0/5")
        ttk.Label(ip_frame, textvariable=self.client_count_var).grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Log display
        log_frame = ttk.LabelFrame(control_frame, text="Server Log")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.log_display = scrolledtext.ScrolledText(log_frame, height=10)
        self.log_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.log_display.config(state=tk.DISABLED)
        
        # Add a custom handler to redirect logs to the text widget
        self.log_handler = TextHandler(self.log_display)
        logger.addHandler(self.log_handler)
    
    def setup_clients_tab(self):
        # Clients List Frame
        clients_frame = ttk.LabelFrame(self.clients_tab, text="Connected Clients")
        clients_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create Treeview for clients
        columns = ('id', 'ip', 'port', 'connected_at', 'last_message')
        self.clients_tree = ttk.Treeview(clients_frame, columns=columns, show='headings')
        
        # Define headings
        self.clients_tree.heading('id', text='Client ID')
        self.clients_tree.heading('ip', text='IP Address')
        self.clients_tree.heading('port', text='Port')
        self.clients_tree.heading('connected_at', text='Connected At')
        self.clients_tree.heading('last_message', text='Last Message')
        
        # Define columns width
        self.clients_tree.column('id', width=200)
        self.clients_tree.column('ip', width=120)
        self.clients_tree.column('port', width=70)
        self.clients_tree.column('connected_at', width=150)
        self.clients_tree.column('last_message', width=150)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(clients_frame, orient=tk.VERTICAL, command=self.clients_tree.yview)
        self.clients_tree.configure(yscroll=scrollbar.set)
        
        # Pack widgets
        self.clients_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Client details frame
        details_frame = ttk.LabelFrame(self.clients_tab, text="Client Details")
        details_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Data from client
        self.client_data = scrolledtext.ScrolledText(details_frame, height=10)
        self.client_data.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Bind selection event
        self.clients_tree.bind('<<TreeviewSelect>>', self.on_client_select)
    
    def setup_message_tab(self):
        # Message builder frame
        builder_frame = ttk.LabelFrame(self.message_tab, text="JSON Message Builder")
        builder_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Message editor
        ttk.Label(builder_frame, text="Enter JSON message:").pack(anchor=tk.W, padx=5, pady=5)
        
        self.message_editor = scrolledtext.ScrolledText(builder_frame, height=10)
        self.message_editor.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.message_editor.insert(tk.END, '{\n    "command": "status",\n    "parameter": "value"\n}')
        
        # Field quick-add
        field_frame = ttk.Frame(builder_frame)
        field_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(field_frame, text="Add field:").grid(row=0, column=0, padx=5, pady=5)
        
        self.field_name = ttk.Entry(field_frame, width=15)
        self.field_name.grid(row=0, column=1, padx=5, pady=5)
        self.field_name.insert(0, "field_name")
        
        self.field_value = ttk.Entry(field_frame, width=15)
        self.field_value.grid(row=0, column=2, padx=5, pady=5)
        self.field_value.insert(0, "value")
        
        ttk.Button(field_frame, text="Add Field", command=self.add_json_field).grid(row=0, column=3, padx=5, pady=5)
        
        # Target client selection
        client_frame = ttk.Frame(builder_frame)
        client_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(client_frame, text="Target Client:").grid(row=0, column=0, padx=5, pady=5)
        
        self.target_client = ttk.Combobox(client_frame, width=30)
        self.target_client.grid(row=0, column=1, padx=5, pady=5)
        
        # Send button
        send_frame = ttk.Frame(builder_frame)
        send_frame.pack(padx=5, pady=10)
        
        ttk.Button(send_frame, text="Send to Selected Client", command=self.send_json_message).pack(side=tk.LEFT, padx=5)
        ttk.Button(send_frame, text="Send to All Clients", command=lambda: self.send_json_message(all_clients=True)).pack(side=tk.LEFT, padx=5)
        ttk.Button()
        # Message templates
        templates_frame = ttk.LabelFrame(self.message_tab, text="Message Templates")
        templates_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        templates = [
            ("Status Query", '{\n    "command": "status"\n}'),
            ("Set LED Color", '{\n    "command": "set_led",\n    "color": [255, 0, 0]\n}'),
            ("Reset Device", '{\n    "command": "reset"\n}')
        ]
        
        for i, (name, template) in enumerate(templates):
            btn = ttk.Button(templates_frame, text=name, 
                           command=lambda t=template: self.load_template(t))
            btn.grid(row=i//3, column=i%3, padx=10, pady=5, sticky=tk.W)
    def setup_simulate_tab(self):
        # Main frame
        simulate_frame = ttk.LabelFrame(self.simulate_tab, text="Simulate Client Connection")
        simulate_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Client configuration
        config_frame = ttk.Frame(simulate_frame)
        config_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Client IP
        ttk.Label(config_frame, text="Simulated Client IP:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.sim_client_ip = ttk.Entry(config_frame, width=15)
        self.sim_client_ip.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        self.sim_client_ip.insert(0, "192.168.1.100")
        
        # Client ID (optional)
        ttk.Label(config_frame, text="Client ID (optional):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.sim_client_id = ttk.Entry(config_frame, width=36)
        self.sim_client_id.grid(row=1, column=1, columnspan=2, sticky=tk.W, padx=5, pady=5)
        
        # Client Type / Sensor Type
        ttk.Label(config_frame, text="Sensor Type:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.sim_client_type = ttk.Combobox(config_frame, width=20)
        self.sim_client_type.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        self.sim_client_type['values'] = ('Temperature/Humidity', 'Smoke Detector', 'Motion Sensor', 'Custom')
        self.sim_client_type.current(0)
        self.sim_client_type.bind('<<ComboboxSelected>>', self.on_sim_type_selected)
        
        # Connect/Disconnect button
        self.sim_connect_button = ttk.Button(config_frame, text="Simulate Connection", command=self.simulate_connection)
        self.sim_connect_button.grid(row=0, column=2, rowspan=2, padx=10, pady=5)
        
        # Message editor
        message_frame = ttk.LabelFrame(simulate_frame, text="Message Data")
        message_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        ttk.Label(message_frame, text="Enter JSON message to simulate receiving:").pack(anchor=tk.W, padx=5, pady=5)
        
        self.sim_message_editor = scrolledtext.ScrolledText(message_frame, height=10)
        self.sim_message_editor.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.sim_message_editor.insert(tk.END, '{\n    "temperature": 22.5,\n    "humidity": 45.2,\n    "smoke": 10\n}')
        
        # Sensor value sliders
        slider_frame = ttk.LabelFrame(simulate_frame, text="Quick Sensor Values")
        slider_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Temperature slider
        ttk.Label(slider_frame, text="Temperature:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.temp_var = tk.DoubleVar(value=22.5)
        temp_slider = ttk.Scale(slider_frame, from_=0, to=100, orient=tk.HORIZONTAL, 
                            variable=self.temp_var, length=200,
                            command=lambda v: self.update_sim_values('temperature', self.temp_var.get()))
        temp_slider.grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(slider_frame, textvariable=self.temp_var).grid(row=0, column=2, padx=5, pady=5)
        
        # Humidity slider
        ttk.Label(slider_frame, text="Humidity:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.humidity_var = tk.DoubleVar(value=45.2)
        humidity_slider = ttk.Scale(slider_frame, from_=0, to=100, orient=tk.HORIZONTAL, 
                                variable=self.humidity_var, length=200,
                                command=lambda v: self.update_sim_values('humidity', self.humidity_var.get()))
        humidity_slider.grid(row=1, column=1, padx=5, pady=5)
        ttk.Label(slider_frame, textvariable=self.humidity_var).grid(row=1, column=2, padx=5, pady=5)
        
        # Smoke sensor slider
        ttk.Label(slider_frame, text="Smoke Level:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.smoke_var = tk.DoubleVar(value=10)
        smoke_slider = ttk.Scale(slider_frame, from_=0, to=100, orient=tk.HORIZONTAL, 
                                variable=self.smoke_var, length=200,
                                command=lambda v: self.update_sim_values('smoke', self.smoke_var.get()))
        smoke_slider.grid(row=2, column=1, padx=5, pady=5)
        ttk.Label(slider_frame, textvariable=self.smoke_var).grid(row=2, column=2, padx=5, pady=5)
        
        # Transmission control
        send_frame = ttk.Frame(simulate_frame)
        send_frame.pack(fill=tk.X, padx=5, pady=10)
        
        # Send single message
        ttk.Button(send_frame, text="Send Single Message", 
                command=self.simulate_receive_message).pack(side=tk.LEFT, padx=5)
        
        # Start/stop continuous transmission
        self.sim_continuous_var = tk.BooleanVar(value=False)
        self.sim_continuous_button = ttk.Button(send_frame, text="Start Continuous Send",
                                            command=self.toggle_continuous_simulation)
        self.sim_continuous_button.pack(side=tk.LEFT, padx=5)
        
        # Interval for continuous transmission
        ttk.Label(send_frame, text="Interval (sec):").pack(side=tk.LEFT, padx=5)
        self.sim_interval_var = tk.DoubleVar(value=5.0)
        ttk.Spinbox(send_frame, from_=0.5, to=60, increment=0.5, 
                textvariable=self.sim_interval_var, width=5).pack(side=tk.LEFT, padx=5)
        
        # Simulation log
        log_frame = ttk.LabelFrame(simulate_frame, text="Simulation Log")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.sim_log = scrolledtext.ScrolledText(log_frame, height=6)
        self.sim_log.pack(fill=tk.BOTH, expand=True)
        self.sim_log.config(state=tk.DISABLED)
        
        # Initialize simulated client state
        self.sim_client_connected = False
        self.sim_client_info = None
        self.continuous_sim_running = False
        self.continuous_sim_task = None
        
    def add_json_field(self):
        """Add a field to the JSON editor"""
        try:
            # Get current JSON
            current_text = self.message_editor.get("1.0", tk.END)
            
            # Parse JSON
            try:
                json_data = json.loads(current_text)
            except json.JSONDecodeError:
                # If not valid JSON, start fresh
                json_data = {}
            
            # Add new field
            field_name = self.field_name.get()
            field_value = self.field_value.get()
            
            # Try to convert to int or float if possible
            try:
                field_value = int(field_value)
            except ValueError:
                try:
                    field_value = float(field_value)
                except ValueError:
                    # Keep as string
                    pass
            
            json_data[field_name] = field_value
            
            # Format and update JSON
            formatted_json = json.dumps(json_data, indent=4)
            self.message_editor.delete("1.0", tk.END)
            self.message_editor.insert("1.0", formatted_json)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add field: {str(e)}")
    def on_sim_type_selected(self, event):
        """Update message template based on selected sensor type"""
        sensor_type = self.sim_client_type.get()
        
        if sensor_type == 'Temperature/Humidity':
            template = '{\n    "temperature": 22.5,\n    "humidity": 45.2\n}'
        elif sensor_type == 'Smoke Detector':
            template = '{\n    "smoke": 10,\n    "battery": 95\n}'
        elif sensor_type == 'Motion Sensor':
            template = '{\n    "motion": false,\n    "battery": 90\n}'
        else:  # Custom - don't change
            return
            
        self.sim_message_editor.delete("1.0", tk.END)
        self.sim_message_editor.insert(tk.END, template)

    def update_sim_values(self, field_name, value):
        """Update a value in the simulation message editor"""
        try:
            # Get current JSON
            current_text = self.sim_message_editor.get("1.0", tk.END)
            
            # Parse JSON
            try:
                json_data = json.loads(current_text)
            except json.JSONDecodeError:
                # If not valid JSON, start fresh
                json_data = {}
            
            # Update field
            json_data[field_name] = float(value)
            
            # Format and update JSON
            formatted_json = json.dumps(json_data, indent=4)
            self.sim_message_editor.delete("1.0", tk.END)
            self.sim_message_editor.insert("1.0", formatted_json)
            
        except Exception as e:
            self.log_to_sim("Error updating values: " + str(e))

    def simulate_connection(self):
        """Simulate a client connecting/disconnecting"""
        if not self.server_running:
            messagebox.showerror("Error", "Server is not running. Start the server first.")
            return
        
        if not self.sim_client_connected:
            # Simulate new connection
            client_ip = self.sim_client_ip.get()
            
            # Use provided client ID or generate one
            client_id = self.sim_client_id.get().strip()
            if not client_id:
                client_id = str(uuid.uuid4())
                self.sim_client_id.delete(0, tk.END)
                self.sim_client_id.insert(0, client_id)
            
            # Create the simulated client
            self.sim_client_info = {
                "client_id": client_id,
                "addr": (client_ip, 12345),  # Fake port
                "connected_at": time.time(),
                "last_message": None,
                "data": []
            }
            
            # Add to connected clients (exclude reader/writer which we don't need)
            connected_clients[client_id] = self.sim_client_info
            
            # Update UI
            self.update_clients_view()
            self.update_client_dropdown()
            self.sim_client_connected = True
            self.sim_connect_button.config(text="Disconnect Simulated Client")
            
            # Log
            self.log_to_sim(f"Simulated client connected with ID: {client_id}")
            logger.info(f"Simulated client connected from {client_ip}. ID: {client_id}")
            
        else:
            # Disconnect simulated client
            if self.sim_client_info and self.sim_client_info["client_id"] in connected_clients:
                client_id = self.sim_client_info["client_id"]
                del connected_clients[client_id]
                
                # Update UI
                self.update_clients_view()
                self.update_client_dropdown()
                
                # Log
                self.log_to_sim(f"Simulated client disconnected: {client_id}")
                logger.info(f"Simulated client {client_id} disconnected")
                
            self.sim_client_connected = False
            self.sim_client_info = None
            self.sim_connect_button.config(text="Simulate Connection")
            
            # Stop continuous simulation if running
            if self.continuous_sim_running:
                self.toggle_continuous_simulation()

    def simulate_receive_message(self):
        """Simulate receiving a message from the connected simulated client"""
        if not self.server_running:
            messagebox.showerror("Error", "Server is not running. Start the server first.")
            return
            
        if not self.sim_client_connected:
            messagebox.showerror("Error", "No simulated client connected. Connect a client first.")
            return
        
        try:
            # Get message from editor
            message_text = self.sim_message_editor.get("1.0", tk.END).strip()
            json_data = json.loads(message_text)
            
            # Get client info
            client_id = self.sim_client_info["client_id"]
            client_info = connected_clients[client_id]
            
            # Update client info as if we received a message
            client_info["last_message"] = time.time()
            client_info["data"].append(json_data)
            
            # Update UI
            self.update_clients_view()
            
            # Log the simulated message
            self.log_to_sim(f"Sent message: {message_text}")
            logger.info(f"Simulated message from {client_id}: {json_data}")
            
        except json.JSONDecodeError:
            messagebox.showerror("Error", "Invalid JSON in message editor")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to simulate message: {str(e)}")

    def toggle_continuous_simulation(self):
        """Start or stop continuous message simulation"""
        if self.continuous_sim_running:
            # Stop simulation
            self.continuous_sim_running = False
            self.sim_continuous_button.config(text="Start Continuous Send")
            self.log_to_sim("Stopped continuous message simulation")
        else:
            # Start simulation if we have a connected client
            if not self.sim_client_connected:
                messagebox.showerror("Error", "No simulated client connected. Connect a client first.")
                return
                
            self.continuous_sim_running = True
            self.sim_continuous_button.config(text="Stop Continuous Send")
            self.log_to_sim(f"Started continuous message simulation (interval: {self.sim_interval_var.get()} sec)")
            
            # Schedule the continuous sending
            self.schedule_next_simulation()

    def schedule_next_simulation(self):
        """Schedule the next simulated message if continuous mode is active"""
        if self.continuous_sim_running and self.sim_client_connected:
            # Send a message
            self.simulate_receive_message()
            
            # Schedule the next one
            interval_ms = int(self.sim_interval_var.get() * 1000)
            self.continuous_sim_task = self.root.after(interval_ms, self.schedule_next_simulation)
        else:
            self.continuous_sim_running = False
            self.sim_continuous_button.config(text="Start Continuous Send")

    def log_to_sim(self, message):
        """Add a message to the simulation log"""
        self.sim_log.config(state=tk.NORMAL)
        self.sim_log.insert(tk.END, f"{time.strftime('%H:%M:%S')} - {message}\n")
        self.sim_log.see(tk.END)  # Scroll to the end
        self.sim_log.config(state=tk.DISABLED)

    def on_closing(self):
        """Update on_closing to handle simulation resources"""
        # Stop continuous simulation if running
        if hasattr(self, 'continuous_sim_running') and self.continuous_sim_running:
            self.continuous_sim_running = False
            if self.continuous_sim_task:
                self.root.after_cancel(self.continuous_sim_task)
        
        # Clean up simulated client if connected
        if hasattr(self, 'sim_client_connected') and self.sim_client_connected:
            if self.sim_client_info and self.sim_client_info["client_id"] in connected_clients:
                del connected_clients[self.sim_client_info["client_id"]]
        
        # Original closing logic
        if self.server_running:
            if messagebox.askokcancel("Quit", "The server is still running. Do you want to stop it and quit?"):
                self.stop_server()
                self.root.destroy()
        else:
            self.root.destroy()
    def load_template(self, template):
        """Load a template into the JSON editor"""
        self.message_editor.delete("1.0", tk.END)
        self.message_editor.insert("1.0", template)
    
    def send_json_message(self, all_clients=False):
        """Send JSON message to selected client or all clients"""
        try:
            # Get message
            message_text = self.message_editor.get("1.0", tk.END)
            json_data = json.loads(message_text)
            
            # Format message
            message = json.dumps(json_data) + '\n'
            encoded_message = message.encode('utf-8')
            
            if not self.server_running:
                messagebox.showwarning("Server not running", "The server is not running. Start it first.")
                return
            
            if all_clients:
                # Send to all clients
                for client_id, client_info in connected_clients.items():
                    try:
                        client_info["writer"].write(encoded_message)
                        asyncio.run_coroutine_threadsafe(client_info["writer"].drain(), self.loop)
                        logger.info(f"Message sent to all clients")
                    except Exception as e:
                        logger.error(f"Failed to send to client {client_id}: {e}")
            else:
                # Send to selected client
                selected_client = self.target_client.get()
                if not selected_client:
                    messagebox.showwarning("No client selected", "Please select a client from the dropdown.")
                    return
                
                client_id = selected_client.split(' ')[0]  # Extract ID from combobox text
                
                if client_id in connected_clients:
                    try:
                        connected_clients[client_id]["writer"].write(encoded_message)
                        asyncio.run_coroutine_threadsafe(connected_clients[client_id]["writer"].drain(), self.loop)
                        logger.info(f"Message sent to client {client_id}")
                    except Exception as e:
                        logger.error(f"Failed to send to client {client_id}: {e}")
                else:
                    messagebox.showwarning("Client not found", f"Client {client_id} is no longer connected.")
                    self.update_client_dropdown()
        
        except json.JSONDecodeError:
            messagebox.showerror("Invalid JSON", "The message is not valid JSON.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to send message: {str(e)}")
    
    def toggle_server(self):
        """Start or stop the server"""
        if not self.server_running:
            self.start_server()
        else:
            self.stop_server()
    
    def start_server(self):
        """Start the server in a separate thread"""
        self.server_running = True
        self.server_button.config(text="Stop Server")
        
        # Start server in a new thread
        self.server_thread = threading.Thread(target=self.run_server)
        self.server_thread.daemon = True
        self.server_thread.start()
        
        logger.info("Server starting...")
    
    def stop_server(self):
        """Stop the running server"""
        if self.loop and self.server:
            # Schedule server stop in the event loop
            asyncio.run_coroutine_threadsafe(self.cleanup_server(), self.loop)
            
            # Wait for the server to stop
            if self.server_thread:
                self.server_thread.join(timeout=2.0)
            
            self.server_running = False
            self.server_button.config(text="Start Server")
            self.ip_var.set("Not running")
            self.port_var.set("Not running")
            self.client_count_var.set("0/5")
            
            # Clear the clients treeview
            for item in self.clients_tree.get_children():
                self.clients_tree.delete(item)
            
            logger.info("Server stopped")
    
    async def cleanup_server(self):
        """Clean up the server resources"""
        # Close all client connections
        for client_id, client_info in connected_clients.items():
            client_info["writer"].close()
            await client_info["writer"].wait_closed()
        
        connected_clients.clear()
        
        # Close the server
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.server = None
    
    def run_server(self):
        """Run the asyncio server"""
        async def run_async_server():
            host = "0.0.0.0"  # Listen on all network interfaces
            port = 8765
            
            self.server = await asyncio.start_server(self.handle_client, host, port)
            
            addr = self.server.sockets[0].getsockname()
            logger.info(f'TCP server started on {addr}')
            
            # Get local IP address
            hostname = socket.gethostname()

            
            ip_address = get_ip_address()#socket.gethostbyname(hostname)
            
            # Update UI (in the main thread)
            self.root.after(0, lambda: self.ip_var.set(ip_address))
            self.root.after(0, lambda: self.port_var.set(str(port)))
            
            # Log the IP to use for ESP32
            logger.info(f"WebSocket server address: {ip_address} <----- Put this in esp self.server_ip variable")
            
            # Start status monitor 
            monitor_task = asyncio.create_task(self.status_monitor())
            
            async with self.server:
                try:
                    await self.server.serve_forever()
                except Exception as e:
                    if isinstance(e, asyncio.CancelledError):
                        print(f"Server cancelled error: {e}")
                        pass
        # Create new event loop for this thread
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        try:
            self.loop.run_until_complete(run_async_server())
        except Exception as e:
            logger.error(f"Server error: {e}")
        finally:
            self.loop.close()
            self.loop = None
    
    async def handle_client(self, reader, writer):
        """Handle a client connection"""
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
        
        # Update the UI in the main thread
        self.root.after(0, self.update_clients_view)
        self.root.after(0, self.update_client_dropdown)
        
        try:
            # Send welcome message
            #writer.write(json.dumps({"status": "connected", "client_id": client_id}).encode() + b'\n')
            #await writer.drain()
            
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
                    
                    # Update UI
                    self.root.after(0, self.update_clients_view)
                    resp = await self.parse_message(message,client_id=client_id)
                    writer.write(json.dumps(resp).encode() + b'\n')
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
                logger.info(f"Client {client_id} disconnected. Total clients: {len(connected_clients)}")
                # Update UI
                self.root.after(0, self.update_clients_view)
                self.root.after(0, self.update_client_dropdown)
            try:
                writer.close()
                await writer.wait_closed()
            except ConnectionResetError:
                logger.warning(f"Connection was reset by client {client_id}")
            except Exception as e:
                logger.error(f"Error while closing connection with client {client_id}: {e}")
    async def parse_message(self, message, client_id):
        """Parse incoming message and route to appropriate handler"""
        try:
            # Determine message type
            msg_type = message.get("msg_id", "unknown")
            
            # Log the message type and source
            logger.info(f"Processing {msg_type} message from {client_id}")
            resp = {"msg_id": "node_update_ack", "status": "ok"}
            return resp
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

    async def status_monitor(self):
        """Periodically update server status"""
        while True:
            # Update client count in UI (must be done in main thread)
            self.root.after(0, self.update_status_display)
            await asyncio.sleep(5)  # Update every 5 seconds
    
    def update_status_display(self):
        """Update the status display"""
        self.client_count_var.set(f"{len(connected_clients)}/{MAX_CLIENTS}")
    
    def update_clients_view(self):
        """Update the clients treeview with current clients"""
        # Clear existing items
        for item in self.clients_tree.get_children():
            self.clients_tree.delete(item)
        
        # Add current clients
        for client_id, client_info in connected_clients.items():
            ip, port = client_info["addr"]
            connected_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(client_info["connected_at"]))
            
            last_message = "Never"
            if client_info["last_message"]:
                last_message = time.strftime("%H:%M:%S", time.localtime(client_info["last_message"]))
            
            self.clients_tree.insert('', tk.END, values=(client_id, ip, port, connected_at, last_message))
    
    def update_client_dropdown(self):
        """Update the client dropdown in the message tab"""
        clients = []
        for client_id, client_info in connected_clients.items():
            ip, port = client_info["addr"]
            clients.append(f"{client_id} ({ip}:{port})")
        
        self.target_client['values'] = clients
        if clients:
            self.target_client.current(0)
    
    def on_client_select(self, event):
        """When a client is selected, display its data"""
        selected_items = self.clients_tree.selection()
        if not selected_items:
            return
        
        item = selected_items[0]
        client_id = self.clients_tree.item(item, 'values')[0]
        
        if client_id in connected_clients:
            self.client_data.config(state=tk.NORMAL)
            self.client_data.delete("1.0", tk.END)
            
            client_info = connected_clients[client_id]
            data = client_info["data"]
            
            if data:
                for i, msg in enumerate(data):
                    self.client_data.insert(tk.END, f"Message {i+1}:\n")
                    self.client_data.insert(tk.END, json.dumps(msg, indent=4) + "\n\n")
            else:
                self.client_data.insert(tk.END, "No data received from this client yet.")
            
            self.client_data.config(state=tk.DISABLED)
    
    def on_closing(self):
        """Handle window close event"""
        if self.server_running:
            if messagebox.askokcancel("Quit", "The server is still running. Do you want to stop it and quit?"):
                self.stop_server()
                self.root.destroy()
        else:
            self.root.destroy()

class TextHandler(logging.Handler):
    """Handler that redirects logging output to a tkinter Text widget"""
    def __init__(self, text_widget):
        logging.Handler.__init__(self)
        self.text_widget = text_widget
    
    def emit(self, record):
        msg = self.format(record)
        
        # Schedule the update in the main thread
        self.text_widget.after(0, self.update_widget, msg)
    
    def update_widget(self, msg):
        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.insert(tk.END, msg + '\n')
        self.text_widget.see(tk.END)  # Scroll to the end
        self.text_widget.config(state=tk.DISABLED)
def get_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Doesn't need to be reachable
        s.connect(('10.255.255.255', 1))
        ip_address = s.getsockname()[0]
    except Exception:
        ip_address = '127.0.0.1'
    finally:
        s.close()
    return ip_address
if __name__ == "__main__":
    root = tk.Tk()
    app = ServerUI(root)
    root.mainloop()