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
PCB_SIZE_CM = (0.5, 0.53)  # PCB size in centimeters (width, height)

RESOLUTION = 30  # Resolution in points per centimeter
STEP_SIZE = 1 / RESOLUTION  # Step size in centimeters
x_values = [i * STEP_SIZE for i in range(int(PCB_SIZE_CM[0] / STEP_SIZE) + 1)]
y_values = [i * STEP_SIZE for i in range(int(PCB_SIZE_CM[1] / STEP_SIZE) + 1)]

# Radio measurement configuration
CENTER_FREQUENCY = 400e6  # Center frequency in Hz (default: 400 MHz)
EQUIVALENT_BW = 10e6      # Equivalent bandwidth in Hz (default: 50 MHz)
RX_GAIN = 76              # Receiver gain in dB
nb_avera = 100            # Number of measurements to average

# 3D printer configuration
PRINTER_IP = "192.168.2.100"  # Updated to match actual printer IP based on ping results
PRINTER_PORT = 23  # Default Telnet port for G-code communication
DEFAULT_Z = 98.2  # Default Z height in mm for printer positioning
with open("password.txt", "r") as file:
    PRINTER_PASSWORD = file.read().strip()  # Password is now loaded from password.txt file instead of being hardcoded

# Hardware simulation flag
SIMULATE_USRP = False  # Set to True to run without actual USRP hardware for testing

# Debug settings
DEBUG_ALL = False  # Set to True to enable verbose debug output throughout scanning

# Output configuration
PCB_IMAGE_PATH = "./pcb_die.jpg"  # Path to the PCB image
OUTPUT_FILE = "scan_v1a_400MHz_Rx_pcb.json"  # Default output file name
