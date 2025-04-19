import errno

def read_network_config(file_path='network_config.ini'):
    """Read network configurations from ini file.
    
    Returns a dictionary with network configurations where each key is a network name
    and each value is a dictionary containing 'ssid' and 'password'.
    """
    networks = {}
    current_network = None
    
    try:
        # Open and read the configuration file
        with open(file_path, 'r') as f:
            lines = f.readlines()
            
        # Parse each line for configuration
        for line in lines:
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
                
            # Check if this is a network section header [network_name]
            if line.startswith('[') and line.endswith(']'):
                current_network = line[1:-1].strip()
                networks[current_network] = {
                    'ssid': None,
                    'password': None
                }
                continue
                
            # Only process key-value pairs if we're in a network section
            if current_network is None:
                continue
                
            # Split by equals sign or colon
            if '=' in line:
                key, value = line.split('=', 1)
            elif ':' in line:
                key, value = line.split(':', 1)
            else:
                continue
                
            # Remove extra whitespace
            key = key.strip().lower()
            value = value.strip()
            
            # Store the value in the appropriate network config
            if key == 'ssid':
                networks[current_network]['ssid'] = value
            elif key == 'password':
                networks[current_network]['password'] = value
        

            
        print(f"Read {len(networks)} network configurations from {file_path}")
        return networks
        
    except OSError as e:
        # Handle file not found error
        if e.args[0] == errno.ENOENT:  # File not found
            print(f"Config file {file_path} not found. Using default config.")
        else:
            print(f"Error reading config file: {e}")
        
        # Return default hotspot config if file can't be read
        #return {'hotspot': hotspot_config}