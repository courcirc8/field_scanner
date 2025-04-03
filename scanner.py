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
import tkinter as tk
from tkinter import simpledialog

# PCB-related constants
PCB_SIZE_CM = (2.165, 1.53)  # PCB size in centimeters (width, height)
#PCB_SIZE_CM = (1.4, 1.4)  # PCB size in centimeters (width, height)

RESOLUTION = 30  # Resolution in points per centimeter
PCB_SIZE = (PCB_SIZE_CM[0], PCB_SIZE_CM[1])  # PCB size already in centimeters
max_height_x_pos = 0.444  # X position of the highest component in cm
max_height_y_pos = 0.37  # Y position of the highest component in cm

# Z-height-related constants
INITIAL_Z_HEIGHT = 97.3  # Initial probing height in mm (3.4 cm)
Z_LIFT = 1  # Lift height in mm for safe movements

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
RX_GAIN = 76              # Receiver gain in dB 76dB in Rx 20 or 30 in Tx
WAVELENGTH = 3e8 / CENTER_FREQUENCY  # Speed of light divided by frequency
SIMULATE_USRP = False     # Set to True to simulate the USRP
nb_avera = 100 # Number of measurements to average

# 3D printer configuration
PRINTER_IP = "192.168.1.100"  # Replace with the actual IP of the 3D printer
PRINTER_PORT = 23  # Default Telnet port for G-code communication
SIMULATE_PRINTER = False  # Set to True to simulate the printer

# Output configuration
OUTPUT_FILE = "scan_v1a_400MHz_Rx.json"
DEBUG_MESSAGE = True  # Set to True to enable debug messages
PCB_IMAGE_PATH = "./pcb_die.jpg"  # Path to the PCB image

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
    contour = ax.contourf(empty_x, empty_y, empty_z, cmap="viridis", levels=50, alpha=0.35)  # Set alpha to 0.35
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
    contour = ax.contourf(X, Y, Z, cmap="viridis", levels=50, alpha=0.35)  # Set alpha to 0.35

    # Update the colorbar without recreating it
    colorbar.update_normal(contour)  # Update the colorbar with the new contour

    # Update axis labels and title
    ax.set_xlabel("X (cm)")  # Ensure the label reflects centimeters
    ax.set_ylabel("Y (cm)")  # Ensure the label reflects centimeters
    ax.set_title("EM Field Strength (Interactive)")
    ax.set_aspect('equal', adjustable='box')
    plt.pause(0.1)  # Pause to update the plot

    return contour  # Return the updated contour object

def save_scan_results(filename, results, metadata=None):
    """
    Save scan results to a JSON file with optional metadata.

    Args:
        filename (str): The name of the file to save the results.
        results (list): The scan results as a list of dictionaries.
        metadata (dict): Optional metadata to include in the file.
    """
    data = {
        "metadata": metadata or {},  # Include metadata if provided
        "results": results  # Include scan results
    }
    try:
        with open(filename, "w") as f:
            json.dump(data, f, indent=4)
        print(f"Scan results saved to {filename}")
    except Exception as e:
        print(f"Error saving scan results to {filename}: {e}")

