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

INPUT_FILE = "./scan_v1a_470ohms_m60d.json"
PCB_IMAGE_PATH = "./pcb_die.jpg"  # Path to the PCB image
PCB_IMAGE_ROTATION = 0  # Rotation angle in degrees
VERTICAL_FLIP = True  # Flip the PCB image vertically
HORIZONTAL_FLIP = False  # Flip the PCB image horizontally

# Constants for the second measurement and PCB image
SECOND_INPUT_FILE = "./scan_v1b_m60d.json"
SECOND_PCB_IMAGE_PATH = "./pcb_die.jpg"

def plot_field(input_file):
    """Plot the EM field strength from the scan results with PCB overlay and transparency adjustment."""
    try:
        print(f"Loading scan results from: {input_file}")  # Debug message
        # Load scan results
        with open(input_file, "r") as f:  # Use the provided input file
            results = json.load(f)
        print(f"Successfully loaded {len(results)} data points from {input_file}.")  # Debug message

        # Extract x, y, and field_strength values
        x = np.array([point["x"] for point in results]) * 100  # Convert from meters to cm
        y = np.array([point["y"] for point in results]) * 100  # Convert from meters to cm
        field_strength = np.array([point["field_strength"] for point in results])
        print(f"Extracted x, y, and field_strength arrays.")  # Debug message

        # Reshape data for plotting
        unique_x = np.unique(x)
        unique_y = np.unique(y)
        print(f"Unique x values: {unique_x}")  # Debug message
        print(f"Unique y values: {unique_y}")  # Debug message
        X, Y = np.meshgrid(unique_x, unique_y)
        Z = field_strength.reshape(len(unique_y), len(unique_x))

        # Interpolate data for smoothing
        grid_x, grid_y = np.linspace(unique_x[0], unique_x[-1], 200), np.linspace(unique_y[0], unique_y[-1], 200)
        grid_X, grid_Y = np.meshgrid(grid_x, grid_y)
        Z = griddata((x, y), field_strength, (grid_X, grid_Y), method='cubic')

        # Load and rotate the PCB image
        try:
            pcb_image = Image.open(PCB_IMAGE_PATH)
        except FileNotFoundError:
            print(f"Error: PCB image file not found at path: {PCB_IMAGE_PATH}")  # Specific error message
            return

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

        print("Creating the plot...")  # Debug message
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

        print("Displaying the plot...")  # Debug message
        plt.show(block=True)  # Ensure the plot remains open until the user closes it
        print("Plot closed.")  # Debug message

    except FileNotFoundError:
        print(f"Error: File not found at path: {input_file}")  # Updated error message
    except json.JSONDecodeError:
        print(f"Error: Failed to decode JSON from file: {input_file}")  # Updated error message
    except Exception as e:
        print(f"An unexpected error occurred while processing file {input_file}: {e}")  # Updated error message
    finally:
        plt.close('all')  # Ensure all plots are closed

