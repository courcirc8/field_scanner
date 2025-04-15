# This module contains the core scanning functionality for measuring electromagnetic fields.
# It orchestrates the movement of the 3D printer probe and the acquisition of field measurements
# from the USRP radio at each position in the scan grid.
#
# The scanning process follows these steps:
# 1. Connect to the 3D printer and USRP radio
# 2. Allow the user to adjust the probe position
# 3. Scan in a raster pattern at the first orientation (0°)
# 4. Prompt the user to rotate the probe by 45°
# 5. Perform a second scan at the diagonal orientation (45°)
# 6. Prompt the user to rotate the probe by 90°
# 7. Perform a third scan at the perpendicular orientation (90°)
# 8. Visualize the results

from printer_utils import adjust_head
from radio_utils import measure_field_strength, initialize_radio
from file_utils import save_scan_results, combine_scans
from plot_utils import initialize_plot, update_plot, plot_field, plot_with_selector
from d3d_printer import PrinterConnection
from file_utils import show_rotate_probe_dialog, show_rotate_probe_dialog_45
from config import (x_values, y_values, PCB_IMAGE_PATH, CENTER_FREQUENCY, RX_GAIN, nb_avera, 
                  EQUIVALENT_BW, PRINTER_IP, PRINTER_PORT, SIMULATE_USRP, PCB_SIZE_CM, 
                  RESOLUTION, DEBUG_ALL, DEBUG_INTERRACTIVE, MOVEMENT_SETTLE_DELAY, BUFFER_FLUSH_COUNT, PRINTER_WAIT, PRINTER_WAIT_LINE)
import matplotlib.pyplot as plt
import time
import gc

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
    first_line_complete = False
    power_values = []
    fig = None  # Store the figure reference for later closing

    try:
        # Initialize the interactive plot with a more descriptive title
        # Only create interactive plot if DEBUG_INTERRACTIVE is True
        if DEBUG_INTERRACTIVE:
            fig, ax, contour, colorbar = initialize_plot()
            orientation = "0°"
            if "_45d" in file_name:
                orientation = "45°"
            elif "_90d" in file_name:
                orientation = "90°"
            fig.canvas.manager.set_window_title(f"Measuring board with {orientation} probe angle")
            print(f"Interactive plot initialized for {orientation} orientation")
        
        # Main scanning loop
        for y_idx, y in enumerate(y_values):
            # Wait for PRINTER_WAIT_LINE at the start of each new line
            time.sleep(PRINTER_WAIT_LINE)
            
            # Perform an additional RSSI measurement at the start of the line
            try:
                initial_field_strength = measure_field_strength(
                    streamer, RX_GAIN, debug=(DEBUG_ALL or DEBUG_INTERRACTIVE)
                )
                if initial_field_strength is not None:
                    print(f"DEBUG: Initial RSSI at start of line {y_idx+1}/{len(y_values)} (y={y:.3f}): {initial_field_strength:.2f} dBm")
            except Exception as e:
                if DEBUG_ALL or DEBUG_INTERRACTIVE:
                    print(f"Error measuring initial RSSI at start of line {y_idx+1}: {e}")

            for x_idx, x in enumerate(x_values):
                # Step 1: Schedule the movement
                printer.move_probe(
                    x=(x * 10) + x_offset,
                    y=(y * 10) + y_offset,
                    z=z_height,
                    debug=(DEBUG_ALL or DEBUG_INTERRACTIVE or not first_line_complete)
                )
                
                # Step 2: Wait for movement completion
                printer.send_gcode("M400")
                if DEBUG_ALL or DEBUG_INTERRACTIVE:
                    print("Waiting for printer movement to complete (M400)")
                
                # Step 3: Restart RSSI (flush previous readings)
                if not SIMULATE_USRP and streamer is not None:
                    for _ in range(BUFFER_FLUSH_COUNT):
                        try:
                            # Explicitly flush the buffer before measurement
                            _ = measure_field_strength(streamer, RX_GAIN, debug=False)
                        except Exception as e:
                            if DEBUG_ALL or DEBUG_INTERRACTIVE:
                                print(f"Buffer flush attempt failed: {e}")
                
                # Step 4: Wait for stabilization
                time.sleep(PRINTER_WAIT)
                
                # Step 5: Perform RSSI measurement
                try:
                    field_strength = measure_field_strength(
                        streamer, RX_GAIN,
                        debug=(DEBUG_ALL or DEBUG_INTERRACTIVE or not first_line_complete)
                    )
                    if field_strength is not None:
                        power_values.append(field_strength)
                        if DEBUG_INTERRACTIVE:
                            print(f"Measured field strength: {field_strength:.2f} dBm")
                except Exception as e:
                    if DEBUG_ALL or DEBUG_INTERRACTIVE or not first_line_complete:
                        print(f"Error measuring field strength: {e}")
                    field_strength = None

                if field_strength is not None:
                    results.append({
                        "x": float(x),
                        "y": float(y),
                        "field_strength": float(field_strength)
                    })
                else:
                    if DEBUG_ALL or DEBUG_INTERRACTIVE or not first_line_complete:
                        print(f"Warning: No field strength measured at X={x:.3f}, Y={y:.3f}")

            # Update the plot after completing each X line, but only if interactive mode is enabled
            if DEBUG_INTERRACTIVE and fig is not None:
                contour = update_plot(ax, contour, colorbar, results, x_values, y_values)
                print(f"Updated plot after completing row {y_idx+1}/{len(y_values)} (y={y:.3f})")
            elif DEBUG_ALL or not first_line_complete:
                print(f"Completed row {y_idx+1}/{len(y_values)} (y={y:.3f})")
            
            # Calculate and display average power after first line is complete
            if not first_line_complete:
                first_line_complete = True
                if power_values:
                    avg_power = sum(power_values) / len(power_values)
                    print(f"\n=== SCAN PROGRESS ===")
                    print(f"First line completed.")
                    print(f"Average power: {avg_power:.2f} dBm")
                    print(f"Number of valid measurements: {len(power_values)}/{len(x_values)}")
                    print(f"Min power: {min(power_values):.2f} dBm, Max power: {max(power_values):.2f} dBm")
                    if not DEBUG_INTERRACTIVE and not DEBUG_ALL:
                        print(f"=== DEBUG OUTPUT REDUCED ===\n")
                else:
                    print("\n=== WARNING: NO VALID POWER MEASUREMENTS IN FIRST LINE ===")
                    print("Check USRP connection, gain settings, and transmitter status")
                    if not DEBUG_INTERRACTIVE and not DEBUG_ALL:
                        print("=== DEBUG OUTPUT REDUCED ===\n")

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
            print(f"Scan results saved to {file_name}")
        else:
            print("No results to save.")
            
        # Close the plot window if it was created
        if fig is not None and DEBUG_INTERRACTIVE:
            plt.close(fig)
            print("Closed interactive scan window")

