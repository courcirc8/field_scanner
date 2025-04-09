# This module handles data storage, retrieval, and processing for scan results.
# It includes functions for:
# 1. Saving scan results to JSON files
# 2. Loading and processing previous scan data
# 3. Combining perpendicular scan orientations into a comprehensive field map
# 4. Providing user interfaces for file selection and scan control
#
# The module is designed to maintain consistent file naming conventions and
# support both single-orientation and dual-orientation (0° and 90°) scans.

import json
import os
import numpy as np  # Import numpy for array operations
import tkinter as tk  # Import tkinter for GUI dialogs

def save_scan_results(filename, results, metadata=None):
    """
    Save scan results to a JSON file with optional metadata.
    
    This function stores both the raw measurement data and metadata about
    the scan conditions, hardware settings, and PCB information. The metadata
    is crucial for interpreting the results later and ensuring reproducibility.
    
    Args:
        filename: Output file path
        results: List of scan points with field strength measurements
        metadata: Dictionary of scan parameters and settings
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

def combine_scans(file_0d, file_90d):
    """
    Combine two perpendicular scans to create a more complete field map.
    
    This function implements the mathematical combination of orthogonal field 
    components. It:
    1. Loads both 0° and 90° scan data
    2. Converts field strength from dBm to linear power
    3. Combines values using sqrt(x²+y²) for amplitude
    4. Converts back to dBm for consistent visualization
    
    This is important for creating a complete picture of the field, particularly
    with linearly polarized antennas that might miss components not aligned with
    the antenna orientation.
    
    Args:
        file_0d: Path to 0° orientation scan results
        file_90d: Path to 90° orientation scan results
        
    Returns:
        Dictionary with combined scan data ready for saving or visualization
    """
    with open(file_0d, 'r') as f:
        data_0d = json.load(f)
    with open(file_90d, 'r') as f:
        data_90d = json.load(f)
        
    # Convert dBm to linear power
    power_0d = np.power(10, np.array([p["field_strength"] for p in data_0d["results"]]) / 10)
    power_90d = np.power(10, np.array([p["field_strength"] for p in data_90d["results"]]) / 10)
    
    # Calculate combined power
    power_combined = np.sqrt(np.power(power_0d, 2) + np.power(power_90d, 2))
    
    # Convert back to dBm
    combined_dbm = 10 * np.log10(power_combined)
    
    # Create combined results
    combined_results = []
    for i, point in enumerate(data_0d["results"]):
        combined_results.append({
            "x": point["x"],
            "y": point["y"],
            "field_strength": float(combined_dbm[i])
        })
    
    return {"metadata": data_0d["metadata"], "results": combined_results}

def display_scan(file_name, pcb_image_path):
    """
    Determine how to display scan results based on available files.
    
    This function handles the logic for determining whether to display:
    1. A single scan file directly
    2. Multiple orientation scans with a selector interface
    
    It also provides helpful debug information about file paths and availability.
    
    Args:
        file_name: Base path for scan results
        pcb_image_path: Path to the PCB image overlay
        
    Returns:
        Tuple of (primary_file, secondary_file, has_both_orientations)
    """
    print(f"Debug: Entered display_scan with file_name: {file_name}")  # Debug message

    # Remove the .json extension if it exists
    base_name = file_name.rsplit('.json', 1)[0]
    file_0d = base_name + '_0d.json'
    file_90d = base_name + '_90d.json'

    print(f"Debug: Checking for _0d.json file: {file_0d}")  # Debug message
    print(f"Debug: Checking for _90d.json file: {file_90d}")  # Debug message

    if os.path.exists(file_0d) and os.path.exists(file_90d):
        # Both _0d and _90d files exist, use angle selector
        print(f"Debug: Found both _0d.json and _90d.json files: {file_0d}, {file_90d}")  # Debug message
        # Don't import plot_with_selector here - this will be called from scanner.py
        return file_0d, file_90d, True  # Return the filenames and a flag indicating both files exist
    elif os.path.exists(file_name):
        # Use the provided file directly
        print(f"Debug: Using provided file: {file_name}")  # Debug message
        # Don't import plot_field here - this will be called from scanner.py
        return file_name, None, False  # Return the filename and a flag indicating only one file exists
    else:
        # Neither the provided file nor _0d/_90d files exist
        print(f"Error: File not found at path: {file_name}")  # Error message
        print(f"Debug: Neither {file_0d} nor {file_90d} exist.")  # Debug message
        return None, None, False  # Return None and a flag indicating no files exist

def get_user_choice(default_output_file):
    """
    Display a popup window to choose between displaying a previous scan or making a new scan.
    
    This function creates a simple GUI that:
    1. Prompts the user to enter a file name
    2. Offers options to view an existing scan or create a new one
    3. Returns the choice and filename for further processing
    
    Args:
        default_output_file: Default file name to show in the entry field
        
    Returns:
        Tuple of (choice, file_name) where choice is either "display" or "scan"
    """
    import tkinter as tk

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

    # Add a text entry for the file name (pre-filled with default_output_file)
    entry = tk.Entry(root, font=("Helvetica", 12), width=40)
    entry.insert(0, default_output_file)  # Pre-fill with the default value
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

def show_rotate_probe_dialog():
    """
    Show a dialog asking the user to rotate the probe by 90 degrees.
    
    This function is called between the 0° and 90° scans to instruct
    the user to physically rotate the probe. The workflow pauses until
    the user confirms the rotation is complete.
    """
    root = tk.Tk()
    root.title("Rotate Probe")
    root.geometry("400x200")

    label = tk.Label(root, text="Please rotate the probe by 90° and press Done.", font=("Helvetica", 12))
    label.pack(pady=30)

    def on_done():
        root.destroy()

    button = tk.Button(root, text="Done", command=on_done, font=("Helvetica", 12))
    button.pack()

    root.mainloop()