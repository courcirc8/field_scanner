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
    """Load scanned data from a JSON file and visualize the EM field in dBm."""
    with open(INPUT_FILE, "r") as f:
        data = json.load(f)
    
    # Extract x, y, and field strength values
    x = np.array([point["x"] for point in data])
    y = np.array([point["y"] for point in data])
    field_strength = np.array([point["field_strength"] for point in data])
    
    # Determine grid dimensions
    grid_size_x = len(np.unique(x))
    grid_size_y = len(np.unique(y))
    
    # Ensure grid dimensions are valid for contour plotting
    if grid_size_x < 2 or grid_size_y < 2:
        raise ValueError("Grid dimensions must be at least 2x2 for contour plotting.")
    
    # Reshape data into 2D grids
    X = x.reshape(grid_size_y, grid_size_x)
    Y = y.reshape(grid_size_y, grid_size_x)
    Z = field_strength.reshape(grid_size_y, grid_size_x)
    
    # Plot the EM field
    plt.figure(figsize=(10, 8))
    plt.contourf(X, Y, Z, cmap='viridis')
    plt.colorbar(label='Field Strength (dBm)')
    plt.title('Measured EM Field in dBm')
    plt.xlabel('X Position (m)')
    plt.ylabel('Y Position (m)')
    plt.show()

if __name__ == "__main__":
    plot_field()