def scan_field(file_name):
    """
    Perform both 0°, 45°, and 90° scans to capture the complete field.
    
    This is the main scanning function that:
    1. Initializes hardware connections
    2. Guides the user through the complete measurement process
    3. Performs scans at three orientations (0°, 45°, and 90°)
    4. Saves and visualizes the results
    
    The multi-orientation approach allows for capturing more components of the
    electromagnetic field, which provides a more complete understanding of field
    distribution and polarization effects.
    
    Args:
        file_name: Base file name for saving results (will be appended with _0d, _45d, and _90d)
    """
    # Modify file names
    file_0d = file_name.replace('.json', '_0d.json')
    file_45d = file_name.replace('.json', '_45d.json')
    file_90d = file_name.replace('.json', '_90d.json')
    file_combined = file_name.replace('.json', '_combined.json')
        
    # Initialize the radio once
    usrp, streamer = (None, None)
    if not SIMULATE_USRP:
        print("DEBUG: Initializing radio hardware...")
        usrp, streamer = initialize_radio(CENTER_FREQUENCY, RX_GAIN, EQUIVALENT_BW)
        print(f"DEBUG: Radio initialization returned: USRP={usrp is not None}, streamer={streamer is not None}")
        if not usrp or not streamer:
            print("Failed to initialize radio. Exiting scan.")
            return

    # Initialize the 3D printer connection
    print("DEBUG: Connecting to 3D printer...")
    printer = PrinterConnection(PRINTER_IP, PRINTER_PORT)  # No password argument - will load from file
    connection_status = printer.connect()

    # Terminate if the printer connection fails
    if not connection_status or not printer.connected:  # Updated to check `printer.connected`
        print("Failed to connect to the 3D printer. Check IP address, port, and password. Exiting scan.")
        return

    try:
        # Initialize the printer (home axes and calibrate Z-axis)
        printer.initialize_printer()

        # Add a small delay before starting GUI operations
        time.sleep(1.0)  # Allow any previous Tkinter resources to be cleaned up

        # Adjust head position and get the final offsets using graphical adjustment
        print("Starting graphical adjustment of the probe head...")
        x_offset, y_offset, z_height = adjust_head(printer, usrp, streamer)
        print("Graphical adjustment completed.")
        
        # Ensure the measure_power thread is terminated before proceeding
        time.sleep(0.5)  # Allow the thread to fully terminate
        
        # Add a delay after GUI operations before starting the next GUI
        # This helps ensure Tkinter resources are properly cleaned up
        time.sleep(1.0)
        
        # Clear any remaining Tkinter resources
        gc.collect()
        
        # First scan (0°)
        print("Starting 0° scan...")
        scan_single_orientation(file_0d, printer, usrp, streamer, x_offset, y_offset, z_height)
        
        # Add delay between GUI operations
        time.sleep(0.5)
        
        # Show rotation dialog for 45° - Corrected sequence
        print("Starting 45° scan next...")
        show_rotate_probe_dialog_45()
        
        # Add delay between GUI operations
        time.sleep(0.5)
        
        # Second scan (45°) - Moved this to be second in sequence
        print("Starting 45° scan...")
        scan_single_orientation(file_45d, printer, usrp, streamer, x_offset, y_offset, z_height)
        
        # Add delay between GUI operations
        time.sleep(0.5)
        
        # Show rotation dialog for 90° - Now third
        print("Starting 90° scan next...")
        show_rotate_probe_dialog()  # 90° rotation dialog
        
        # Add delay between GUI operations
        time.sleep(0.5)
        
        # Third scan (90°) - Move to be last in sequence
        print("Starting 90° scan...")
        scan_single_orientation(file_90d, printer, usrp, streamer, x_offset, y_offset, z_height)
        
        # Generate and save the combined scan results (using only 0° and 90° data)
        print("Generating combined results from 0° and 90° scans...")
        data_combined = combine_scans(file_0d, file_90d)
        save_scan_results(file_combined, data_combined["results"], data_combined["metadata"])
        print(f"Combined results saved to {file_combined}")
        
        # Display the complete scan results
        print("Displaying the complete scan results...")
        plot_with_selector(file_0d, file_90d, file_45d)

    except KeyboardInterrupt:
        print("\nScan interrupted by user. Cleaning up...")
    finally:
        # Ensure the printer is disconnected properly
        printer.disconnect()