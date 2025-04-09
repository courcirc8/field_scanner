# This module provides visualization tools for electromagnetic field measurements.
# It includes functions for:
# 1. Creating interactive plots for real-time scanning
# 2. Updating plots during scanning process
# 3. Displaying results with selectable scan orientations (0° and 90°)
#
# A major challenge addressed in this module is the visualization of different field
# orientations (0° and 90°) and allowing the user to switch between them while
# maintaining a consistent color scale and transparent PCB overlay.

import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.colorbar import Colorbar  # Import for colorbar detection
from plot_field import plot_field
import tkinter as tk
import os
import json
import numpy as np
from file_utils import combine_scans
from scipy.interpolate import griddata
from PIL import Image

def initialize_plot():
    """
    Initialize the interactive plot for real-time scanning visualization.
    Creates a figure, axis, contour plot, and colorbar for displaying field strength.
    Used during the scanning process to provide immediate feedback.
    """
    plt.ion()  # Turn on interactive mode
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.set_xlabel("X (cm)")
    ax.set_ylabel("Y (cm)")
    ax.set_title("EM Field Strength (Interactive)")
    ax.set_aspect('equal', adjustable='box')

    # Create an empty 2D array for the initial contour plot
    empty_x = [0, 1]  # Two points for x-axis
    empty_y = [0, 1]  # Two points for y-axis
    empty_z = [[0, 0], [0, 0]]  # 2x2 array of zeros for z-axis
    contour = ax.contourf(empty_x, empty_y, empty_z, cmap="viridis", levels=50, alpha=0.35)
    colorbar = plt.colorbar(contour, ax=ax, label="Field Strength (dBm)")
    return fig, ax, contour, colorbar

def update_plot(ax, contour, colorbar, results, x_values, y_values):
    """
    Update the plot with new data during the scanning process.
    This function is called after each row is scanned to provide real-time visualization.
    
    Args:
        ax: The matplotlib axis to plot on
        contour: The existing contour plot to update
        colorbar: The colorbar to update
        results: List of measurement points with field strengths
        x_values: List of x coordinate values
        y_values: List of y coordinate values
        
    Returns:
        Updated contour plot object
    """
    x = [point["x"] for point in results]
    y = [point["y"] for point in results]
    field_strength = [point["field_strength"] for point in results]

    unique_x = sorted(set(x_values))
    unique_y = sorted(set(y_values))
    X, Y = plt.meshgrid(unique_x, unique_y)
    Z = [[None for _ in unique_x] for _ in unique_y]

    for point in results:
        xi = unique_x.index(point["x"])
        yi = unique_y.index(point["y"])
        Z[yi][xi] = point["field_strength"]

    for artist in ax.collections:
        artist.remove()

    contour = ax.contourf(X, Y, Z, cmap="viridis", levels=50, alpha=0.35)
    colorbar.update_normal(contour)
    ax.set_xlabel("X (cm)")
    ax.set_ylabel("Y (cm)")
    ax.set_title("EM Field Strength (Interactive)")
    ax.set_aspect('equal', adjustable='box')
    plt.pause(0.1)

    return contour

