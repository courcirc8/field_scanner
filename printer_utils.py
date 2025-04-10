# This module contains utilities for controlling the 3D printer used as a positioning system.
# It provides functions for sending G-code commands and a graphical interface for
# precisely adjusting the probe position over the PCB.
#
# The key challenge addressed here is providing precise manual positioning control
# while simultaneously displaying real-time signal strength from the USRP.

import tkinter as tk
import threading
import time
import numpy as np
import uhd  # Add uhd import here
from radio_utils import get_power_dBm
from config import RX_GAIN, DEFAULT_Z, PCB_SIZE_CM, MAX_HEIGHT_COMPONENT_X_MM, MAX_HEIGHT_COMPONENT_Y_MM  # Import additional constants

def send_gcode_command(command, printer_socket):
    """
    Send a G-code command to the 3D printer and retrieve the response.
    
    This is a low-level function that handles the communication protocol
    with the 3D printer's control interface.
    
    Args:
        command: G-code command string
        printer_socket: Connected socket to the printer
        
    Returns:
        Response string from the printer
    """
    printer_socket.sendall((command + "\n").encode())
    response = printer_socket.recv(1024).decode()
    return response

def adjust_head(printer, usrp, streamer):
    """
    Interactive graphical tool for precise probe positioning.
    
    This function creates a GUI with the following features:
    1. Buttons to move to pre-defined PCB corners
    2. Fine control of X, Y, and Z positioning
    3. Real-time display of signal strength to aid positioning
    4. Visualization of the current position
    
    The function provides all the tools necessary to align the probe with 
    the PCB before starting a scan. It's a critical step for ensuring accurate
    measurements, especially when scanning at different orientations that
    require probe rotation.
    
    Args:
        printer: Connected PrinterConnection object
        usrp: Initialized USRP radio object
        streamer: USRP streamer object
        
    Returns:
        Tuple of (x_offset, y_offset, z_height) representing the final probe position
    """
    # Ensure the printer is in absolute positioning mode
    printer.send_gcode("G90")  # Set absolute positioning

    # Initialize the offsets
    x_offset = 0.0  # X-axis offset in mm
    y_offset = 0.0  # Y-axis offset in mm
    z_height = DEFAULT_Z  # Use the default Z height from config.py instead of hardcoded value
    z_lift = 1  # Use the defined lift height
    
    # Use PCB size from config.py, converting from cm to mm
    pcb_corners = {
        "Upper Left": (0, PCB_SIZE_CM[1] * 10),
        "Upper Right": (PCB_SIZE_CM[0] * 10, PCB_SIZE_CM[1] * 10),
        "Bottom Left": (0, 0),
        "Bottom Right": (PCB_SIZE_CM[0] * 10, 0),
    }

    def move_to_corner(corner):
        """Move the probe to a specified corner."""
        x, y = pcb_corners[corner]
        # Lift the probe to a safe height before moving in X-Y
        printer.move_probe(x=0, y=0, z=z_height + z_lift, feedrate=3000)  # Lift Z first
        printer.move_probe(x=x + x_offset, y=y + y_offset, z=z_height + z_lift, feedrate=3000)  # Travel to the corner
        printer.move_probe(x=x + x_offset, y=y + y_offset, z=z_height - z_lift, feedrate=3000)  # Lower Z to probing height

    def move_to_max_height():
        """Move the probe to the highest component position."""
        x = MAX_HEIGHT_COMPONENT_X_MM  # Use constant from config.py
        y = MAX_HEIGHT_COMPONENT_Y_MM  # Use constant from config.py
        # Lift the probe to a safe height before moving in X-Y
        printer.move_probe(x=0, y=0, z=z_height + z_lift, feedrate=3000)  # Lift Z first
        printer.move_probe(x=x + x_offset, y=y + y_offset, z=z_height + z_lift, feedrate=3000)  # Travel to the max height position
        printer.move_probe(x=x + x_offset, y=y + y_offset, z=z_height, feedrate=3000)  # Land at max Z

    def measure_power():
        """Measure the radio power and update the label in a thread-safe way."""
        while not done:
            try:
                # Store measurements locally first
                local_power = None
                
                # Only continue if not done to prevent accessing closed resources
                if done:
                    break
                
                if False:  # Simulate USRP
                    local_power = np.random.uniform(-70, -50)  # Simulated power in dBm
                else:
                    # First make sure we're issuing a stream command
                    stream_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.num_done)
                    stream_cmd.num_samps = 1024
                    stream_cmd.stream_now = True
                    streamer.issue_stream_cmd(stream_cmd)
                    
                    # Then measure power
                    local_power = get_power_dBm(streamer, RX_GAIN)
                    
                    # Debug output for successful measurement
                    if local_power is not None and not np.isnan(local_power):
                        print(f"DEBUG: Measured power: {local_power:.2f} dBm")
                
                # IMPORTANT: Check if 'done' before updating UI to prevent crashes
                # This is critical for thread safety
                if not done and root.winfo_exists():
                    # Use root.after with a local copy of the power value
                    # This schedules the UI update to happen in the main thread
                    power_val = local_power  # Make a local copy for the lambda
                    if power_val is not None and not np.isnan(power_val):
                        root.after(0, lambda p=power_val: power_label.config(text=f"Power: {p:.2f} dBm"))
                    else:
                        root.after(0, lambda: power_label.config(text="Power: Measurement Failed"))
            except Exception as e:
                print(f"ERROR in measurement thread: {e}")
                # If we get an exception, add a small delay to prevent tight loops
                time.sleep(0.1)
            
            # Sleep to avoid tight loop
            time.sleep(1)
    
    def done_callback():
        """Return to the correct Z height and exit."""
        nonlocal done
        # Signal the thread to stop before destroying the window
        done = True
        time.sleep(0.3)  # Give the thread more time to completely exit
        
        # Move to final height - do this before destroying the window
        try:
            printer.send_gcode(f"G1 Z{z_height:.3f} F3000")
            # Safely destroy AFTER all operations completed
            safe_destroy()
        except Exception as e:
            print(f"ERROR in done_callback: {e}")
            safe_destroy()
    
    def safe_destroy():
        """Safely destroy the window from the main thread.
        This function is critical for preventing Tcl_AsyncDelete errors.
        """
        try:
            # Schedule destruction with a small delay to allow other operations to complete
            root.after(200, lambda: actually_destroy())
        except Exception as e:
            print(f"ERROR scheduling window destruction: {e}")
    
    def actually_destroy():
        """Actually perform the window destruction after all operations are complete."""
        try:
            root.quit()
            root.destroy()
        except Exception as e:
            print(f"ERROR during window cleanup: {e}")

    def adjust_z(delta):
        """Adjust the Z height by a specified delta without moving X or Y."""
        nonlocal z_height
        z_height += delta
        printer.send_gcode(f"G1 Z{z_height:.3f} F3000")  # Only adjust Z
        z_label.config(text=f"Defined Z: {z_height:.2f} mm")  # Update the Z reference display

    def adjust_x(delta):
        """Adjust the X offset."""
        nonlocal x_offset
        x_offset += delta
        printer.send_gcode(f"G1 X{x_offset:.3f} F3000")  # Move X axis
        x_label.config(text=f"X Offset: {x_offset:.2f} mm")  # Update the X offset display

    def adjust_y(delta):
        """Adjust the Y offset."""
        nonlocal y_offset
        y_offset += delta
        printer.send_gcode(f"G1 Y{y_offset:.3f} F3000")  # Move Y axis
        y_label.config(text=f"Y Offset: {y_offset:.2f} mm")  # Update the Y offset display

    # Create the Tkinter window
    root = tk.Tk()
    root.title("Adjust Head Position")
    root.geometry("600x560")  # Increased height to accommodate the new message

    # Add corner buttons
    tk.Button(root, text="Upper Left", command=lambda: move_to_corner("Upper Left")).place(x=50, y=50)
    tk.Button(root, text="Upper Right", command=lambda: move_to_corner("Upper Right")).place(x=250, y=50)
    tk.Button(root, text="Bottom Left", command=lambda: move_to_corner("Bottom Left")).place(x=50, y=250)
    tk.Button(root, text="Bottom Right", command=lambda: move_to_corner("Bottom Right")).place(x=250, y=250)

    # Add "Max Height" button
    tk.Button(root, text="Max Height", command=move_to_max_height).place(x=150, y=150)

    # Add Z adjustment buttons on the right
    tk.Button(root, text="+1 cm", command=lambda: adjust_z(10)).place(x=500, y=100)
    tk.Button(root, text="+1 mm", command=lambda: adjust_z(1)).place(x=500, y=150)
    tk.Button(root, text="+0.1 mm", command=lambda: adjust_z(0.1)).place(x=500, y=200)
    tk.Button(root, text="-0.1 mm", command=lambda: adjust_z(-0.1)).place(x=500, y=250)
    tk.Button(root, text="-1 mm", command=lambda: adjust_z(-1)).place(x=500, y=300)
    tk.Button(root, text="-1 cm", command=lambda: adjust_z(-10)).place(x=500, y=350)

    # Add X-Y adjustment buttons in a cross layout
    tk.Button(root, text="+Y", command=lambda: adjust_y(0.1)).place(x=400, y=150)  # Above
    tk.Button(root, text="-Y", command=lambda: adjust_y(-0.1)).place(x=400, y=250)  # Below
    tk.Button(root, text="+X", command=lambda: adjust_x(0.1)).place(x=450, y=200)  # Right
    tk.Button(root, text="-X", command=lambda: adjust_x(-0.1)).place(x=350, y=200)  # Left

    # Add a "Done" button
    tk.Button(root, text="Done", command=done_callback).place(x=250, y=450)  # Moved down to avoid overlap

    # Add a label to display the measured power
    power_label = tk.Label(root, text="Power: -- dBm", font=("Helvetica", 14))
    power_label.place(x=100, y=400)  # Moved down to avoid overlap with the "Done" button

    # Add labels to display the defined offsets
    z_label = tk.Label(root, text=f"Defined Z: {z_height:.2f} mm", font=("Helvetica", 14))
    z_label.place(x=100, y=20)
    x_label = tk.Label(root, text=f"X Offset: {x_offset:.2f} mm", font=("Helvetica", 14))
    x_label.place(x=400, y=20)
    y_label = tk.Label(root, text=f"Y Offset: {y_offset:.2f} mm", font=("Helvetica", 14))
    y_label.place(x=400, y=60)

    # Add rotation instructions at the top
    rotation_label = tk.Label(root, text="Please position probe at 0° angle position", 
                            font=("Helvetica", 14), fg="blue")
    rotation_label.place(x=120, y=480)  # Place below existing elements

    # Start a thread for real-time power updates - make sure it's a daemon thread
    # Daemon threads automatically terminate when the main program exits
    done = False
    power_thread = threading.Thread(target=measure_power, daemon=True)
    power_thread.start()

    # Start the GUI event loop last to ensure everything is ready
    root.mainloop()
    
    # Ensure thread cleanup before returning
    # This is VERY important to avoid Tcl_AsyncDelete errors
    done = True
    try:
        # Give the thread more time to fully exit
        time.sleep(0.5)
        
        # Ensure all pending Tkinter events are processed
        while root.winfo_exists():
            try:
                root.update()
            except:
                break
            time.sleep(0.01)
        
        # Forcefully destroy any remaining Tk objects
        try:
            root.quit()
            root.destroy()
        except:
            pass
            
        # Force Python's garbage collection to clean up Tkinter objects
        import gc
        gc.collect()
        
        # Clear any remaining Tcl interpreter resources
        # This helps prevent cross-thread Tcl interpreter issues
        try:
            from tkinter import _tkinter
            _tkinter.create()
        except:
            pass
        
    except Exception as e:
        print(f"ERROR during thread cleanup: {e}")
    
    # Return the final offsets
    return x_offset, y_offset, z_height