def compare_fields(input_file1, pcb_image1, input_file2, pcb_image2):
    """Compare two measurements side by side with the same scale."""
    try:
        print(f"Loading first scan results from: {input_file1}")
        with open(input_file1, "r") as f1:
            results1 = json.load(f1)
        print(f"Successfully loaded {len(results1)} data points from {input_file1}.")

        print(f"Loading second scan results from: {input_file2}")
        with open(input_file2, "r") as f2:
            results2 = json.load(f2)
        print(f"Successfully loaded {len(results2)} data points from {input_file2}.")

        # Extract x, y, and field_strength values for both scans
        x1 = np.array([point["x"] for point in results1]) * 100
        y1 = np.array([point["y"] for point in results1]) * 100
        field_strength1 = np.array([point["field_strength"] for point in results1])

        x2 = np.array([point["x"] for point in results2]) * 100
        y2 = np.array([point["y"] for point in results2]) * 100
        field_strength2 = np.array([point["field_strength"] for point in results2])

        # Reshape data for plotting
        unique_x = np.unique(np.concatenate((x1, x2)))
        unique_y = np.unique(np.concatenate((y1, y2)))
        grid_x, grid_y = np.linspace(unique_x[0], unique_x[-1], 200), np.linspace(unique_y[0], unique_y[-1], 200)
        grid_X, grid_Y = np.meshgrid(grid_x, grid_y)

        Z1 = griddata((x1, y1), field_strength1, (grid_X, grid_Y), method='cubic')
        Z2 = griddata((x2, y2), field_strength2, (grid_X, grid_Y), method='cubic')

        # Load and process PCB images with the same flip and rotation settings
        try:
            pcb_image1 = Image.open(pcb_image1)
            pcb_image2 = Image.open(pcb_image2)

            if VERTICAL_FLIP:
                pcb_image1 = pcb_image1.transpose(Image.FLIP_TOP_BOTTOM)
                pcb_image2 = pcb_image2.transpose(Image.FLIP_TOP_BOTTOM)
            if HORIZONTAL_FLIP:
                pcb_image1 = pcb_image1.transpose(Image.FLIP_LEFT_RIGHT)
                pcb_image2 = pcb_image2.transpose(Image.FLIP_LEFT_RIGHT)

            pcb_image1 = pcb_image1.rotate(PCB_IMAGE_ROTATION, expand=True)
            pcb_image2 = pcb_image2.rotate(PCB_IMAGE_ROTATION, expand=True)

            pcb_image1 = np.array(pcb_image1)
            pcb_image2 = np.array(pcb_image2)
        except FileNotFoundError as e:
            print(f"Error: PCB image file not found: {e}")
            return

        # Create the plot
        print("Creating comparison plot...")
        fig, axes = plt.subplots(1, 2, figsize=(16, 8), constrained_layout=True)

        # Plot the first measurement
        pcb_overlay1 = axes[0].imshow(
            pcb_image1,
            extent=[unique_x[0], unique_x[-1], unique_y[0], unique_y[-1]],
            origin="lower",
            alpha=0.5
        )
        heatmap1 = axes[0].imshow(
            Z1,
            extent=[grid_x[0], grid_x[-1], grid_y[0], grid_y[-1]],
            origin="lower",
            cmap="viridis",
            alpha=0.5
        )
        axes[0].set_title(f"Measurement 1: {input_file1}")
        axes[0].set_xlabel("X (cm)")
        axes[0].set_ylabel("Y (cm)")
        axes[0].set_aspect('equal', adjustable='box')

        # Plot the second measurement
        pcb_overlay2 = axes[1].imshow(
            pcb_image2,
            extent=[unique_x[0], unique_x[-1], unique_y[0], unique_y[-1]],
            origin="lower",
            alpha=0.5
        )
        heatmap2 = axes[1].imshow(
            Z2,
            extent=[grid_x[0], grid_x[-1], grid_y[0], grid_y[-1]],
            origin="lower",
            cmap="viridis",
            alpha=0.5
        )
        axes[1].set_title(f"Measurement 2: {input_file2}")
        axes[1].set_xlabel("X (cm)")
        axes[1].set_ylabel("Y (cm)")
        axes[1].set_aspect('equal', adjustable='box')

        # Move the transparency slider further to the left
        ax_slider = plt.axes([0.01, 0.25, 0.02, 0.5], facecolor="lightgray")  # Adjusted position
        slider = Slider(ax_slider, "Alpha", 0.0, 1.0, valinit=0.5, orientation="vertical")

        def update_alpha(val):
            alpha = slider.val
            pcb_overlay1.set_alpha(alpha)
            heatmap1.set_alpha(1 - alpha)
            pcb_overlay2.set_alpha(alpha)
            heatmap2.set_alpha(1 - alpha)
            fig.canvas.draw_idle()

        slider.on_changed(update_alpha)

        # Add a single colorbar for both plots
        cbar = fig.colorbar(heatmap1, ax=axes, location="right", shrink=0.8, label="Field Strength (dBm)")

        print("Displaying the comparison plot...")
        plt.show()
        print("Comparison plot closed.")

    except FileNotFoundError as e:
        print(f"Error: File not found: {e}")
    except json.JSONDecodeError as e:
        print(f"Error: Failed to decode JSON: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    # Compare two measurements by default
    compare_fields(INPUT_FILE, PCB_IMAGE_PATH, SECOND_INPUT_FILE, SECOND_PCB_IMAGE_PATH)
