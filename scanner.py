import numpy as np
import json
import socket

# Constants

# The goal of this code is to implement a near-field scanner to visuialize EM field strenght at agiven frequency.
# A 3D printer is used to move the probe on th XY axis. The probe is used to measure the EM field strenght at each point.
# The printer using reprap duet 2 is controlled using G-code commands through ethernet.
# The software defined radio used for measurement is USRP B205.
# The data is then processed and visualized using python.
# the code is divided into 2 parts scanner.py to record the field and save a json the result and plot_field.py to visualize the field.


FREQUENCY = 400e6  # 400 MHz
WAVELENGTH = 3e8 / FREQUENCY  # Speed of light divided by frequency
GRID_SIZE = (100, 100)  # Size of the scanning grid

PRINTER_IP = "192.168.1.100"  # Replace with the actual IP of the 3D printer
PRINTER_PORT = 23  # Default Telnet port for G-code communication
OUTPUT_FILE = "scan_results.json"

SIMULATE_PRINTER = True  # Set to True to simulate the printer
SIMULATE_USRP = False     # Set to True to simulate the USRP

DEBUG_MESSAGE = True  # Set to True to enable debug messages

PCB_SIZE_CM = (3, 2)  # PCB size in centimeters (width, height)
RESOLUTION = 10  # Resolution in points per millimeter

# Convert PCB size to meters for calculations
PCB_SIZE = (PCB_SIZE_CM[0] / 100, PCB_SIZE_CM[1] / 100)

# Generate scanning grid based on PCB size and resolution
STEP_SIZE = 1 / (RESOLUTION * 10)  # Step size in meters (convert points/mm to points/m)
x_values = np.arange(0, PCB_SIZE[0], STEP_SIZE)
y_values = np.arange(0, PCB_SIZE[1], STEP_SIZE)

# Ensure the grid has at least two points in both dimensions
if len(x_values) < 2:
    x_values = np.array([0, PCB_SIZE[0]])
if len(y_values) < 2:
    y_values = np.array([0, PCB_SIZE[1]])

X, Y = np.meshgrid(x_values, y_values)

# Simulated EM field data (for demonstration purposes)
def simulate_em_field(x, y):
    """Simulate an EM field strength at a given point."""
    return np.sin(2 * np.pi * x / WAVELENGTH) * np.cos(2 * np.pi * y / WAVELENGTH)

def send_gcode_command(command, printer_socket):
    """Send a G-code command to the 3D printer."""
    printer_socket.sendall((command + "\n").encode())
    response = printer_socket.recv(1024).decode()
    return response

def measure_field_strength():
    """Simulate or interface with USRP B205 to measure field strength in dBm."""
    if SIMULATE_USRP:
        # Simulated measurement
        power_linear = np.random.random()  # Simulated linear power (0 to 1)
        power_dbm = 10 * np.log10(power_linear + 1e-12) + 30  # Convert to dBm
        if DEBUG_MESSAGE:
            print(f"Simulated power: {power_linear:.6f} linear, {power_dbm:.2f} dBm")
        return power_dbm
    else:
        # Actual USRP B205 measurement code
        try:
            import uhd  # UHD library for USRP
            print("Connecting to USRP device...")  # Indicate connection attempt
            usrp = uhd.usrp.MultiUSRP()  # Create a USRP object
            print("USRP device found and communicating.")  # Indicate successful communication
            
            # Configure USRP settings
            usrp.set_rx_freq(FREQUENCY)  # Set the frequency
            usrp.set_rx_gain(10)  # Set the gain
            
            # Receive samples and calculate power
            print("Receiving samples from USRP...")
            samples = usrp.recv_num_samps(1024, timeout=1.0)  # Receive samples
            power_linear = np.mean(np.abs(samples)**2)  # Calculate power in linear scale
            power_dbm = 10 * np.log10(power_linear + 1e-12) + 30  # Convert to dBm
            if DEBUG_MESSAGE:
                print(f"Measured power: {power_linear:.6f} linear, {power_dbm:.2f} dBm")
            return power_dbm
        except ImportError:
            print("UHD library is not installed. Falling back to simulated USRP.")
            return measure_field_strength()  # Fallback to simulation
        except Exception as e:
            raise RuntimeError(f"Error reading from USRP: {e}")

def scan_field():
    """Perform the scanning process and save results to a JSON file."""
    results = []
    if SIMULATE_PRINTER:
        print("Printer simulation mode enabled. No printer connection will be made.")
        for y in y_values:
            for x in x_values:
                # Simulate moving the probe to the (x, y) position
                print(f"Simulating move to X={x:.3f}, Y={y:.3f}")
                
                # Measure the field strength
                field_strength = measure_field_strength()
                results.append({"x": x, "y": y, "field_strength": field_strength})
    else:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as printer_socket:
            printer_socket.connect((PRINTER_IP, PRINTER_PORT))
            for y in y_values:
                for x in x_values:
                    # Move the probe to the (x, y) position
                    gcode_command = f"G1 X{x:.3f} Y{y:.3f}"
                    send_gcode_command(gcode_command, printer_socket)
                    
                    # Measure the field strength
                    field_strength = measure_field_strength()
                    results.append({"x": x, "y": y, "field_strength": field_strength})
    
    # Save results to a JSON file
    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=4)
    print(f"Scan results saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    scan_field()