def plot_with_selector(file_0d, file_90d):
    """
    Plot results with angle selector for switching between 0°, 90°, and combined views.
    
    This function creates an integrated UI with:
    - A control panel on the left for selecting scan orientation
    - An interactive visualization on the right showing field strength
    - A transparency slider to adjust PCB overlay visibility
    
    The implementation takes special care to:
    1. Use a consistent color scale across all views
    2. Maintain a single colorbar to avoid duplication
    3. Allow real-time adjustment of transparency
    4. Properly clean up resources when switching views
    
    Args:
        file_0d: Path to the 0° scan results file
        file_90d: Path to the 90° scan results file
    """
    # Load data files
    with open(file_0d, 'r') as f:
        data_0d = json.load(f)
    with open(file_90d, 'r') as f:
        data_90d = json.load(f)
    
    # Create combined data
    combined_file = file_0d.replace('_0d.json', '_combined.json')
    if not os.path.exists(combined_file):
        data_combined = combine_scans(file_0d, file_90d)
        with open(combined_file, 'w') as f:
            json.dump(data_combined, f)
    else:
        with open(combined_file, 'r') as f:
            data_combined = json.load(f)
    
    # Create the main Tkinter window
    root = tk.Tk()
    root.title("Field Scanner Visualization")
    root.geometry("1200x800")
    
    # Create frames
    button_frame = tk.Frame(root, width=200, padx=10, pady=10)
    button_frame.pack(side=tk.LEFT, fill=tk.Y)
    
    plot_frame = tk.Frame(root)
    plot_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
    
    # Get global min/max for consistent colormap
    all_field_strengths = []
    for dataset in [data_0d, data_90d, data_combined]:
        all_field_strengths.extend([point["field_strength"] for point in dataset["results"]])
    vmin = min(all_field_strengths)
    vmax = max(all_field_strengths)
    
    # Create figure and canvas
    fig, ax = plt.subplots(figsize=(10, 8))
    canvas = FigureCanvasTkAgg(fig, master=plot_frame)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    # Add toolbar
    toolbar_frame = tk.Frame(plot_frame)
    toolbar_frame.pack(side=tk.BOTTOM, fill=tk.X)
    toolbar = NavigationToolbar2Tk(canvas, toolbar_frame)
    toolbar.update()
    
    # Create a dummy transparent image for initial colorbar
    dummy_data = np.zeros((10, 10))
    dummy_img = ax.imshow(dummy_data, cmap='plasma', visible=False, vmin=vmin, vmax=vmax)
    
    # Create a persistent colorbar that won't be destroyed or recreated
    persistent_colorbar = fig.colorbar(dummy_img, ax=ax, label="Field Strength (dBm)")
    
    # Initialize plot objects dictionary to store image references
    plot_objects = {
        "pcb_overlay": None,
        "heatmap": None
    }
    
    # Current state variables
    current_file = tk.StringVar(value=combined_file)  # Start with combined plot
    current_title = tk.StringVar(value="Combined Scan")
    alpha_value = tk.DoubleVar(value=0.5)  # Default transparency value
    
    def update_plot():
        """Update the plot with the selected scan data."""
        try:
            # Clear the existing plot content but keep the figure
            ax.clear()
            
            # Load and plot the new data
            file_path = current_file.get()
            print(f"Plotting file: {file_path}")
            
            # Directly draw the PCB and heatmap on our existing axis
            pcb_img = Image.open("./pcb_die.jpg")
            if True:  # VERTICAL_FLIP
                pcb_img = pcb_img.transpose(Image.FLIP_TOP_BOTTOM)
            pcb_img = np.array(pcb_img)
            
            # Load the data and prepare coordinates
            with open(file_path, 'r') as f:
                data = json.load(f)
            results = data["results"] if isinstance(data, dict) else data
            
            # Extract coordinates and field strengths
            x_coords = np.array([point["x"] for point in results]) * 100  # Convert to cm
            y_coords = np.array([point["y"] for point in results]) * 100
            field = np.array([point["field_strength"] for point in results])
            
            # Prepare grid for plotting
            unique_x = np.unique(x_coords)
            unique_y = np.unique(y_coords)
            
            # Create extent for both images
            extent = [unique_x.min(), unique_x.max(), unique_y.min(), unique_y.max()]
            
            # Draw PCB overlay first
            plot_objects["pcb_overlay"] = ax.imshow(
                pcb_img,
                extent=extent,
                origin="lower",
                alpha=alpha_value.get()  # Use current alpha value
            )
            
            # Prepare grid for interpolation
            grid_x, grid_y = np.linspace(extent[0], extent[1], 200), np.linspace(extent[2], extent[3], 200)
            grid_X, grid_Y = np.meshgrid(grid_x, grid_y)
            Z = griddata((x_coords, y_coords), field, (grid_X, grid_Y), method='cubic')
            
            # Draw field heatmap
            plot_objects["heatmap"] = ax.imshow(
                Z,
                extent=extent,
                origin="lower",
                cmap="plasma",
                alpha=1.0 - alpha_value.get(),  # Complementary alpha
                vmin=vmin,
                vmax=vmax
            )
            
            # Update colorbar mappings - important for correct color scale
            persistent_colorbar.update_normal(plot_objects["heatmap"])
            
            # Set labels and title
            ax.set_xlabel("X (cm)")
            ax.set_ylabel("Y (cm)")
            ax.set_title("EM Field Strength with PCB Overlay")
            ax.set_aspect('equal', adjustable='box')
            fig.suptitle(current_title.get(), fontsize=14)
            
            # Update canvas
            canvas.draw()
            
            return True
        except Exception as e:
            print(f"Error in update_plot: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def update_alpha(val):
        """Update transparency of plot elements based on slider value."""
        try:
            alpha = alpha_value.get()
            print(f"Setting alpha: {alpha}")
            
            if plot_objects["pcb_overlay"] is not None:
                plot_objects["pcb_overlay"].set_alpha(alpha)
                print("Updated PCB overlay alpha")
            
            if plot_objects["heatmap"] is not None:
                plot_objects["heatmap"].set_alpha(1.0 - alpha)
                print("Updated heatmap alpha")
            
            # Force redraw
            canvas.draw_idle()
        except Exception as e:
            print(f"Error in update_alpha: {e}")
            import traceback
            traceback.print_exc()
    
    # Create UI elements
    tk.Label(button_frame, text="Select Scan Orientation:", font=("Helvetica", 12)).pack(pady=10)
    
    # Angle selection buttons with simplified command functions
    tk.Button(button_frame, text="0° Scan", font=("Helvetica", 12),
              command=lambda: [current_file.set(file_0d), current_title.set("0° Scan"), update_plot()]).pack(pady=5, fill=tk.X)
    
    tk.Button(button_frame, text="90° Scan", font=("Helvetica", 12),
              command=lambda: [current_file.set(file_90d), current_title.set("90° Scan"), update_plot()]).pack(pady=5, fill=tk.X)
    
    tk.Button(button_frame, text="Combined Scan", font=("Helvetica", 12),
              command=lambda: [current_file.set(combined_file), current_title.set("Combined Scan"), update_plot()]).pack(pady=5, fill=tk.X)
    
    # Done button
    tk.Button(button_frame, text="Done", font=("Helvetica", 12),
              command=root.destroy).pack(pady=20, fill=tk.X)
    
    # Add alpha transparency slider with direct update function
    tk.Label(button_frame, text="Adjust Transparency:", font=("Helvetica", 12)).pack(pady=10)
    
    alpha_slider = tk.Scale(
        button_frame, 
        from_=0.0, 
        to=1.0, 
        resolution=0.01,
        orient=tk.HORIZONTAL, 
        variable=alpha_value,
        command=lambda val: update_alpha(val)
    )
    alpha_slider.pack(fill=tk.X, pady=5)
    
    # Show initial plot (combined view by default)
    update_plot()
    
    # Start the Tkinter event loop
    root.mainloop()