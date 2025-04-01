"""
Field Scanner Implementation

This script implements the core functionality of a near-field scanner to visualize 
the electromagnetic (EM) field strength at a given frequency. The scanner uses a 
3D printer to move a probe along the XY axis and a software-defined radio (USRP B205) 
to measure the EM field strength at each point. The results are saved to a JSON file 
and visualized using Python.

Implemented Features:
- PCB grid generation based on user-defined size and resolution.
- Communication with a 3D printer using G-code commands (simulated or real).
- USRP initialization and power measurement using the `measure_power` module.
- Interactive plot updates during the scanning process.
- Final plot generation with proper scaling and colorbar.

Missing Features:
- Integration with a real 3D printer for physical probe movement.
- Error handling for edge cases such as communication failures with the printer or USRP.
- Optimization for faster scanning and plotting.
- Advanced visualization options (e.g., 3D plots or heatmaps with interpolation).
"""

import numpy as np
import json
import socket
import matplotlib.pyplot as plt
from measure_power import initialize_radio, receive_frame  # Import the updated functions
from plot_field import plot_field  # Import the plotting function
from d3d_printer import PrinterConnection  # Import the PrinterConnection class

# PCB-related constants
PCB_SIZE_CM = (3, 2)  # PCB size in centimeters (width, height)
RESOLUTION = 50  # Resolution in points per centimeter
PCB_SIZE = (PCB_SIZE_CM[0], PCB_SIZE_CM[1])  # PCB size already in centimeters

# Generate scanning grid based on PCB size and resolution
STEP_SIZE = 1 / RESOLUTION  # Step size in centimeters
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
SIMULATE_PRINTER = False  # Set to True to simulate the printer
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

def initialize_plot():
    """Initialize the interactive plot."""
    plt.ion()  # Turn on interactive mode
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.set_xlabel("X (cm)")
    ax.set_ylabel("Y (cm)")
    ax.set_title("EM Field Strength (Interactive)")
    ax.set_aspect('equal', adjustable='box')

    # Create an empty 2D array for the initial contour plot
    empty_x = np.linspace(0, PCB_SIZE_CM[0], 2)  # Two points for x-axis
    empty_y = np.linspace(0, PCB_SIZE_CM[1], 2)  # Two points for y-axis
    empty_z = np.zeros((2, 2))  # 2x2 array of zeros for z-axis
    contour = ax.contourf(empty_x, empty_y, empty_z, cmap="viridis", levels=50)  # Initialize contour
    colorbar = plt.colorbar(contour, ax=ax, label="Field Strength (dBm)")
    return fig, ax, contour, colorbar

def update_plot(ax, contour, colorbar, results, x_values, y_values):
    """Update the plot with new data."""
    x = np.array([point["x"] for point in results]) * 100  # Convert from meters to cm
    y = np.array([point["y"] for point in results]) * 100  # Convert from meters to cm
    field_strength = np.array([point["field_strength"] for point in results])

    # Reshape data for plotting
    unique_x = np.unique(x_values * 100)  # Convert x_values to cm
    unique_y = np.unique(y_values * 100)  # Convert y_values to cm
    X, Y = np.meshgrid(unique_x, unique_y)
    Z = np.full(X.shape, np.nan)  # Initialize with NaN for missing points

    # Fill in the measured points
    for point in results:
        xi = np.where(unique_x == point["x"] * 100)[0][0]
        yi = np.where(unique_y == point["y"] * 100)[0][0]
        Z[yi, xi] = point["field_strength"]

    # Remove the old contour plot
    for artist in ax.collections:
        artist.remove()  # Remove the old contour plot

    # Create a new contour plot
    contour = ax.contourf(X, Y, Z, cmap="viridis", levels=50)

    # Update the colorbar without recreating it
    colorbar.update_normal(contour)  # Update the colorbar with the new contour

    # Update axis labels and title
    ax.set_xlabel("X (cm)")
    ax.set_ylabel("Y (cm)")
    ax.set_title("EM Field Strength (Interactive)")
    ax.set_aspect('equal', adjustable='box')
    plt.pause(0.1)  # Pause to update the plot

    return contour  # Return the updated contour object

