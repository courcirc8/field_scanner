# This module contains the core scanning functionality for measuring electromagnetic fields.
# It orchestrates the movement of the 3D printer probe and the acquisition of field measurements
# from the USRP radio at each position in the scan grid.
#
# The scanning process follows these steps:
# 1. Connect to the 3D printer and USRP radio
# 2. Allow the user to adjust the probe position
# 3. Scan in a raster pattern at the first orientation (0°)
# 4. Prompt the user to rotate the probe by 90°
# 5. Perform a second scan at the perpendicular orientation (90°)
# 6. Visualize the results

from printer_utils import adjust_head
from radio_utils import measure_field_strength, initialize_radio
from file_utils import save_scan_results
from plot_utils import initialize_plot, update_plot, plot_field, plot_with_selector
from d3d_printer import PrinterConnection
from file_utils import show_rotate_probe_dialog
from config import x_values, y_values, PCB_IMAGE_PATH, CENTER_FREQUENCY, RX_GAIN, nb_avera, EQUIVALENT_BW, PRINTER_IP, PRINTER_PORT  # Import constants from config

def scan_single_orientation(file_name, printer, usrp, streamer, x_offset, y_offset, z_height):
    """
    Perform a single orientation scan across the defined grid.
    
    This function performs a raster scan, moving the probe in a pattern that:
    1. Scans each row from minimum to maximum X
    2. Advances to the next Y position
    3. Shows real-time updates of the scan progress
    
    For each position, it:
    1. Moves the 3D printer head to the specified coordinates
    2. Measures the field strength using the USRP radio
    3. Records the measurement and updates the visualization
    
    Args:
        file_name: Output file for the scan results
        printer: Connected PrinterConnection object
        usrp: Initialized USRP radio object
        streamer: USRP streamer object
        x_offset: X-axis offset for the probe in mm
        y_offset: Y-axis offset for the probe in mm
        z_height: Z-axis height for the probe in mm
    """
    results = []

    try:
        # Initialize the interactive plot
        fig, ax, contour, colorbar = initialize_plot()

        # Main scanning loop
        for y_idx, y in enumerate(y_values):
            for x_idx, x in enumerate(x_values):
                # Move the probe to the (x, y) position using the adjusted Z height
                print(f"Moving probe to X={x:.3f}, Y={y:.3f}, Z={z_height:.3f}")
                printer.move_probe(x=(x * 10) + x_offset, y=(y * 10) + y_offset, z=z_height)  # Convert to mm

                # Measure the field strength using the averaged get_power_dBm with specified averages
                try:
                    field_strength = measure_field_strength(usrp, streamer, RX_GAIN, nb_avera, CENTER_FREQUENCY, EQUIVALENT_BW)
                except Exception as e:
                    print(f"Error measuring field strength: {e}")
                    field_strength = None

                if field_strength is not None:
                    results.append({
                        "x": float(x),
                        "y": float(y),
                        "field_strength": float(field_strength)
                    })
                else:
                    print(f"Warning: No field strength measured at X={x:.3f}, Y={y:.3f}")

            # Update the plot after completing each X line
            contour = update_plot(ax, contour, colorbar, results, x_values, y_values)

    except KeyboardInterrupt:
        print("\nScan interrupted by user. Cleaning up...")
    finally:
        # Save results to a JSON file if any data was collected
        if results:
            metadata = {
                "PCB_SIZE": PCB_SIZE_CM,
                "resolution": RESOLUTION,
                "center_freq": CENTER_FREQUENCY,  # Stored in Hz
                "BW": EQUIVALENT_BW,  # Stored in Hz
                "nb_average": nb_avera
            }

            save_scan_results(file_name, results, metadata)

            # Save the plot as an image file
            plot_image_path = file_name.replace(".json", ".png")
            print(f"Calling plot_field with file: {file_name}")
            plot_field(file_name, PCB_IMAGE_PATH, save_path=plot_image_path)  # Pass PCB_IMAGE_PATH as an argument
            print(f"Plot saved as: {plot_image_path}")
        else:
            print("No results to save.")

        print(f"Calling plot_field with file: {file_name}")
        plot_field(file_name, PCB_IMAGE_PATH)  # Pass PCB_IMAGE_PATH as an argument
        print("plot_field execution completed.")

def scan_field(file_name):
    """
    Perform both 0° and 90° scans to capture the complete field.
    
    This is the main scanning function that:
    1. Initializes hardware connections
    2. Guides the user through the complete measurement process
    3. Performs scans at both orientations
    4. Saves and visualizes the results
    
    The dual orientation approach allows for capturing both components of the
    electromagnetic field, which provides a more complete understanding of field
    distribution and polarization effects.
    
    Args:
        file_name: Base file name for saving results (will be appended with _0d and _90d)
    """
    # Modify file names
    file_0d = file_name.replace('.json', '_0d.json')
    file_90d = file_name.replace('.json', '_90d.json')
        
    # Initialize the radio once
    usrp, streamer = (None, None)
    if not SIMULATE_USRP:
        usrp, streamer = initialize_radio(CENTER_FREQUENCY, RX_GAIN, EQUIVALENT_BW)
        if not usrp or not streamer:
            print("Failed to initialize radio. Exiting scan.")
            return

    # Initialize the 3D printer connection
    printer = PrinterConnection(PRINTER_IP, PRINTER_PORT)
    printer.connect()

    # Terminate if the printer connection fails
    if not printer.socket:
        print("Failed to connect to the 3D printer. Possible authentication issue. Exiting scan.")
        return

    try:
        # Initialize the printer (home axes and calibrate Z-axis)
        printer.initialize_printer()

        # Adjust head position and get the final offsets using graphical adjustment
        print("Starting graphical adjustment of the probe head...")
        x_offset, y_offset, z_height = adjust_head(printer, usrp, streamer)
        print("Graphical adjustment completed.")

        # First scan (0°)
        print("Starting 0° scan...")
        scan_single_orientation(file_0d, printer, usrp, streamer, x_offset, y_offset, z_height)
        
        # Show rotation dialog
        show_rotate_probe_dialog()
        
        # Second scan (90°)
        print("Starting 90° scan...")
        scan_single_orientation(file_90d, printer, usrp, streamer, x_offset, y_offset, z_height)
        
        # Plot results with selector
        plot_with_selector(file_0d, file_90d)

    except KeyboardInterrupt:
        print("\nScan interrupted by user. Cleaning up...")
    finally:
        # Ensure the printer is disconnected properly
        printer.disconnect()