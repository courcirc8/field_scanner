import json
import os
from plot_utils import plot_with_selector, plot_field  # Correct import for plot_with_selector
import tkinter as tk  # Import tkinter for GUI dialogs

def save_scan_results(filename, results, metadata=None):
    """
    Save scan results to a JSON file with optional metadata.

    Args:
        filename (str): The name of the file to save the results.
        results (list): The scan results as a list of dictionaries.
        metadata (dict): Optional metadata to include in the file.
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
    """Combine two perpendicular scans using sqrt(x²+y²)."""
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
    """Display the scan results with or without angle selection."""
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
        plot_with_selector(file_0d, file_90d)
    elif os.path.exists(file_name):
        # Use the provided file directly
        print(f"Debug: Using provided file: {file_name}")  # Debug message
        plot_field(file_name, pcb_image_path)
    else:
        # Neither the provided file nor _0d/_90d files exist
        print(f"Error: File not found at path: {file_name}")  # Error message
        print(f"Debug: Neither {file_0d} nor {file_90d} exist.")  # Debug message

def get_user_choice(default_output_file):
    """Display a popup window to choose between displaying a previous scan or making a new scan."""
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
    """Show a dialog asking the user to rotate the probe."""
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