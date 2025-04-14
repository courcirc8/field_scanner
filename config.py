# This module centralizes all configuration parameters for the field scanner system.
# It defines constants for:
# 1. PCB dimensions and scan resolution
# 2. Radio frequency settings and measurement parameters
# 3. Hardware connection information
# 4. Output and visualization settings
#
# Centralizing these parameters makes it easier to adjust the system for
# different PCBs, frequencies, and measurement conditions.

# PCB-related constants
#PCB_SIZE_CM = (2.165, 1.53)  # PCB size in centimeters (width, height)
PCB_SIZE_CM = (2.55, 2.0)  # PCB size in centimeters (width, height)
#PCB_SIZE_CM = (1.55, 1.06)  # PCB size in centimeters (width, height)


# Component position for max height measurement
MAX_HEIGHT_COMPONENT_X_MM = 8.0  # X position of the highest component in mm
MAX_HEIGHT_COMPONENT_Y_MM = 6.0   # Y position of the highest component in mm

RESOLUTION = 25  # Resolution in points per centimeter
STEP_SIZE = 1 / RESOLUTION  # Step size in centimeters
x_values = [i * STEP_SIZE for i in range(int(PCB_SIZE_CM[0] / STEP_SIZE) + 1)]
y_values = [i * STEP_SIZE for i in range(int(PCB_SIZE_CM[1] / STEP_SIZE) + 1)]

# Radio measurement configuration
CENTER_FREQUENCY = 400e6  # Center frequency in Hz (default: 400 MHz)
EQUIVALENT_BW = 10e6      # Equivalent bandwidth in Hz (default: 50 MHz)
RX_GAIN = 76              # Receiver gain in dB
nb_avera = 100            # Number of measurements to average

# 3D printer configuration
PRINTER_IP = "192.168.2.100"  # Printer IP address
PRINTER_PORT = 80  # Changed from 23 (Telnet) to 80 (HTTP)
DEFAULT_Z = 98.2  # Default Z height in mm for printer positioning
with open("password.txt", "r") as file:
    PRINTER_PASSWORD = file.read().strip()  # Password is now loaded from password.txt file instead of being hardcoded

# Hardware simulation flag
SIMULATE_USRP = False  # Set to True to run without actual USRP hardware for testing

# Debug settings
DEBUG_ALL = False  # Set to True to enable verbose debug output throughout scanning
DEBUG_INTERRACTIVE = True  # If True, print debug commands and update graphical view after each measurement

# USRP buffer and movement settings
MOVEMENT_SETTLE_DELAY = 0.05  # Delay after movement (in seconds) to allow mechanics to stabilize
BUFFER_FLUSH_COUNT = 8  # Increased from 3 to 8 to better handle buffering issues

# Output configuration
PCB_IMAGE_PATH = "./pcb_large_1.jpg"  # Path to the PCB image
OUTPUT_FILE = "scan_v1a_470o_400MHz_Rx_pcb_large.json"  # Default output file name

# Visualization configuration
VERTICAL_FLIP = True # Whether to flip the PCB image vertically for proper alignment
HORIZONTAL_FLIP = False  # Whether to flip the PCB image horizontally

# Current visualization settings
CURRENT_GRID_SPACING_MM = 2.0  # Grid spacing for current direction arrows in mm


