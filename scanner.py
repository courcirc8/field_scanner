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
from measure_power import initialize_radio, receive_frame, get_power_dBm  # Import the updated functions
from plot_field import plot_field  # Import the plotting function
from d3d_printer import PrinterConnection  # Import the PrinterConnection class
import time

# PCB-related constants
PCB_SIZE_CM = (2.05, 1.4)  # PCB size in centimeters (width, height)
#PCB_SIZE_CM = (1.4, 1.4)  # PCB size in centimeters (width, height)

RESOLUTION = 30  # Resolution in points per centimeter
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
EQUIVALENT_BW = 10e6      # Equivalent bandwidth in Hz (default: 50 MHz)
RX_GAIN = 76              # Receiver gain in dB
WAVELENGTH = 3e8 / CENTER_FREQUENCY  # Speed of light divided by frequency
SIMULATE_USRP = False     # Set to True to simulate the USRP
nb_avera = 100 # Number of measurements to average

# 3D printer configuration
PRINTER_IP = "192.168.1.100"  # Replace with the actual IP of the 3D printer
PRINTER_PORT = 23  # Default Telnet port for G-code communication
SIMULATE_PRINTER = False  # Set to True to simulate the printer

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
        # Use get_power_dBm function to get the average power
        try:
            return get_power_dBm(streamer, RX_GAIN)
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
    # Extract x, y, and field_strength values
    x = np.array([point["x"] for point in results]) * 100  # Convert from meters to cm
    y = np.array([point["y"] for point in results]) * 100  # Convert from meters to cm
    field_strength = np.array([point["field_strength"] for point in results])

    # Ensure unique_x and unique_y are consistent with the grid
    unique_x = np.unique(x_values * 100)  # Convert x_values to cm
    unique_y = np.unique(y_values * 100)  # Convert y_values to cm
    X, Y = np.meshgrid(unique_x, unique_y)
    Z = np.full(X.shape, np.nan)  # Initialize with NaN for missing points

    # Fill in the measured points
    for point in results:
        xi = np.where(unique_x == point["x"] * 100)[0]
        yi = np.where(unique_y == point["y"] * 100)[0]
        if xi.size > 0 and yi.size > 0:  # Ensure indices are valid
            Z[yi[0], xi[0]] = point["field_strength"]

    # Remove the old contour plot
    for artist in ax.collections:
        artist.remove()  # Remove the old contour plot

    # Create a new contour plot
    contour = ax.contourf(X, Y, Z, cmap="viridis", levels=50)

    # Update the colorbar without recreating it
    colorbar.update_normal(contour)  # Update the colorbar with the new contour

    # Update axis labels and title
    ax.set_xlabel("X (cm)")  # Ensure the label reflects centimeters
    ax.set_ylabel("Y (cm)")  # Ensure the label reflects centimeters
    ax.set_title("EM Field Strength (Interactive)")
    ax.set_aspect('equal', adjustable='box')
    plt.pause(0.1)  # Pause to update the plot

    return contour  # Return the updated contour object

def move_around_perimeter(printer, pcb_width, pcb_height, z_height):
    """
    Move the printer around the PCB perimeter to allow the user to adjust PCB placement.

    :param printer: PrinterConnection object.
    :param pcb_width: Width of the PCB in cm.
    :param pcb_height: Height of the PCB in cm.
    :param z_height: Adjusted Z height to use for movements.
    """
    import tkinter as tk
    import queue

    # Ensure the printer is in absolute positioning mode
    printer.send_gcode("G90")  # Set absolute positioning

    def stop_movement():
        nonlocal done
        done = True
        root.quit()  # Safely exit the main loop

    # Create the Tkinter window
    root = tk.Tk()
    root.title("Adjust PCB Placement")
    root.geometry("200x100")
    tk.Button(root, text="Done", command=stop_movement).pack(pady=20)

    done = False
    command_queue = queue.Queue()

    def cycle_perimeter():
        while not done:
            command_queue.put((0, 0))  # Bottom-left corner
            command_queue.put((pcb_width * 10, 0))  # Bottom-right corner
            command_queue.put((pcb_width * 10, pcb_height * 10))  # Top-right corner
            command_queue.put((0, pcb_height * 10))  # Top-left corner
            command_queue.put((0, 0))  # Return to bottom-left corner

    def process_commands():
        if not command_queue.empty():
            x, y = command_queue.get()
            printer.move_probe(x=x, y=y, z=z_height, feedrate=800)
        if not done:
            root.after(100, process_commands)  # Schedule the next command processing

    # Start the perimeter cycling in a separate thread
    import threading
    threading.Thread(target=cycle_perimeter, daemon=True).start()

    # Start processing commands on the main thread
    process_commands()

    # Run the Tkinter event loop on the main thread
    root.mainloop()

    # Ensure the printer returns to the starting position after the "Done" button is pressed
    print("Returning to starting position...")
    printer.move_probe(x=0, y=0, z=z_height, feedrate=800)

