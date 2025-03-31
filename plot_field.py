"""
Field Visualization Module

This script visualizes the EM field strength recorded by the field scanner. It reads 
the results from a JSON file, reshapes the data into a grid, and generates a contour 
plot with proper scaling and aspect ratio.

Implemented Features:
- Loading scan results from a JSON file.
- Reshaping data into a grid for plotting.
- Contour plot generation with a colorbar and proper aspect ratio.
- User prompt to close the plot after visualization.

Missing Features:
- Advanced visualization options (e.g., 3D plots or interactive plots).
- Support for exporting plots to image files (e.g., PNG, PDF).
- Error handling for invalid or missing input files.
"""

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

    # Show the plot and block until the window is closed
    plt.show(block=True)

    # Prompt the user to press Enter to exit the program
    input("Press Enter to exit the program.")

if __name__ == "__main__":
    plot_field()
