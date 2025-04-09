"""
This module provides visualization tools for electromagnetic field measurements.
It includes functions for:
1. Creating interactive plots for real-time scanning.
2. Updating plots during the scanning process with live feedback.
3. Displaying results with selectable scan orientations (0°, 90°, 45°, and combined views).
4. Visualizing current directions based on magnetic field measurements.
5. Allowing users to adjust transparency of the PCB overlay and heatmap.
6. Supporting cached current direction data for faster visualization.
7. Handling metadata display, including PCB size, resolution, and frequency information.
8. Providing flexible UI elements such as buttons for angle selection and a slider for transparency adjustment.
9. Supporting both individual arrows and streamlines for current direction visualization.
10. Ensuring consistent color scaling across different scan orientations.

Key Features:
- Interactive angle selection: Users can switch between 0°, 90°, 45°, and combined views.
- Real-time updates: The plot updates dynamically during the scanning process.
- Current direction visualization: Displays current flow using arrows or streamlines.
- Metadata extraction: Displays PCB size, resolution, and other scan parameters.
- Error handling: Handles missing or invalid data gracefully.
- Caching: Supports caching of computed current directions for faster reloading.

Challenges Addressed:
- Maintaining consistent color scaling across different scan orientations.
- Efficiently visualizing large datasets with high resolution.
- Providing a user-friendly interface for exploring scan results.

Dependencies:
- matplotlib: For plotting and interactive UI elements.
- numpy: For numerical operations and grid interpolation.
- scipy: For interpolating field strength data.
- PIL (Pillow): For loading and displaying PCB images.
- json: For handling scan data and metadata.
- multiprocessing: For parallel processing of current direction calculations.
"""

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
# Import PCB_IMAGE_PATH, VERTICAL_FLIP, and CURRENT_GRID_SPACING_MM from config
from config import PCB_IMAGE_PATH, VERTICAL_FLIP, CURRENT_GRID_SPACING_MM
import time  # Import for timing calculations
from multiprocessing import Pool  # Import for parallel processing

# Define constants
GRID_SPACING = 2  # Spacing for current direction lines in mm

