import tkinter as tk
import threading
import time
import numpy as np  # Missing import for NumPy
from radio_utils import get_power_dBm  # Missing import for get_power_dBm

def send_gcode_command(command, printer_socket):
    """Send a G-code command to the 3D printer."""
    printer_socket.sendall((command + "\n").encode())
    response = printer_socket.recv(1024).decode()
    return response

def adjust_head(printer, usrp, streamer):
    """
    Adjust the printer head position (X, Y, Z) and allow the user to set the offsets for probing.
    Includes real-time radio power measurement and display.

    :param printer: PrinterConnection object.
    :param usrp: USRP object for power measurement.
    :param streamer: Streamer object for power measurement.
    :return: Final X, Y, Z offsets to be used for probing.
    """
    import tkinter as tk
    import threading
    import time

    # Ensure the printer is in absolute positioning mode
    printer.send_gcode("G90")  # Set absolute positioning

    # Initialize the offsets
    x_offset = 0.0  # X-axis offset in mm
    y_offset = 0.0  # Y-axis offset in mm
    z_height = 97.3  # Start at the initial probing height
    z_lift = 1  # Use the defined lift height
    pcb_corners = {
        "Upper Left": (0, 15.3),
        "Upper Right": (21.65, 15.3),
        "Bottom Left": (0, 0),
        "Bottom Right": (21.65, 0),
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
        x = 4.44  # Convert to mm
        y = 3.7  # Convert to mm
        # Lift the probe to a safe height before moving in X-Y
        printer.move_probe(x=0, y=0, z=z_height + z_lift, feedrate=3000)  # Lift Z first
        printer.move_probe(x=x + x_offset, y=y + y_offset, z=z_height + z_lift, feedrate=3000)  # Travel to the max height position
        printer.move_probe(x=x + x_offset, y=y + y_offset, z=z_height, feedrate=3000)  # Land at max Z

    def measure_power():
        """Measure the radio power and update the label in a thread-safe way."""
        while not done:
            if False:  # Simulate USRP
                power = np.random.uniform(-70, -50)  # Simulated power in dBm
            else:
                try:
                    power = get_power_dBm(usrp, streamer, 76, 100, 400e6, 10e6)
                except Exception as e:
                    print(f"Error measuring field strength: {e}")
                    power = None

            if not done:
                if power is not None:
                    root.after(0, lambda: power_label.config(text=f"Power: {power:.2f} dBm"))  # Thread-safe update
                else:
                    root.after(0, lambda: power_label.config(text="Power: Measurement Failed"))  # Handle None case
            time.sleep(1)  # Update every second

    def done_callback():
        """Return to the correct Z height and exit."""
        nonlocal done
        done = True  # Stop the measure_power thread
        printer.send_gcode(f"G1 Z{z_height:.3f} F3000")  # Return to the correct Z height
        root.quit()  # Safely exit the main loop

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
    root.geometry("600x500")  # Increased height to accommodate all elements

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

    # Start a thread for real-time power updates
    done = False
    threading.Thread(target=measure_power, daemon=True).start()

    # Run the Tkinter event loop
    root.mainloop()

    # Return the final offsets
    return x_offset, y_offset, z_height