def adjust_head(printer, usrp, streamer):
    """
    Adjust the printer head position (X, Y, Z) and allow the user to set the offsets for probing.
    Includes real-time radio power measurement and display.

    :param printer: PrinterConnection object.
    :param usrp: USRP object for power measurement.
    :param streamer: Streamer object for power measurement.
    :return: Final X, Y, Z offsets to be used for probing.
    """
    import tkinter as tk
    import threading
    import time

    # Ensure the printer is in absolute positioning mode
    printer.send_gcode("G90")  # Set absolute positioning

    # Initialize the offsets
    x_offset = 0.0  # X-axis offset in mm
    y_offset = 0.0  # Y-axis offset in mm
    z_height = INITIAL_Z_HEIGHT  # Start at the initial probing height
    z_lift = Z_LIFT  # Use the defined lift height
    pcb_corners = {
        "Upper Left": (0, PCB_SIZE_CM[1] * 10),
        "Upper Right": (PCB_SIZE_CM[0] * 10, PCB_SIZE_CM[1] * 10),
        "Bottom Left": (0, 0),
        "Bottom Right": (PCB_SIZE_CM[0] * 10, 0),
    }

    def move_to_corner(corner):
        """Move the probe to a specified corner."""
        x, y = pcb_corners[corner]
        # Lift the probe to a safe height before moving in X-Y
        printer.move_probe(x=0, y=0, z=z_height + z_lift, feedrate=3000)  # Lift Z first
        printer.move_probe(x=x + x_offset, y=y + y_offset, z=z_height + z_lift, feedrate=3000)  # Travel to the corner
        printer.move_probe(x=x + x_offset, y=y + y_offset, z=z_height - z_lift, feedrate=3000)  # Lower Z to probing height

    def move_to_max_height():
        """Move the probe to the highest component position."""
        x = max_height_x_pos * 10  # Convert to mm
        y = max_height_y_pos * 10  # Convert to mm
        # Lift the probe to a safe height before moving in X-Y
        printer.move_probe(x=0, y=0, z=z_height + z_lift, feedrate=3000)  # Lift Z first
        printer.move_probe(x=x + x_offset, y=y + y_offset, z=z_height + z_lift, feedrate=3000)  # Travel to the max height position
        printer.move_probe(x=x + x_offset, y=y + y_offset, z=z_height, feedrate=3000)  # Land at max Z

    def measure_power():
        """Measure the radio power and update the label in a thread-safe way."""
        while not done:
            if SIMULATE_USRP:
                power = np.random.uniform(-70, -50)  # Simulated power in dBm
            else:
                try:
                    power = get_power_dBm(usrp, streamer, RX_GAIN, nb_avera, CENTER_FREQUENCY, EQUIVALENT_BW)
                except Exception as e:
                    print(f"Error measuring field strength: {e}")
                    power = None

            if not done:
                if power is not None:
                    root.after(0, lambda: power_label.config(text=f"Power: {power:.2f} dBm"))  # Thread-safe update
                else:
                    root.after(0, lambda: power_label.config(text="Power: Measurement Failed"))  # Handle None case
            time.sleep(1)  # Update every second

    def done_callback():
        """Return to the correct Z height and exit."""
        nonlocal done
        done = True  # Stop the measure_power thread
        printer.send_gcode(f"G1 Z{z_height:.3f} F3000")  # Return to the correct Z height
        root.quit()  # Safely exit the main loop

    def adjust_z(delta):
        """Adjust the Z height by a specified delta without moving X or Y."""
        nonlocal z_height
        z_height += delta
        printer.send_gcode(f"G1 Z{z_height:.3f} F3000")  # Only adjust Z
        z_label.config(text=f"Defined Z: {z_height:.2f} mm")  # Update the Z reference display

    def adjust_x(delta):
        """Adjust the X offset."""
        nonlocal x_offset
        x_offset += delta
        printer.send_gcode(f"G1 X{x_offset:.3f} F3000")  # Move X axis
        x_label.config(text=f"X Offset: {x_offset:.2f} mm")  # Update the X offset display

    def adjust_y(delta):
        """Adjust the Y offset."""
        nonlocal y_offset
        y_offset += delta
        printer.send_gcode(f"G1 Y{y_offset:.3f} F3000")  # Move Y axis
        y_label.config(text=f"Y Offset: {y_offset:.2f} mm")  # Update the Y offset display

    # Create the Tkinter window
    root = tk.Tk()
    root.title("Adjust Head Position")
    root.geometry("600x500")  # Increased height to accommodate all elements

    # Add corner buttons
    tk.Button(root, text="Upper Left", command=lambda: move_to_corner("Upper Left")).place(x=50, y=50)
    tk.Button(root, text="Upper Right", command=lambda: move_to_corner("Upper Right")).place(x=250, y=50)
    tk.Button(root, text="Bottom Left", command=lambda: move_to_corner("Bottom Left")).place(x=50, y=250)
    tk.Button(root, text="Bottom Right", command=lambda: move_to_corner("Bottom Right")).place(x=250, y=250)

    # Add "Max Height" button
    tk.Button(root, text="Max Height", command=move_to_max_height).place(x=150, y=150)

    # Add Z adjustment buttons on the right
    tk.Button(root, text="+1 cm", command=lambda: adjust_z(10)).place(x=500, y=100)
    tk.Button(root, text="+1 mm", command=lambda: adjust_z(1)).place(x=500, y=150)
    tk.Button(root, text="+0.1 mm", command=lambda: adjust_z(0.1)).place(x=500, y=200)
    tk.Button(root, text="-0.1 mm", command=lambda: adjust_z(-0.1)).place(x=500, y=250)
    tk.Button(root, text="-1 mm", command=lambda: adjust_z(-1)).place(x=500, y=300)
    tk.Button(root, text="-1 cm", command=lambda: adjust_z(-10)).place(x=500, y=350)

    # Add X-Y adjustment buttons in a cross layout
    tk.Button(root, text="+Y", command=lambda: adjust_y(0.1)).place(x=400, y=150)  # Above
    tk.Button(root, text="-Y", command=lambda: adjust_y(-0.1)).place(x=400, y=250)  # Below
    tk.Button(root, text="+X", command=lambda: adjust_x(0.1)).place(x=450, y=200)  # Right
    tk.Button(root, text="-X", command=lambda: adjust_x(-0.1)).place(x=350, y=200)  # Left

    # Add a "Done" button
    tk.Button(root, text="Done", command=done_callback).place(x=250, y=450)  # Moved down to avoid overlap

    # Add a label to display the measured power
    power_label = tk.Label(root, text="Power: -- dBm", font=("Helvetica", 14))
    power_label.place(x=100, y=400)  # Moved down to avoid overlap with the "Done" button

    # Add labels to display the defined offsets
    z_label = tk.Label(root, text=f"Defined Z: {z_height:.2f} mm", font=("Helvetica", 14))
    z_label.place(x=100, y=20)
    x_label = tk.Label(root, text=f"X Offset: {x_offset:.2f} mm", font=("Helvetica", 14))
    x_label.place(x=400, y=20)
    y_label = tk.Label(root, text=f"Y Offset: {y_offset:.2f} mm", font=("Helvetica", 14))
    y_label.place(x=400, y=60)

    # Start a thread for real-time power updates
    done = False
    threading.Thread(target=measure_power, daemon=True).start()

    # Run the Tkinter event loop
    root.mainloop()

    # Return the final offsets
    return x_offset, y_offset, z_height