def adjust_pcb_height(printer, usrp, streamer):
    """
    Adjust the PCB height and allow the user to set the Z position for probing.
    Includes real-time radio power measurement and display.

    :param printer: PrinterConnection object.
    :param usrp: USRP object for power measurement.
    :param streamer: Streamer object for power measurement.
    :return: Final Z height to be used for probing.
    """
    import tkinter as tk
    import queue
    import threading
    import time

    # Ensure the printer is in absolute positioning mode
    printer.send_gcode("G90")  # Set absolute positioning

    # Move the printer head up by 3 cm at feedrate 3000
    printer.move_probe(x=0, y=0, z=34, feedrate=3000)  # This ensures Z is set initially

    # Initialize the Z height
    z_height = 34  # Start at 3 cm
    power_queue = queue.Queue()

    # Create a popup window for user adjustment
    def measure_power():
        """Measure the radio power and update the queue."""
        while not done:
            if SIMULATE_USRP:
                power = np.random.uniform(-70, -50)  # Simulated power in dBm
            else:
                power = measure_field_strength(usrp, streamer)
            power_queue.put(power)
            time.sleep(1)  # Update every second

    def update_power_label():
        """Update the power label from the queue."""
        if not power_queue.empty():
            power = power_queue.get()
            power_label.config(text=f"Power: {power:.2f} dBm")
        if not done:
            root.after(100, update_power_label)  # Schedule the next update

    def move_up_1cm():
        nonlocal z_height
        z_height += 10
        printer.move_probe(x=0, y=0, z=z_height, feedrate=3000)

    def move_up_1mm():
        nonlocal z_height
        z_height += 1
        printer.move_probe(x=0, y=0, z=z_height, feedrate=3000)

    def move_down_1mm():
        nonlocal z_height
        z_height -= 1
        printer.move_probe(x=0, y=0, z=z_height, feedrate=3000)

    def move_down_1cm():
        nonlocal z_height
        z_height -= 10
        printer.move_probe(x=0, y=0, z=z_height, feedrate=3000)

    def move_up_0_1mm():
        nonlocal z_height
        z_height += 0.1
        printer.move_probe(x=0, y=0, z=z_height, feedrate=3000)

    def move_down_0_1mm():
        nonlocal z_height
        z_height -= 0.1
        printer.move_probe(x=0, y=0, z=z_height, feedrate=3000)

    def done_callback():
        nonlocal done
        done = True
        root.quit()  # Safely exit the main loop

    root = tk.Tk()
    root.title("Adjust PCB Height")
    root.geometry("300x500")

    # Add buttons for adjustment
    tk.Button(root, text="Move up by 1 cm", command=move_up_1cm).pack(pady=10)
    tk.Button(root, text="Move up by 1 mm", command=move_up_1mm).pack(pady=10)
    tk.Button(root, text="Move up by 0.1 mm", command=move_up_0_1mm).pack(pady=10)
    tk.Button(root, text="Move down by 0.1 mm", command=move_down_0_1mm).pack(pady=10)
    tk.Button(root, text="Move down by 1 mm", command=move_down_1mm).pack(pady=10)
    tk.Button(root, text="Move down by 1 cm", command=move_down_1cm).pack(pady=10)
    tk.Button(root, text="Done", command=done_callback).pack(pady=10)

    # Add a label to display the measured power
    power_label = tk.Label(root, text="Power: -- dBm", font=("Helvetica", 14))
    power_label.pack(pady=20)

    # Start a thread for real-time power updates
    done = False
    threading.Thread(target=measure_power, daemon=True).start()

    # Start updating the power label on the main thread
    update_power_label()

    # Run the Tkinter event loop
    root.mainloop()

    # Return the final Z height
    return z_height

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
        print("Failed to connect to the 3D printer. Possible authentication issue. Exiting scan.")
        return

    try:
        # Initialize the printer (home axes and calibrate Z-axis)
        printer.initialize_printer()

        # Adjust PCB height and get the final Z height
        z_height = adjust_pcb_height(printer, usrp, streamer)

        # Move around the PCB perimeter for adjustment using the adjusted Z height
        move_around_perimeter(printer, PCB_SIZE_CM[0], PCB_SIZE_CM[1], z_height)

        # Add a delay after the perimeter movement to ensure the printer is ready
        # time.sleep(2)  # Adjust the delay as needed

        # Initialize the interactive plot
        fig, ax, contour, colorbar = initialize_plot()

        # Main scanning loop
        for y_idx, y in enumerate(y_values):
            # Add a delay at the beginning of each new line
            # time.sleep(0.5)

            for x_idx, x in enumerate(x_values):
                # Move the probe to the (x, y) position using the adjusted Z height
                print(f"Moving probe to X={x:.3f}, Y={y:.3f}, Z={z_height:.3f}")
                printer.move_probe(x=x * 10, y=y * 10, z=z_height)  # Convert to mm

                # Measure the field strength using the averaged get_power_dBm with specified averages
                try:
                    field_strength = get_power_dBm(streamer, RX_GAIN, nb_avera)
                except Exception as e:
                    print(f"Error measuring field strength: {e}")
                    field_strength = None

                if field_strength is not None:
                    results.append({
                        "x": float(x),
                        "y": float(y),
                        "field_strength": float(field_strength)
                    })
                else:
                    print(f"Warning: No field strength measured at X={x:.3f}, Y={y:.3f}")

            # Update the plot after completing each X line
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