def move_around_perimeter(printer, pcb_width, pcb_height):
    """
    Move the printer around the PCB perimeter to allow the user to adjust PCB placement.

    :param printer: PrinterConnection object.
    :param pcb_width: Width of the PCB in cm.
    :param pcb_height: Height of the PCB in cm.
    """
    print("Moving around the PCB perimeter for adjustment...")
    printer.move_probe(x=0, y=0, feedrate=800)  # Move to bottom-left corner
    printer.move_probe(x=pcb_width * 10, y=0, feedrate=800)  # Move to bottom-right corner
    printer.move_probe(x=pcb_width * 10, y=pcb_height * 10, feedrate=800)  # Move to top-right corner
    printer.move_probe(x=0, y=pcb_height * 10, feedrate=800)  # Move to top-left corner
    printer.move_probe(x=0, y=0, feedrate=800)  # Return to bottom-left corner

    # Display a graphical popup for user adjustment
    plt.figure(figsize=(6, 4))
    plt.text(0.5, 0.5, "Adjust PCB placement\nthen press the button to continue", 
             fontsize=14, ha='center', va='center')
    plt.axis('off')
    plt.show(block=False)

    # Wait for user confirmation via a graphical button
    input("Press Enter to continue after adjustment...")
    plt.close()

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

    # Initialize the 3D printer connection
    printer = PrinterConnection(PRINTER_IP, PRINTER_PORT)
    printer.connect()

    # Terminate if the printer connection fails
    if not printer.socket:
        print("Failed to connect to the 3D printer. Exiting scan.")
        return



    # Initialize the interactive plot
    fig, ax, contour, colorbar = initialize_plot()

    if SIMULATE_PRINTER:
        print("Printer simulation mode enabled. No printer connection will be made.")
        for i, (y, x) in enumerate(np.ndindex(len(y_values), len(x_values))):
            # Simulate moving the probe to the (x, y) position
            print(f"Simulating move to X={x_values[x]:.3f}, Y={y_values[y]:.3f}")
            
            # Measure the field strength
            field_strength = measure_field_strength(usrp, streamer)
            if field_strength is not None:
                results.append({
                    "x": float(x_values[x]),
                    "y": float(y_values[y]),
                    "field_strength": float(field_strength)
                })

            # Update the plot every 10 measurements
            if (i + 1) % 10 == 0:
                contour = update_plot(ax, contour, colorbar, results, x_values, y_values)
    else:
        try:
            # Initialize the printer (home axes and calibrate Z-axis)
            printer.initialize_printer()

            # Move around the PCB perimeter for adjustment
            move_around_perimeter(printer, PCB_SIZE_CM[0], PCB_SIZE_CM[1])

            for i, (y, x) in enumerate(np.ndindex(len(y_values), len(x_values))):
                # Move the probe to the (x, y) position
                print(f"Moving probe to X={x_values[x]:.3f}, Y={y_values[y]:.3f}")
                printer.move_probe(x=x_values[x] * 10, y=y_values[y] * 10)  # Convert to mm

                # Measure the field strength
                field_strength = measure_field_strength(usrp, streamer)
                if field_strength is not None:
                    results.append({
                        "x": float(x_values[x]),
                        "y": float(y_values[y]),
                        "field_strength": float(field_strength)
                    })

                # Update the plot every 10 measurements
                if (i + 1) % 10 == 0:
                    contour = update_plot(ax, contour, colorbar, results, x_values, y_values)
        finally:
            # Ensure the printer is disconnected properly
            printer.disconnect()
    
    # Save results to a JSON file
    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=4)
    print(f"Scan results saved to {OUTPUT_FILE}")

    # Redraw the plot completely at the end of measurements
    plt.close(fig)  # Close the interactive plot
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.set_xlabel("X (cm)")
    ax.set_ylabel("Y (cm)")
    ax.set_title("EM Field Strength (Final)")
    ax.set_aspect('equal', adjustable='box')

    # Extract x, y, and field_strength values for final plot
    x = np.array([point["x"] for point in results]) * 100
    y = np.array([point["y"] for point in results]) * 100
    field_strength = np.array([point["field_strength"] for point in results])

    # Reshape data for plotting
    unique_x = np.unique(x_values * 100)
    unique_y = np.unique(y_values * 100)
    X, Y = np.meshgrid(unique_x, unique_y)
    Z = np.full(X.shape, np.nan)

    for point in results:
        xi = np.where(unique_x == point["x"] * 100)[0][0]
        yi = np.where(unique_y == point["y"] * 100)[0][0]
        Z[yi, xi] = point["field_strength"]

    # Create the final contour plot
    contour = ax.contourf(X, Y, Z, cmap="viridis", levels=50)
    plt.colorbar(contour, ax=ax, label="Field Strength (dBm)")

    # Show the final plot and wait for the user to close it
    plt.show(block=True)

    # Prompt the user to press Enter to exit the program
    input("Press Enter to exit the program.")

if __name__ == "__main__":
    scan_field()