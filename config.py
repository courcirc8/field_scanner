# PCB-related constants
PCB_SIZE_CM = (2.165, 1.53)  # PCB size in centimeters (width, height)
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
PRINTER_IP = "192.168.1.100"  # Replace with the actual IP of the 3D printer
PRINTER_PORT = 23  # Default Telnet port for G-code communication

# Output configuration
PCB_IMAGE_PATH = "./pcb_die.jpg"  # Path to the PCB image
OUTPUT_FILE = "scan_v1a_400MHz_Rx_pcb.json"  # Default output file name
