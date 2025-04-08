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

INPUT_FILE = "./scan_v1a_400MHz_Rx_module1.json"
PCB_IMAGE_PATH = "./pcb_die.jpg"  # Path to the PCB image
PCB_IMAGE_ROTATION = 0  # Rotation angle in degrees
VERTICAL_FLIP = True  # Flip the PCB image vertically
HORIZONTAL_FLIP = False  # Flip the PCB image horizontally

# Constants for the second measurement and PCB image
SECOND_INPUT_FILE = "./scan_v1a_400MHz_Rx_module2_nores_patched.json"
SECOND_PCB_IMAGE_PATH = "./pcb_die.jpg"

def plot_field(input_file, pcb_image_path, save_path=None):
    """Plot the EM field strength from the scan results with PCB overlay and transparency adjustment."""
    try:
        print(f"Loading scan results from: {input_file}")  # Debug message
        # Load scan results
        with open(input_file, "r") as f:  # Use the provided input file
            data = json.load(f)

        # Check if the data is a list (older format) or a dictionary (newer format)
        if isinstance(data, list):
            results = data  # Flat list of results (older format)
            metadata = {}  # No metadata available
            print("No metadata found. Using default values.")  # Debug message
        elif isinstance(data, dict):
            results = data.get("results", [])  # Use "results" key if available
            metadata = data.get("metadata", {})  # Extract metadata if available
            print(f"Metadata found: {metadata}")  # Debug message
        else:
            raise ValueError("Invalid JSON format: Expected a list or a dictionary.")

        # Extract metadata with defaults for missing values
        pcb_size = metadata.get("PCB_SIZE", "Unknown")
        resolution = metadata.get("resolution", "Unknown")
        center_freq = metadata.get("center_freq", "Unknown")
        bw = metadata.get("BW", "Unknown")
        nb_average = metadata.get("nb_average", "Unknown")
        file_name = metadata.get("file_name", input_file)

        # Convert center_freq and BW to MHz if they are numeric
        center_freq_mhz = f"{center_freq / 1e6:.2f} MHz" if isinstance(center_freq, (int, float)) else "Unknown"
        bw_mhz = f"{bw / 1e6:.2f} MHz" if isinstance(bw, (int, float)) else "Unknown"

        # Display metadata in the console
        print(f"Metadata for {input_file}:")
        print(f"  PCB Size: {pcb_size}")
        print(f"  Resolution: {resolution}")
        print(f"  Center Frequency: {center_freq_mhz}")
        print(f"  Bandwidth: {bw_mhz}")
        print(f"  Number of Averages: {nb_average}")
        print(f"  File Name: {file_name}")

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
            pcb_image = Image.open(pcb_image_path)  # Use the parameter instead of the global variable
        except FileNotFoundError:
            print(f"Error: PCB image file not found at path: {pcb_image_path}")  # Specific error message
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
        plt.subplots_adjust(left=0.15, right=0.95, bottom=0.35, top=0.9)  # Increased bottom margin to 0.35

        # Overlay the PCB image
        pcb_overlay = ax.imshow(
            pcb_image,
            extent=[unique_x[0], unique_x[-1], unique_y[0], unique_y[-1],],  # Scale to PCB dimensions
            origin="lower",  # Ensure the origin matches the field plot
            alpha=0.35  # Initial transparency
        )

        # Plot the field strength as a heatmap
        heatmap = ax.imshow(
            Z,
            extent=[grid_x[0], grid_x[-1], grid_y[0], grid_y[-1],],  # Scale to interpolated grid dimensions
            origin="lower",  # Ensure the origin matches the PCB image
            cmap="plasma",  # Updated colormap to 'plasma' for a larger color range
            alpha=0.65  # Initial transparency
        )
        plt.colorbar(heatmap, ax=ax, label="Field Strength (dBm)")

        ax.set_xlabel("X (cm)")
        ax.set_ylabel("Y (cm)")
        ax.set_title("EM Field Strength with PCB Overlay")
        ax.set_aspect('equal', adjustable='box')

        # Display metadata below the plot
        metadata_text = (
            f"PCB Size: {pcb_size}\n"
            f"Resolution: {resolution}\n"
            f"Center Frequency: {center_freq_mhz}\n"
            f"Bandwidth: {bw_mhz}\n"
            f"Number of Averages: {nb_average}\n"
            f"File Name: {file_name}"
        )
        fig.text(0.5, 0.01, metadata_text, ha="center", va="center", fontsize=10, wrap=True)  # Adjusted vertical position to 0.01

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

        # Save the plot as an image file if a save path is provided
        if save_path:
            plt.savefig(save_path, format="png", dpi=300)
            print(f"Plot saved to: {save_path}")

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
            data1 = json.load(f1)
        print(f"Successfully loaded data from {input_file1}.")

        print(f"Loading second scan results from: {input_file2}")
        with open(input_file2, "r") as f2:
            data2 = json.load(f2)
        print(f"Successfully loaded data from {input_file2}.")

        # Handle both older (flat list) and newer (dictionary with metadata) formats
        if isinstance(data1, list):
            results1 = data1  # Flat list of results (older format)
            metadata1 = {}  # No metadata available
        elif isinstance(data1, dict):
            results1 = data1.get("results", [])  # Use "results" key if available
            metadata1 = data1.get("metadata", {})  # Extract metadata if available
        else:
            raise ValueError(f"Invalid JSON format in {input_file1}: Expected a list or a dictionary.")

        if isinstance(data2, list):
            results2 = data2  # Flat list of results (older format)
            metadata2 = {}  # No metadata available
        elif isinstance(data2, dict):
            results2 = data2.get("results", [])  # Use "results" key if available
            metadata2 = data2.get("metadata", {})  # Extract metadata if available
        else:
            raise ValueError(f"Invalid JSON format in {input_file2}: Expected a list or a dictionary.")

        # Extract metadata with defaults for missing values
        pcb_size1 = metadata1.get("PCB_SIZE", "Unknown")
        resolution1 = metadata1.get("resolution", "Unknown")
        center_freq1 = metadata1.get("center_freq", "Unknown")
        bw1 = metadata1.get("BW", "Unknown")
        nb_average1 = metadata1.get("nb_average", "Unknown")
        file_name1 = metadata1.get("file_name", input_file1)

        pcb_size2 = metadata2.get("PCB_SIZE", "Unknown")
        resolution2 = metadata2.get("resolution", "Unknown")
        center_freq2 = metadata2.get("center_freq", "Unknown")
        bw2 = metadata2.get("BW", "Unknown")
        nb_average2 = metadata2.get("nb_average", "Unknown")
        file_name2 = metadata2.get("file_name", input_file2)

        # Convert center_freq and BW to MHz for both files
        center_freq1_mhz = f"{center_freq1 / 1e6:.2f} MHz" if isinstance(center_freq1, (int, float)) else "Unknown"
        bw1_mhz = f"{bw1 / 1e6:.2f} MHz" if isinstance(bw1, (int, float)) else "Unknown"
        center_freq2_mhz = f"{center_freq2 / 1e6:.2f} MHz" if isinstance(center_freq2, (int, float)) else "Unknown"
        bw2_mhz = f"{bw2 / 1e6:.2f} MHz" if isinstance(bw2, (int, float)) else "Unknown"

        # Display metadata for the first file
        print(f"Metadata for {input_file1}:")
        print(f"  PCB Size: {pcb_size1}")
        print(f"  Resolution: {resolution1}")
        print(f"  Center Frequency: {center_freq1_mhz}")
        print(f"  Bandwidth: {bw1_mhz}")
        print(f"  Number of Averages: {nb_average1}")
        print(f"  File Name: {file_name1}")

        # Display metadata for the second file
        print(f"Metadata for {input_file2}:")
        print(f"  PCB Size: {pcb_size2}")
        print(f"  Resolution: {resolution2}")
        print(f"  Center Frequency: {center_freq2_mhz}")
        print(f"  Bandwidth: {bw2_mhz}")
        print(f"  Number of Averages: {nb_average2}")
        print(f"  File Name: {file_name2}")

        # Extract x, y, and field_strength values for both scans
        x1 = np.array([point["x"] for point in results1]) * 100
        y1 = np.array([point["y"] for point in results1]) * 100
        field_strength1 = np.array([point["field_strength"] for point in results1])

        x2 = np.array([point["x"] for point in results2]) * 100
        y2 = np.array([point["y"] for point in results2]) * 100
        field_strength2 = np.array([point["field_strength"] for point in results2])

        # Create unique grids for each measurement
        unique_x1, unique_y1 = np.unique(x1), np.unique(y1)
        unique_x2, unique_y2 = np.unique(x2), np.unique(y2)

        grid_x1, grid_y1 = np.linspace(unique_x1[0], unique_x1[-1], 200), np.linspace(unique_y1[0], unique_y1[-1], 200)
        grid_x2, grid_y2 = np.linspace(unique_x2[0], unique_x2[-1], 200), np.linspace(unique_y2[0], unique_y2[-1], 200)

        grid_X1, grid_Y1 = np.meshgrid(grid_x1, grid_y1)
        grid_X2, grid_Y2 = np.meshgrid(grid_x2, grid_y2)

        Z1 = griddata((x1, y1), field_strength1, (grid_X1, grid_Y1), method='cubic')
        Z2 = griddata((x2, y2), field_strength2, (grid_X2, grid_Y2), method='cubic')

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
        fig, axes = plt.subplots(1, 2, figsize=(16, 8), constrained_layout=False)
        plt.subplots_adjust(left=0.1, right=0.9, bottom=0.4, top=0.9)  # Increased bottom margin to 0.4

        # Plot the first measurement
        pcb_overlay1 = axes[0].imshow(
            pcb_image1,
            extent=[unique_x1[0], unique_x1[-1], unique_y1[0], unique_y1[-1]],
            origin="lower",
            alpha=0.35  # Initial transparency set to 0.35
        )
        heatmap1 = axes[0].imshow(
            Z1,
            extent=[grid_x1[0], grid_x1[-1], grid_y1[0], grid_y1[-1]],
            origin="lower",
            cmap="plasma",  # Updated colormap to 'plasma' for a larger color range
            alpha=0.65  # Complementary transparency
        )
        axes[0].set_title(f"Measurement 1")
        axes[0].set_xlabel("X (cm)")
        axes[0].set_ylabel("Y (cm)")
        axes[0].set_aspect('equal', adjustable='box')

        # Plot the second measurement
        pcb_overlay2 = axes[1].imshow(
            pcb_image2,
            extent=[unique_x2[0], unique_x2[-1], unique_y2[0], unique_y2[-1]],
            origin="lower",
            alpha=0.35  # Initial transparency set to 0.35
        )
        heatmap2 = axes[1].imshow(
            Z2,
            extent=[grid_x2[0], grid_x2[-1], grid_y2[0], grid_y2[-1]],
            origin="lower",
            cmap="plasma",  # Updated colormap to 'plasma' for a larger color range
            alpha=0.65  # Complementary transparency
        )
        axes[1].set_title(f"Measurement 2")
        axes[1].set_xlabel("X (cm)")
        axes[1].set_ylabel("Y (cm)")
        axes[1].set_aspect('equal', adjustable='box')

        # Add a shared transparency slider
        ax_slider = plt.axes([0.02, 0.25, 0.03, 0.5], facecolor="lightgray")  # Slider on the left
        slider = Slider(ax_slider, "Alpha", 0.0, 1.0, valinit=0.35, orientation="vertical")

        # Update function for the slider
        def update(val):
            alpha = slider.val
            pcb_overlay1.set_alpha(alpha)
            heatmap1.set_alpha(1 - alpha)  # Inverse transparency for the first heatmap
            pcb_overlay2.set_alpha(alpha)
            heatmap2.set_alpha(1 - alpha)  # Inverse transparency for the second heatmap
            fig.canvas.draw_idle()

        slider.on_changed(update)

        # Display metadata below the plots
        metadata_text1 = (
            f"PCB Size: {pcb_size1}\n"
            f"Resolution: {resolution1}\n"
            f"Center Frequency: {center_freq1_mhz}\n"
            f"Bandwidth: {bw1_mhz}\n"
            f"Number of Averages: {nb_average1}\n"
            f"File Name: {file_name1}"
        )
        metadata_text2 = (
            f"PCB Size: {pcb_size2}\n"
            f"Resolution: {resolution2}\n"
            f"Center Frequency: {center_freq2_mhz}\n"
            f"Bandwidth: {bw2_mhz}\n"
            f"Number of Averages: {nb_average2}\n"
            f"File Name: {file_name2}"
        )
        fig.text(0.25, 0.07, metadata_text1, ha="center", va="center", fontsize=10, wrap=True)  # Adjusted vertical position to 0.07
        fig.text(0.75, 0.07, metadata_text2, ha="center", va="center", fontsize=10, wrap=True)  # Adjusted vertical position to 0.07

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
    compare_fields(INPUT_FILE, PCB_IMAGE_PATH, SECOND_INPUT_FILE, SECOND_PCB_IMAGE_PATH)
