"""
Field Visualization Module

This module provides advanced visualization tools for electromagnetic field scans.
It processes scan data and creates visualizations with PCB image overlays.

Key features include:
- Loading scan results from JSON files with metadata
- Creating heatmap visualizations of field strength
- Overlaying PCB images for reference
- Interactive transparency adjustment
- Support for single and comparative visualizations
- Metadata display for context

The implementation addresses several visualization challenges:
1. Interpolation of sparse measurement points into a smooth field map
2. Proper alignment of field data with PCB image
3. Interactive controls for exploring the data
4. Handling both single measurements and comparisons
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

def plot_field(input_file, pcb_image_path, save_path=None, ax=None, vmin=None, vmax=None):
    """
    Plot the EM field strength from scan results with PCB overlay and transparency adjustment.
    
    This is the primary visualization function that:
    1. Loads scan data and metadata from a JSON file
    2. Processes the raw points into a continuous field visualization
    3. Overlays the PCB image with adjustable transparency
    4. Displays metadata and measurement information
    
    Args:
        input_file: Path to the scan results file
        pcb_image_path: Path to the PCB image overlay
        save_path: Optional path to save the generated image
        ax: Optional existing matplotlib axis to plot on
        vmin/vmax: Optional min/max values for consistent color scale
        
    Returns:
        Dictionary of plot objects when in embedded mode, None otherwise
    """
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
        
        # Check if we have 1D data (only one y-value)
        is_1d_data = len(unique_y) == 1
        
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
        pcb_height = pcb_width / 2 if is_1d_data else (unique_y[-1] - unique_y[0])  # Estimate height for 1D data
        aspect_ratio = pcb_width / pcb_height

        # Create a new figure and axis if no axis is provided
        if ax is None:
            fig, ax = plt.subplots(figsize=(8 * aspect_ratio, 8))
            plt.subplots_adjust(left=0.15, right=0.95, bottom=0.35, top=0.9)  # Adjust margins
        else:
            fig = ax.figure  # Get the figure from the provided axis

        # Overlay the PCB image
        extent = [unique_x[0], unique_x[-1], 
                 unique_y[0] - pcb_height/2 if is_1d_data else unique_y[0], 
                 unique_y[0] + pcb_height/2 if is_1d_data else unique_y[-1]]
                 
        pcb_overlay = ax.imshow(
            pcb_image,
            extent=extent,  # Scale to PCB dimensions
            origin="lower",  # Ensure the origin matches the field plot
            alpha=0.35  # Initial transparency
        )

        # Handle 1D vs 2D data differently
        if is_1d_data:
            # For 1D data - create a simple line plot
            sorted_data = sorted(zip(x, field_strength))
            x_sorted = [point[0] for point in sorted_data]
            field_sorted = [point[1] for point in sorted_data]
            
            heatmap = ax.plot(x_sorted, [unique_y[0]] * len(x_sorted), 'o-', 
                            color='red', linewidth=2, alpha=0.65,
                            marker='o', markersize=6)[0]
            
            # Color the markers according to field strength
            scatter = ax.scatter(x_sorted, [unique_y[0]] * len(x_sorted), 
                               c=field_sorted, cmap='plasma', 
                               vmin=vmin, vmax=vmax,
                               s=50, alpha=0.8)
            
            # Add colorbar if needed
            if ax is None or (vmin is None and vmax is None):
                plt.colorbar(scatter, ax=ax, label="Field Strength (dBm)")
        else:
            # For 2D data - use griddata interpolation as before
            try:
                # Prepare grid for interpolation
                grid_x, grid_y = np.linspace(extent[0], extent[1], 200), np.linspace(extent[2], extent[3], 200)
                grid_X, grid_Y = np.meshgrid(grid_x, grid_y)
                Z = griddata((x, y), field_strength, (grid_X, grid_Y), method='cubic')
                
                # Draw field heatmap
                heatmap = ax.imshow(
                    Z,
                    extent=extent,
                    origin="lower",
                    cmap="plasma",
                    alpha=0.65,  # Complementary transparency
                    vmin=vmin,
                    vmax=vmax
                )
                
                # Only create colorbar if axis is None or no vmin/vmax provided
                if ax is None or (vmin is None and vmax is None):
                    plt.colorbar(heatmap, ax=ax, label="Field Strength (dBm)")
            except Exception as e:
                # Fallback to scatter plot if interpolation fails
                print(f"Interpolation failed, using scatter plot instead: {e}")
                scatter = ax.scatter(x, y, c=field_strength, cmap='plasma', 
                                    vmin=vmin, vmax=vmax, s=50, alpha=0.8)
                heatmap = scatter  # For consistency in return value
                
                if ax is None or (vmin is None and vmax is None):
                    plt.colorbar(scatter, ax=ax, label="Field Strength (dBm)")

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

        # Add a slider for transparency adjustment if no axis is provided
        if ax is None:
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

        # Display the plot if no axis is provided
        if ax is None:
            print("Displaying the plot...")  # Debug message
            plt.show(block=True)  # Ensure the plot remains open until the user closes it
            print("Plot closed.")  # Debug message

        # Return the plot objects if axis is provided
        if ax is not None:
            return {'pcb_overlay': pcb_overlay, 'heatmap': heatmap}

    except FileNotFoundError:
        print(f"Error: File not found at path: {input_file}")  # Updated error message
    except json.JSONDecodeError:
        print(f"Error: Failed to decode JSON from file: {input_file}")  # Updated error message
    except Exception as e:
        print(f"An unexpected error occurred while processing file {input_file}: {e}")  # Updated error message
    finally:
        if ax is None:
            plt.close('all')  # Ensure all plots are closed
        return None  # Return None if there was an error

def compare_fields(input_file1, pcb_image1, input_file2, pcb_image2):
    """
    Compare two measurements side by side with the same color scale.
    
    This function creates a side-by-side comparison visualization that:
    1. Loads two different scan results files
    2. Processes and displays them with consistent scaling
    3. Shows metadata for both scans
    4. Provides interactive transparency adjustment
    
    This is particularly useful for comparing:
    - Before/after modifications to a PCB
    - Different frequencies on the same PCB
    - Same PCB with different components populated
    
    Args:
        input_file1/input_file2: Paths to the scan results files
        pcb_image1/pcb_image2: Paths to the corresponding PCB images
    """
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
