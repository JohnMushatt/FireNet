import time


class Logger:
    # Log levels
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50
    
    # Level names for display
    LEVEL_NAMES = {
        DEBUG: "DEBUG",
        INFO: "INFO",
        WARNING: "WARNING",
        ERROR: "ERROR",
        CRITICAL: "CRITICAL"
    }
    
    # ANSI color codes
    COLORS = {
        DEBUG: "\033[36m",      # Cyan
        INFO: "\033[34m",       # Blue
        WARNING: "\033[33m",    # Yellow
        ERROR: "\033[31m",      # Red
        CRITICAL: "\033[35m",   # Magenta
    }

    RESET = "\033[0m"
    
    max_level_len = len(LEVEL_NAMES[CRITICAL])
    
    def __init__(self, min_level=INFO, use_color=True):
        """Initialize logger with minimum level to display."""
        self.min_level = min_level
        self.use_color = use_color
    
    def _log(self, level=DEBUG, driver_str=None, func_str=None, message=None):
        """Internal logging method."""
        if level < self.min_level:
            return
            
        # Get current timestamp
        timestamp = time.localtime()
        time_str = "{:02d}:{:02d}:{:02d}".format(
            timestamp[3],  # Hour
            timestamp[4],  # Minute
            timestamp[5],  # Second
        )
        
        # Format and print message
        level_name = self.LEVEL_NAMES.get(level, "UNKNOWN")
        

        # Add color if enabled
        if self.use_color:
            
            color_level = self.COLORS.get(level, self.RESET)

            color_driver = self.COLORS.get(logger.WARNING, self.RESET)
            color_func = self.COLORS.get(logger.ERROR, self.RESET)

            print(f"[{time_str}]*[{color_level}{level_name}{self.RESET}]*[{color_driver}{driver_str}{self.RESET}]*[{color_func}{func_str}{self.RESET}] -> {message}")
        else:
            print(f"[{time_str}]*[{level_name}]*[{driver_str}]*[{func_str}] -> {message}")
    
    def debug(self, driver_str, func_str, message):
        """Log debug message."""
        self._log(self.DEBUG, driver_str, func_str, message)
    
    def info(self, driver_str, func_str, message):
        """Log info message."""
        self._log(self.INFO, driver_str, func_str, message)
    
    def warning(self, driver_str, func_str, message):
        """Log warning message."""
        self._log(self.WARNING, driver_str, func_str, message)
    
    def error(self, driver_str, func_str, message):
        """Log error message."""
        self._log(self.ERROR, driver_str, func_str, message)
    
    def critical(self, driver_str, func_str, message):
        """Log critical message."""
        self._log(self.CRITICAL, driver_str, func_str, message)


"""
For development set to Level DEBUG
logger = Logger(Logger.DEBUG)
Global logger for the node
"""
logger = Logger(Logger.INFO, use_color=True)