import numpy as np
import json
import socket
from measure_power import initialize_radio, receive_frame  # Import the updated functions
from plot_field import plot_field  # Import the plotting function

# PCB-related constants
PCB_SIZE_CM = (3, 2)  # PCB size in centimeters (width, height)
RESOLUTION = 10  # Resolution in points per millimeter
PCB_SIZE = (PCB_SIZE_CM[0] / 100, PCB_SIZE_CM[1] / 100)  # Convert PCB size to meters

# Generate scanning grid based on PCB size and resolution
STEP_SIZE = PCB_SIZE[0] / (RESOLUTION * PCB_SIZE_CM[0])  # Step size in meters (scaled to PCB width)
x_values = np.arange(0, PCB_SIZE[0] + STEP_SIZE, STEP_SIZE)
y_values = np.arange(0, PCB_SIZE[1] + STEP_SIZE, STEP_SIZE)

# Ensure the grid has at least two points in both dimensions
if len(x_values) < 2:
    x_values = np.array([0, PCB_SIZE[0]])
if len(y_values) < 2:
    y_values = np.array([0, PCB_SIZE[1]])

X, Y = np.meshgrid(x_values, y_values)

# Radio measurement configuration
CENTER_FREQUENCY = 400e6  # Center frequency in Hz (default: 400 MHz)
EQUIVALENT_BW = 50e6      # Equivalent bandwidth in Hz (default: 50 MHz)
RX_GAIN = 10              # Receiver gain in dB
WAVELENGTH = 3e8 / CENTER_FREQUENCY  # Speed of light divided by frequency
SIMULATE_USRP = False     # Set to True to simulate the USRP

# 3D printer configuration
PRINTER_IP = "192.168.1.100"  # Replace with the actual IP of the 3D printer
PRINTER_PORT = 23  # Default Telnet port for G-code communication
SIMULATE_PRINTER = True  # Set to True to simulate the printer
INIT_GCODE = "G28"  # Example initialization G-code command

# Output configuration
OUTPUT_FILE = "scan_results.json"
DEBUG_MESSAGE = True  # Set to True to enable debug messages

# Simulated EM field data (for demonstration purposes)
def simulate_em_field(x, y):
    """Simulate an EM field strength at a given point."""
    return np.sin(2 * np.pi * x / WAVELENGTH) * np.cos(2 * np.pi * y / WAVELENGTH)

def send_gcode_command(command, printer_socket):
    """Send a G-code command to the 3D printer."""
    printer_socket.sendall((command + "\n").encode())
    response = printer_socket.recv(1024).decode()
    return response

def measure_field_strength(usrp, streamer):
    """Interface with USRP B205 to measure field strength in dBm."""
    if SIMULATE_USRP:
        # Simulated measurement
        power_linear = np.random.random()  # Simulated linear power (0 to 1)
        power_dbm = 10 * np.log10(power_linear + 1e-12) + 30  # Convert to dBm
        input_power_dbm = power_dbm - RX_GAIN  # Subtract simulated receiver gain
        if DEBUG_MESSAGE:
            print(f"Simulated power: {power_linear:.6f} linear, {input_power_dbm:.2f} dBm (input)")
        return input_power_dbm
    else:
        # Use receive_frame function to get the power
        try:
            return receive_frame(streamer, RX_GAIN)
        except Exception as e:
            print(f"Error measuring field strength: {e}")
            return None

def scan_field():
    """Perform the scanning process and save results to a JSON file."""
    results = []

    # Initialize the radio once
    usrp, streamer = (None, None)
    if not SIMULATE_USRP:
        usrp, streamer = initialize_radio(CENTER_FREQUENCY, RX_GAIN, EQUIVALENT_BW)
        if not usrp or not streamer:
            print("Failed to initialize radio. Exiting scan.")
            return

    if SIMULATE_PRINTER:
        print("Printer simulation mode enabled. No printer connection will be made.")
        for y in y_values:
            for x in x_values:
                # Simulate moving the probe to the (x, y) position
                print(f"Simulating move to X={x:.3f}, Y={y:.3f}")
                
                # Measure the field strength
                field_strength = measure_field_strength(usrp, streamer)
                if field_strength is not None:
                    results.append({
                        "x": float(x),  # Convert numpy.float32 to float
                        "y": float(y),  # Convert numpy.float32 to float
                        "field_strength": float(field_strength)  # Convert numpy.float32 to float
                    })
    else:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as printer_socket:
            printer_socket.connect((PRINTER_IP, PRINTER_PORT))
            send_gcode_command(INIT_GCODE, printer_socket)  # Send initialization G-code
            for y in y_values:
                for x in x_values:
                    # Move the probe to the (x, y) position
                    gcode_command = f"G1 X{x:.3f} Y{y:.3f}"
                    send_gcode_command(gcode_command, printer_socket)
                    
                    # Measure the field strength
                    field_strength = measure_field_strength(usrp, streamer)
                    if field_strength is not None:
                        results.append({
                            "x": float(x),  # Convert numpy.float32 to float
                            "y": float(y),  # Convert numpy.float32 to float
                            "field_strength": float(field_strength)  # Convert numpy.float32 to float
                        })
    
    # Save results to a JSON file
    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=4)
    print(f"Scan results saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    scan_field()
    plot_field()  # Call the plotting function to visualize the results