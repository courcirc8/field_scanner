"""
Field Visualization Module

This script visualizes the EM field strength recorded by the field scanner. It reads 
the results from a JSON file, reshapes the data into a grid, and generates a heatmap 
plot with proper scaling and aspect ratio.

Implemented Features:
- Loading scan results from a JSON file.
- Reshaping data into a grid for plotting.
- Heatmap plot generation with a colorbar and proper aspect ratio.
- User prompt to close the plot after visualization.
- Overlaying the PCB image with transparency adjustment.

Missing Features:
- Advanced visualization options (e.g., 3D plots or interactive plots).
- Support for exporting plots to image files (e.g., PNG, PDF).
- Error handling for invalid or missing input files.
"""

import json
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button  # Import Slider and Button widgets
from PIL import Image  # Import for image rotation
from scipy.interpolate import griddata  # Import for interpolation

INPUT_FILE = "scan_results.json"
PCB_IMAGE_PATH = "./pcb.jpg"  # Path to the PCB image
PCB_IMAGE_ROTATION = 0  # Rotation angle in degrees
VERTICAL_FLIP = True  # Flip the PCB image vertically
HORIZONTAL_FLIP = False  # Flip the PCB image horizontally

def plot_field():
    """Plot the EM field strength from the scan results with PCB overlay and transparency adjustment."""
    try:
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

        # Interpolate data for smoothing
        grid_x, grid_y = np.linspace(unique_x[0], unique_x[-1], 200), np.linspace(unique_y[0], unique_y[-1], 200)
        grid_X, grid_Y = np.meshgrid(grid_x, grid_y)
        Z = griddata((x, y), field_strength, (grid_X, grid_Y), method='cubic')

        # Load and rotate the PCB image
        pcb_image = Image.open(PCB_IMAGE_PATH)
        if VERTICAL_FLIP:
            pcb_image = pcb_image.transpose(Image.FLIP_TOP_BOTTOM)  # Apply vertical flip
        if HORIZONTAL_FLIP:
            pcb_image = pcb_image.transpose(Image.FLIP_LEFT_RIGHT)  # Apply horizontal flip
        pcb_image = pcb_image.rotate(PCB_IMAGE_ROTATION, expand=True)  # Apply rotation
        pcb_image = np.array(pcb_image)  # Convert to numpy array for matplotlib

        # Calculate PCB aspect ratio
        pcb_width = unique_x[-1] - unique_x[0]
        pcb_height = unique_y[-1] - unique_y[0]
        aspect_ratio = pcb_width / pcb_height

        # Create the plot
        fig, ax = plt.subplots(figsize=(8 * aspect_ratio, 8))
        plt.subplots_adjust(left=0.15, right=0.95, bottom=0.1, top=0.9)

        # Overlay the PCB image
        pcb_overlay = ax.imshow(
            pcb_image,
            extent=[unique_x[0], unique_x[-1], unique_y[0], unique_y[-1]],  # Scale to PCB dimensions
            origin="lower",  # Ensure the origin matches the field plot
            alpha=0.5  # Initial transparency
        )

        # Plot the field strength as a heatmap
        heatmap = ax.imshow(
            Z,
            extent=[grid_x[0], grid_x[-1], grid_y[0], grid_y[-1]],  # Scale to interpolated grid dimensions
            origin="lower",  # Ensure the origin matches the PCB image
            cmap="viridis",
            alpha=0.5  # Initial transparency
        )
        plt.colorbar(heatmap, ax=ax, label="Field Strength (dBm)")

        ax.set_xlabel("X (cm)")
        ax.set_ylabel("Y (cm)")
        ax.set_title("EM Field Strength with PCB Overlay")
        ax.set_aspect('equal', adjustable='box')

        # Add a slider for transparency adjustment
        ax_slider = plt.axes([0.02, 0.25, 0.03, 0.5], facecolor="lightgray")  # Slider on the left
        slider = Slider(ax_slider, "Alpha", 0.0, 1.0, valinit=0.5, orientation="vertical")

        # Update function for the slider
        def update(val):
            alpha = slider.val
            pcb_overlay.set_alpha(alpha)
            heatmap.set_alpha(1 - alpha)  # Inverse transparency for the field strength
            fig.canvas.draw_idle()

        slider.on_changed(update)

        # Add a "Done" button to close the plot
        ax_button = plt.axes([0.85, 0.02, 0.1, 0.05])  # Button at the bottom right
        button = Button(ax_button, "Done", color="lightgray", hovercolor="gray")

        def close_plot(event):
            plt.close(fig)  # Close the plot when the button is clicked

        button.on_clicked(close_plot)

        # Show the plot and block until the window is closed
        plt.show()

    except KeyboardInterrupt:
        print("\nPlot interrupted by user. Exiting cleanly...")
    finally:
        plt.close('all')  # Ensure all plots are closed

if __name__ == "__main__":
    plot_field()