def scan_field(file_name):
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

        # Adjust head position and get the final offsets
        x_offset, y_offset, z_height = adjust_head(printer, usrp, streamer)

        # Add a delay after the adjustment to ensure the printer is ready
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
                printer.move_probe(x=(x * 10) + x_offset, y=(y * 10) + y_offset, z=z_height)  # Convert to mm

                # Measure the field strength using the averaged get_power_dBm with specified averages
                try:
                    field_strength = get_power_dBm(usrp, streamer, RX_GAIN, nb_avera, CENTER_FREQUENCY, EQUIVALENT_BW)
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

            # Debug message to confirm the first line of measurements is saved
            if y_idx == 0:
                print(f"First line of measurements saved: {results[:len(x_values)]}")

            # Update the plot after completing each X line
            contour = update_plot(ax, contour, colorbar, results, x_values, y_values)

    except KeyboardInterrupt:
        print("\nScan interrupted by user. Cleaning up...")
    finally:
        # Ensure the printer is disconnected properly
        printer.disconnect()

        # Save results to a JSON file if any data was collected
        if results:
            metadata = {
                "PCB_SIZE": PCB_SIZE_CM,
                "resolution": RESOLUTION,
                "center_freq": CENTER_FREQUENCY,  # Stored in Hz
                "BW": EQUIVALENT_BW,  # Stored in Hz
                "nb_average": nb_avera
            }

            # Display metadata in MHz
            print("Metadata for the scan:")
            print(f"  PCB Size: {metadata['PCB_SIZE']}")
            print(f"  Resolution: {metadata['resolution']}")
            print(f"  Center Frequency: {metadata['center_freq'] / 1e6:.2f} MHz")
            print(f"  Bandwidth: {metadata['BW'] / 1e6:.2f} MHz")
            print(f"  Number of Averages: {metadata['nb_average']}")

            save_scan_results(file_name, results, metadata)

            # Save the plot as an image file
            plot_image_path = file_name.replace(".json", ".png")
            print(f"Calling plot_field with file: {file_name}")
            plot_field(file_name, save_path=plot_image_path)  # Save the plot with alpha=0.35
            print(f"Plot saved as: {plot_image_path}")
        else:
            print("No results to save.")

        # Debug message before calling plot_field
        print(f"Calling plot_field with file: {file_name}")
        plot_field(file_name)  # plot_field will handle the conversion to MHz
        print("plot_field execution completed.")

def get_user_choice():
    """Display a popup window to choose between displaying a previous scan or making a new scan."""
    def on_display_previous():
        """Handle the 'Display Previous' button click."""
        nonlocal choice, file_name
        choice = "display"
        file_name = entry.get()
        root.destroy()

    def on_scan_new():
        """Handle the 'Scan New' button click."""
        nonlocal choice, file_name
        choice = "scan"
        file_name = entry.get()
        root.destroy()

    # Create the main popup window
    root = tk.Tk()
    root.title("Field Scanner")
    root.geometry("400x200")
    root.resizable(False, False)

    # Add a label for instructions
    label = tk.Label(root, text="Enter the file name for the scan results:", font=("Helvetica", 12))
    label.pack(pady=10)

    # Add a text entry for the file name (pre-filled with OUTPUT_FILE)
    entry = tk.Entry(root, font=("Helvetica", 12), width=40)
    entry.insert(0, OUTPUT_FILE)  # Pre-fill with the default OUTPUT_FILE value
    entry.pack(pady=5)

    # Add a frame for the buttons
    button_frame = tk.Frame(root)
    button_frame.pack(pady=20)

    # Add "Display Previous" and "Scan New" buttons
    display_button = tk.Button(button_frame, text="Display Previous", font=("Helvetica", 12), command=on_display_previous)
    display_button.pack(side="left", padx=10)

    scan_button = tk.Button(button_frame, text="Scan New", font=("Helvetica", 12), command=on_scan_new)
    scan_button.pack(side="left", padx=10)

    # Initialize variables to store the user's choice and file name
    choice = None
    file_name = None

    # Run the Tkinter event loop
    root.mainloop()

    return choice, file_name

if __name__ == "__main__":
    # Get user choice and file name
    choice, file_name = get_user_choice()

    if choice == "display":
        print(f"Displaying previous scan from file: {file_name}")
        print(f"Debug: Passing file path to plot_field: {file_name}")  # Debug message
        plot_field(file_name)  # Removed alpha argument
    elif choice == "scan":
        print(f"Starting a new scan. Results will be saved to: {file_name}")
        scan_field(file_name)  # Pass the user-provided file name to scan_field
    else:
        print("No valid choice made. Exiting.")