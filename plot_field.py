# The goal of this code is to implement a near-field scanner to visuialize EM field strenght at agiven frequency.
# A 3D printer is used to move the probe on th XY axis. The probe is used to measure the EM field strenght at each point.
# The printer using reprap duet 2 is controlled using G-code commands through ethernet.
# The software defined radio used for measurement is USRP B205.
# The data is then processed and visualized using python.
# the code is divided into 2 parts scanner.py to record the field and save a json the result and plot_field.py to visualize the field.

import json
import numpy as np
import matplotlib.pyplot as plt

INPUT_FILE = "scan_results.json"

def plot_field():
    """Plot the EM field strength from the scan results."""
    # Load scan results
    with open(INPUT_FILE, "r") as f:
        results = json.load(f)

    # Extract x, y, and field_strength values
    x = np.array([point["x"] for point in results]) * 100  # Convert from meters to cm
    y = np.array([point["y"] for point in results]) * 100  # Convert from meters to cm
    field_strength = np.array([point["field_strength"] for point in results])

    # Reshape data for plotting
    unique_x = np.unique(x)
    unique_y = np.unique(y)
    X, Y = np.meshgrid(unique_x, unique_y)
    Z = field_strength.reshape(len(unique_y), len(unique_x))

    # Calculate PCB aspect ratio
    pcb_width = unique_x[-1] - unique_x[0]
    pcb_height = unique_y[-1] - unique_y[0]
    aspect_ratio = pcb_width / pcb_height

    # Plot the field strength
    plt.figure(figsize=(8 * aspect_ratio, 8))  # Adjust figure size based on aspect ratio
    plt.contourf(X, Y, Z, cmap="viridis")
    plt.colorbar(label="Field Strength (dBm)")
    plt.xlabel("X (cm)")
    plt.ylabel("Y (cm)")
    plt.title("EM Field Strength")

    # Ensure the aspect ratio matches the PCB's rectangular shape
    plt.gca().set_aspect('equal', adjustable='box')

    plt.show()

if __name__ == "__main__":
    plot_field()