def validate_file(file_path):
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        return False
    try:
        with open(file_path, 'r') as f:
            json.load(f)
    except Exception as e:
        print(f"Error: Invalid JSON file: {file_path}. {e}")
        return False
    return True

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
    fig.canvas.manager.set_window_title("Measuring board - real-time scan view")  # Set a more meaningful window title
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
    """
    x = [point["x"] for point in results]
    y = [point["y"] for point in results]
    field_strength = [point["field_strength"] for point in results]

    unique_x = sorted(set(x_values))
    unique_y = sorted(set(y_values))
    
    # Check if we have more than one unique y-value (2D data)
    is_2d_data = len(unique_y) > 1
    
    # Clear previous plot elements
    for artist in ax.collections:
        artist.remove()
        
    if is_2d_data:
        # For 2D data, use meshgrid and contourf as before
        X, Y = np.meshgrid(unique_x, unique_y)  # Use np.meshgrid instead of plt.meshgrid
        Z = np.full((len(unique_y), len(unique_x)), np.nan)  # Initialize with NaN values

        for point in results:
            xi = unique_x.index(point["x"])
            yi = unique_y.index(point["y"])
            if point["field_strength"] is not None:  # Check for None values
                Z[yi][xi] = point["field_strength"]

        try:
            # Only create contour plot if we have valid data
            if not np.all(np.isnan(Z)):
                contour = ax.contourf(X, Y, Z, cmap="viridis", levels=50, alpha=0.35)
                # Update colorbar if we have a valid contour
                if hasattr(colorbar, 'update_normal'):
                    colorbar.update_normal(contour)
        except Exception as e:
            print(f"Warning: Could not create contour plot: {e}")
            # Fallback to scatter plot if contour fails
            valid_points = [(x[i], y[i], field_strength[i]) for i in range(len(x)) if field_strength[i] is not None]
            if valid_points:
                x_valid, y_valid, fs_valid = zip(*valid_points)
                contour = ax.scatter(x_valid, y_valid, c=fs_valid, cmap="viridis", alpha=0.8)
    else:
        # For 1D data (only one y-value), use a line plot
        sorted_data = sorted([(p["x"], p["field_strength"]) for p in results if p["field_strength"] is not None])
        if sorted_data:  # Only proceed if we have valid data
            x_sorted = [point[0] for point in sorted_data]
            field_sorted = [point[1] for point in sorted_data]
            
            # Plot as a line
            if hasattr(contour, 'remove'):
                contour.remove()  # Remove previous line
            contour = ax.plot(x_sorted, field_sorted, 'o-', color='blue', linewidth=2, alpha=0.8)[0]
            
            # Set y-axis limits with a buffer
            if field_sorted:  # Only set limits if we have data
                y_min = min(field_sorted) - 5
                y_max = max(field_sorted) + 5
                ax.set_ylim(y_min, y_max)
    
    ax.set_xlabel("X (cm)")
    ax.set_ylabel("Y (cm)" if is_2d_data else "Field Strength (dBm)")
    ax.set_title("EM Field Strength (Interactive)")
    ax.set_aspect('auto')  # Changed from 'equal' to 'auto' for better display of 1D data
    plt.pause(0.1)

    return contour

def load_data(file_path):
    """Load and validate the data from the given JSON file."""
    try:
        # Check if the file is a JSON file
        if file_path.endswith(".json"):
            with open(file_path, "r") as f:
                data = json.load(f)
            
            # Extract metadata and results
            metadata = data.get("metadata", {})
            results = data.get("results", [])
            
            # Extract PCB size and resolution
            pcb_size = metadata.get("PCB_SIZE", [1.0, 1.0])  # Default to 1x1 if missing
            resolution = metadata.get("resolution", 30)  # Default resolution
            
            # Create a 2D grid for the field strength
            x_values = sorted(set(point["x"] for point in results))
            y_values = sorted(set(point["y"] for point in results))
            field_strength = np.full((len(y_values), len(x_values)), np.nan)  # Initialize with NaN
            
            for point in results:
                x_idx = x_values.index(point["x"])
                y_idx = y_values.index(point["y"])
                field_strength[y_idx, x_idx] = point["field_strength"]
            
            return field_strength, pcb_size, resolution
        else:
            raise ValueError("Unsupported file format. Only JSON files are supported.")
    except Exception as e:
        print(f"Error loading data from {file_path}: {e}")
        return None, None, None

def compute_current_direction(args):
    x, y, points_0d, points_90d = args
    # Compute current direction logic here
    return x, y, dx, dy

def show_currents(event):
    """Display current directions using arrows or streamlines and save intensity data.
    
    This function processes the measurements from different probe orientations to estimate
    current directions on the PCB. The process works as follows:
    
    1. Loads data from three orientations: 0°, 90°, and optionally 45°
    2. Converts field strength from dBm (logarithmic) to linear power units
    3. Computes field orientation angles using the relative strength at different orientations
    4. Calculates the total field intensity using the 0° and 90° measurements
    5. Generates streamlines to visualize the current flow patterns
    
    The orientation angle calculation uses arctan2(B_90 - B_0, B_45) where:
    - B_0: Field strength at 0° (linear scale)
    - B_90: Field strength at 90° (linear scale)
    - B_45: Field strength at 45° (linear scale)
    
    This approach leverages the fact that the magnetic field is perpendicular to
    current flow, allowing us to estimate current directions from the field measurements.
    The intensity of the field provides information about the relative current strength.
    """
    print("Computing current directions for all stored points...")

    # Access the figure and required file paths 
    try:
        fig = event.inaxes.figure
        plot_ax = fig.main_plot_ax  # Use the stored reference to the main plot axes
        
        # Get file paths stored in the figure object
        file_0d = fig.file_0d
        file_90d = fig.file_90d
        file_45d = fig.file_45d if hasattr(fig, 'file_45d') else None
        
        print(f"Using files for current calculation:")
        print(f"  0° file: {file_0d}")
        print(f"  90° file: {file_90d}")
        print(f"  45° file: {file_45d if file_45d else 'Not available'}")

        # Load data
        with open(file_0d, 'r') as f:
            data_0d = json.load(f)
        with open(file_90d, 'r') as f:
            data_90d = json.load(f)
        if file_45d and os.path.exists(file_45d):
            with open(file_45d, 'r') as f:
                data_45d = json.load(f)
        else:
            data_45d = None
    except Exception as e:
        print(f"Error loading angle files: {e}")
        return

    # Extract results
    results_0d = data_0d["results"]
    results_90d = data_90d["results"]
    results_45d = data_45d["results"] if data_45d else None

    # Compute angles and intensities for all points
    results = []
    for i, point_0d in enumerate(results_0d):
        x = point_0d["x"]
        y = point_0d["y"]
        field_0_dBm = point_0d["field_strength"]
        field_90_dBm = results_90d[i]["field_strength"]
        field_45_dBm = results_45d[i]["field_strength"] if results_45d else 0

        # Convert field strength from dBm to linear scale
        # This is necessary because dBm is logarithmic, and we need linear values for vector calculations
        field_0 = 10 ** (field_0_dBm / 10)
        field_90 = 10 ** (field_90_dBm / 10) 
        field_45 = 10 ** (field_45_dBm / 10)

        # Compute the orientation of the field (angle estimation)
        # The formula arctan2(B_90-B_0, B_45) estimates the field orientation
        # based on the relative strength of the field measured at different probe angles
        angle = np.arctan2(field_90 - field_0, field_45)

        # Compute the field intensity using only 0° and 90°
        # The intensity is calculated as the magnitude of the combined orthogonal components
        intensity = np.sqrt(field_0**2 + field_90**2)

        # Append results
        results.append({
            "x": x,
            "y": y,
            "field_strength": intensity,
            "angle": angle
        })

    # Save intensity and angle data to _debug_intensity.json
    debug_intensity_file = "debug_intensity.json"
    debug_data = {
        "metadata": data_0d.get("metadata", {}),
        "results": results
    }
    with open(debug_intensity_file, 'w') as f:
        json.dump(debug_data, f, indent=4)
    print(f"Debug intensity and angle data saved to {debug_intensity_file}")

    # Prepare data for visualization
    x = [point["x"] for point in results]
    y = [point["y"] for point in results]
    intensity = [point["field_strength"] for point in results]
    angle = [point["angle"] for point in results]

    # Create a grid for visualization
    unique_x = sorted(set(x))
    unique_y = sorted(set(y))
    X, Y = np.meshgrid(unique_x, unique_y)
    Z_intensity = np.full((len(unique_y), len(unique_x)), np.nan)
    U = np.full((len(unique_y), len(unique_x)), np.nan)
    V = np.full((len(unique_y), len(unique_x)), np.nan)

    for point in results:
        xi = unique_x.index(point["x"])
        yi = unique_y.index(point["y"])
        Z_intensity[yi, xi] = point["field_strength"]
        U[yi, xi] = np.cos(point["angle"])
        V[yi, xi] = np.sin(point["angle"])

    # Normalize the intensity for visualization
    # This ensures that the streamline coloring and width are properly scaled
    intensity_normalized = Z_intensity / np.nanmax(Z_intensity)

    # Plot streamlines with intensity-based linewidth
    try:
        X_cm = X * 100
        Y_cm = Y * 100
        stream = plot_ax.streamplot(
            X_cm, Y_cm, U, V,
            color=intensity_normalized,  # Use field intensity to color the streamlines
            linewidth=2 * intensity_normalized,  # Thicker lines indicate stronger currents
            cmap='viridis',  # Color map for intensity visualization
            density=2.0  # Higher density provides more detailed current flow patterns
        )
        plot_ax.set_xlim(min(x) * 100, max(x) * 100)
        plot_ax.set_ylim(min(y) * 100, max(y) * 100)
        fig.canvas.draw_idle()
        print("Streamlines displayed.")
    except ValueError as e:
        print(f"Error processing current directions: {e}")

def show_debug_intensity(event):
    """Display the debug intensity data as a heatmap."""
    debug_intensity_file = "debug_intensity.json"
    if not os.path.exists(debug_intensity_file):
        print(f"Debug intensity file not found: {debug_intensity_file}")
        return

    with open(debug_intensity_file, 'r') as f:
        debug_data = json.load(f)

    results = debug_data["results"]
    x = [point["x"] for point in results]
    y = [point["y"] for point in results]
    field_strength = [point["field_strength"] for point in results]

    # Create a grid for plotting
    unique_x = sorted(set(x))
    unique_y = sorted(set(y))
    X, Y = np.meshgrid(unique_x, unique_y)
    Z = np.full((len(unique_y), len(unique_x)), np.nan)

    for point in results:
        xi = unique_x.index(point["x"])
        yi = unique_y.index(point["y"])
        Z[yi, xi] = point["field_strength"]

    # Access the plot_ax from the figure object
    fig = event.inaxes.figure
    plot_ax = fig.main_plot_ax

    # Plot the intensity heatmap
    plot_ax.clear()
    plot_ax.contourf(X, Y, Z, cmap="viridis", levels=50)
    plot_ax.set_title("Debug Intensity Heatmap")
    plot_ax.set_xlabel("X (cm)")
    plot_ax.set_ylabel("Y (cm)")
    fig.canvas.draw_idle()
    print("Debug intensity heatmap displayed.")

def plot_with_selector(file_0d, file_90d, file_45d=None):
    """
    Plot results with angle selector for switching between 0°, 90°, 45°, and combined views.
    """
    print(f"Starting plot_with_selector with files:")
    print(f"  0° file: {file_0d}")
    print(f"  90° file: {file_90d}")
    print(f"  45° file: {file_45d if file_45d else 'Not provided'}")

    # Load data files
    with open(file_0d, 'r') as f:
        data_0d = json.load(f)
    with open(file_90d, 'r') as f:
        data_90d = json.load(f)
    
    # Load 45° data if available
    data_45d = None
    if file_45d and os.path.exists(file_45d):
        with open(file_45d, 'r') as f:
            data_45d = json.load(f)
    
    # Create combined data
    combined_file = file_0d.replace('_0d.json', '_combined.json')
    if not os.path.exists(combined_file):
        print(f"Creating combined file at {combined_file}")
        data_combined = combine_scans(file_0d, file_90d, file_45d)
        with open(combined_file, 'w') as f:
            json.dump(data_combined, f)
    else:
        print(f"Loading existing combined file from {combined_file}")
        with open(combined_file, 'r') as f:
            data_combined = json.load(f)
    
    # Get global min/max for consistent colormap
    all_field_strengths = []
    for dataset in [data_0d, data_90d, data_combined]:
        if dataset:
            all_field_strengths.extend([point["field_strength"] for point in dataset["results"]])
    # Add 45° data if available
    if data_45d:
        all_field_strengths.extend([point["field_strength"] for point in data_45d["results"]])
    
    vmin = min(all_field_strengths)
    vmax = max(all_field_strengths)
    print(f"Field strength range: {vmin:.2f} to {vmax:.2f} dBm")
    
    # Extract PCB size from metadata
    metadata = data_0d.get("metadata", {}) if isinstance(data_0d, dict) else {}
    pcb_size = metadata.get("PCB_SIZE", [1.0, 1.0])  # Default to 1x1 if missing
    print(f"PCB size from metadata: {pcb_size}")
    
    # Create figure with space for UI elements
    plt.rcParams.update({'font.size': 10})
    fig = plt.figure(figsize=(12, 8))
    
    # Create plot area and UI areas - main plot on right side, controls on left
    plot_ax = plt.axes([0.25, 0.25, 0.7, 0.65])  # Main plot area (moved to the right)
    
    # Store a reference to the main plot axes in the figure for access by callbacks
    fig.main_plot_ax = plot_ax
    
    # Create controls area on left side of window
    buttons_left_pos = 0.05
    button_width = 0.12
    button_height = 0.05
    button_spacing = 0.015
    button_start_y = 0.65
    
    # Create button areas - stack vertically on left side
    button0_ax = plt.axes([buttons_left_pos, button_start_y, button_width, button_height])
    button90_ax = plt.axes([buttons_left_pos, button_start_y - (button_height + button_spacing), button_width, button_height])
    button45_ax = plt.axes([buttons_left_pos, button_start_y - 2 * (button_height + button_spacing), button_width, button_height])
    button_combined_ax = plt.axes([buttons_left_pos, button_start_y - 3 * (button_height + button_spacing), button_width, button_height])
    
    # Add current direction button below others
    button_current_ax = plt.axes([buttons_left_pos, button_start_y - 4 * (button_height + button_spacing), button_width, button_height])
    
    # Add Done button at the bottom
    button_done_ax = plt.axes([buttons_left_pos, button_start_y - 5 * (button_height + button_spacing), button_width, button_height])
    
    # Add transparency slider on the left - moved down to avoid overlap
    slider_ax = plt.axes([buttons_left_pos, 0.15, button_width, 0.03])  # Moved down from 0.2 to 0.15
    
    # Add debug intensity button at the bottom left
    button_debug_ax = plt.axes([0.05, 0.05, 0.12, 0.05])
    button_debug = Button(button_debug_ax, 'Debug Intensity', color='orange')
    button_debug.on_clicked(show_debug_intensity)
    
    # Create a dictionary to store plot objects
    plot_objects = {
        "pcb_overlay": None,
        "heatmap": None,
        "current_lines": [],
        "colorbar": None
    }
    
    # Current active file
    current_file = file_0d
    current_title = "0° Scan"
    current_data = data_0d
    
    # Store the current file directly in the figure for access from callbacks
    fig.current_file = current_file
    # Store all file paths in the figure object for access by show_currents
    fig.file_0d = file_0d
    fig.file_90d = file_90d
    fig.file_45d = file_45d
    
    # Create transparency slider - MOVED THIS HERE TO FIX THE ERROR
    alpha_slider = Slider(slider_ax, 'PCB Transparency', 0.0, 1.0, valinit=0.5)
    
    # Create a variable to store our colorbar reference
    colorbar_obj = None

    def load_and_prepare_data(file_path):
        """Load data and prepare for plotting"""
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Extract results depending on data format
        if isinstance(data, dict) and "results" in data:
            results = data["results"]
            metadata = data.get("metadata", {})
        else:
            results = data
            metadata = {}
            
        # Extract coordinates and field strengths
        x = np.array([point["x"] for point in results]) * 100  # Convert to cm
        y = np.array([point["y"] for point in results]) * 100
        field_strength = np.array([point["field_strength"] for point in results])
        
        # Get unique coordinates for grid
        unique_x = np.unique(x)
        unique_y = np.unique(y)
        
        # Prepare grid for interpolation
        grid_x = np.linspace(min(unique_x), max(unique_x), 200)
        grid_y = np.linspace(min(unique_y), max(unique_y), 200)
        grid_X, grid_Y = np.meshgrid(grid_x, grid_y)
        
        # Interpolate field values
        Z = griddata((x, y), field_strength, (grid_X, grid_Y), method='cubic')
        
        # Calculate extent for plotting
        extent = [min(unique_x), max(unique_x), min(unique_y), max(unique_y)]
        
        return data, results, metadata, Z, extent
    
    def update_plot():
        """Update the plot with current data"""
        nonlocal current_data, colorbar_obj  # Include colorbar_obj in the same nonlocal declaration
        print(f"Updating plot with file: {current_file}")
        
        try:
            # Clear the plot
            plot_ax.clear()
            
            # Clear current lines
            for line in plot_objects["current_lines"]:
                if hasattr(line, 'remove'):
                    line.remove()
            plot_objects["current_lines"] = []
            
            # Load and prepare data
            current_data, results, metadata, Z, extent = load_and_prepare_data(current_file)
            
            # Load PCB image
            try:
                pcb_img = Image.open(PCB_IMAGE_PATH)
                if VERTICAL_FLIP:
                    pcb_img = pcb_img.transpose(Image.FLIP_TOP_BOTTOM)
                pcb_img = np.array(pcb_img)
            except Exception as e:
                print(f"Error loading PCB image: {e}")
                pcb_img = np.zeros((100, 100, 3), dtype=np.uint8)  # Placeholder black image
            
            # Plot PCB overlay
            plot_objects["pcb_overlay"] = plot_ax.imshow(
                pcb_img, extent=extent, origin="lower", 
                alpha=alpha_slider.val
            )
            
            # Plot field heatmap - always use consistent vmin/vmax across all scan types
            plot_objects["heatmap"] = plot_ax.imshow(
                Z, extent=extent, origin="lower", cmap="plasma",
                alpha=1.0-alpha_slider.val, vmin=vmin, vmax=vmax
            )
            
            # Remove all existing text elements from the figure
            for txt in fig.texts:
                try:
                    txt.remove()
                except:
                    pass
            
            # COLORBAR HANDLING - PER USER REQUEST:
            # Instead of trying to remove and recreate the colorbar (which causes issues),
            # we'll take a simpler but more reliable approach
            
            # First time only: create the colorbar in a fixed position
            if colorbar_obj is None:
                colorbar_ax = fig.add_axes([0.85, 0.25, 0.03, 0.65])  # Fixed position
                colorbar_obj = fig.colorbar(plot_objects["heatmap"], cax=colorbar_ax)
                colorbar_obj.set_label("Field Strength (dBm)")
                plot_objects["colorbar"] = colorbar_obj
            else:
                # For subsequent updates: just update the existing colorbar if needed
                try:
                    colorbar_obj.update_normal(plot_objects["heatmap"])
                except Exception as e:
                    # If update fails, just continue without updating the colorbar
                    print(f"Notice: Could not update colorbar: {e}")
            
            # Set labels and title
            plot_ax.set_xlabel("X (cm)")
            plot_ax.set_ylabel("Y (cm)")
            plot_ax.set_title(current_title)
            
            # Set fixed position for plot axis
            plot_ax.set_position([0.25, 0.25, 0.55, 0.65])  # Fixed position
            
            # Extract and display metadata
            if isinstance(current_data, dict) and "metadata" in current_data:
                meta = current_data["metadata"]
                meta_text = f"Frequency: {meta.get('center_freq', 0)/1e6:.2f} MHz, "
                meta_text += f"BW: {meta.get('BW', 0)/1e6:.2f} MHz, "
                meta_text += f"Resolution: {meta.get('resolution', 'N/A')} pts/cm"
                
                # Add new text
                fig.text(0.5, 0.02, meta_text, ha='center')
            
            # Make sure current title is displayed in figure title as well
            fig.suptitle(current_title, fontsize=14)
            
            # Reset figure size to original size to prevent shrinking
            fig.set_size_inches(12, 8, forward=True)
            
            # Redraw the figure
            fig.canvas.draw_idle()
            print(f"Plot updated successfully with: {current_title}")
            
        except Exception as e:
            print(f"Error updating plot: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def on_alpha_change(val):
        """Update transparency when slider changes"""
        if plot_objects["pcb_overlay"] is not None:
            plot_objects["pcb_overlay"].set_alpha(val)
        if plot_objects["heatmap"] is not None:
            plot_objects["heatmap"].set_alpha(1.0 - val)
        fig.canvas.draw_idle()
    
    def show_0d(event):
        """Switch to 0° scan view"""
        nonlocal current_file, current_title
        current_file = file_0d
        current_title = "0° Scan"
        fig.current_file = current_file  # Update the figure's current_file
        print(f"Switching to 0° scan view: {file_0d}")  # Debug message
        update_plot()  # Ensure the plot is updated
    
    def show_90d(event):
        """Switch to 90° scan view"""
        nonlocal current_file, current_title
        current_file = file_90d
        current_title = "90° Scan"
        fig.current_file = current_file  # Update the figure's current_file
        print(f"Switching to 90° scan view: {file_90d}")  # Debug message
        update_plot()  # Ensure the plot is updated
    
    def show_45d(event):
        """Switch to 45° scan view"""
        nonlocal current_file, current_title
        if file_45d and os.path.exists(file_45d):
            current_file = file_45d
            current_title = "45° Scan"
            fig.current_file = current_file  # Update the figure's current_file
            print(f"Switching to 45° scan view: {file_45d}")  # Debug message
            update_plot()  # Ensure the plot is updated
    
    def show_combined(event):
        """Switch to combined view"""
        nonlocal current_file, current_title
        current_file = combined_file
        current_title = "Combined Scan"
        fig.current_file = current_file  # Update the figure's current_file
        print(f"Switching to combined scan view: {combined_file}")  # Debug message
        update_plot()  # Ensure the plot is updated
    
    def exit_plot(event):
        """Close the plot window"""
        plt.close(fig)
        print("Plot window closed")
    
    # Create the buttons with updated styles - fix button handlers
    button0 = Button(button0_ax, '0° Scan', color='lightblue')
    button0.on_clicked(show_0d)  # Connect to the correct handler
    
    button90 = Button(button90_ax, '90° Scan', color='lightblue')
    button90.on_clicked(show_90d)  # Connect to the correct handler
    
    button45 = Button(button45_ax, '45° Scan', color='lightblue')
    button45.on_clicked(show_45d)  # Connect to the correct handler
    if not (file_45d and os.path.exists(file_45d)):
        button45.set_active(False)
    
    button_combined = Button(button_combined_ax, 'Combined', color='lightblue')
    button_combined.on_clicked(show_combined)  # Connect to the correct handler
    
    button_current = Button(button_current_ax, 'Show Currents', color='lightcoral')
    button_current.on_clicked(show_currents)
    
    # Add the Done button
    button_done = Button(button_done_ax, 'Done', color='lightgreen')
    button_done.on_clicked(exit_plot)  # Connect to the exit handler
    
    # Add a label for the transparency slider - moved down to match slider
    fig.text(buttons_left_pos + button_width/2, 0.20, 'Adjust Transparency:', ha='center')
    
    # Connect slider to update function
    alpha_slider.on_changed(on_alpha_change)
    
    # Initial plot
    update_plot()
    
    # Show the figure
    plt.show()