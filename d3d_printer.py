"""
3D Printer Communication Module

This module provides functions to initialize and communicate with a 3D printer
running RepRap Duet 2 firmware. It supports sending G-code commands over a Telnet
connection (Ethernet).

Implemented Features:
- Connect to the 3D printer via Telnet.
- Send G-code commands to the printer.
- Initialize the printer (e.g., homing axes).
- Move the probe to specific positions.

Missing Features:
- Error handling for connection failures.
- Support for USB communication.
"""

import socket
import time

class PrinterConnection:
    FAST_Z_MOVE = 100  # Fast Z move height in mm
    NOZZLE_HEIGHT = 3  # Nozzle height in mm for calibration

    def __init__(self, ip, port=23, password_file="password.txt"):
        """
        Initialize the PrinterConnection object.

        :param ip: IP address of the 3D printer.
        :param port: Port for Telnet communication (default: 23).
        :param password_file: Path to the file containing the printer password.
        """
        self.ip = ip
        self.port = port
        self.socket = None
        self.password = self._load_password(password_file)

    def _load_password(self, password_file):
        """Load the password from a file."""
        try:
            with open(password_file, "r") as file:
                return file.read().strip()
        except Exception as e:
            print(f"Error loading password from {password_file}: {e}")
            return None

    def connect(self):
        """Establish a Telnet connection to the 3D printer and send the password."""
        if not self.password:
            print("Password not loaded. Cannot connect to the printer.")
            return
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.ip, self.port))
            print(f"Connected to 3D printer at {self.ip}:{self.port}")

            # Wait for the password prompt
            response = self.socket.recv(1024).decode()
            print(f"Received: {response.strip()}")

            if "Please enter your password:" in response:
                # Send the password
                self.socket.sendall((self.password + "\n").encode())
                response = self.socket.recv(1024).decode()
                print(f"Sent password, Received: {response.strip()}")

                if "log in successful" in response.lower() or "ok" in response.lower():
                    print("Password accepted. Connection established.")
                else:
                    raise ValueError("Failed to authenticate with the printer. Check the password.")
            else:
                raise ValueError("Unexpected response from the printer. Authentication failed.")
        except Exception as e:
            print(f"Failed to connect to 3D printer: {e}")
            self.socket = None

    def disconnect(self):
        """Close the Telnet connection to the 3D printer."""
        if self.socket:
            try:
                # Optional: Home all axes before disconnecting
                print("Homing all axes before disconnecting...")
                self.send_gcode("G28")  # G28 is the G-code for homing all axes

                # Turn off the motors
                print("Turning off motors...")
                self.send_gcode("M84")  # M84 is the G-code to disable motors
            except Exception as e:
                print(f"Error during disconnect: {e}")
            finally:
                # Close the connection
                self.socket.close()
                print("Disconnected from 3D printer.")
                self.socket = None

    def send_gcode(self, command):
        """
        Send a G-code command to the 3D printer.

        :param command: G-code command as a string.
        :return: Response from the printer.
        """
        if not self.socket:
            print("Printer is not connected.")
            return None
        try:
            self.socket.sendall((command + "\n").encode())  # Send the G-code command
            response = self.socket.recv(1024).decode()  # Wait for the printer's response
            print(f"Sent: {command}, Received: {response.strip()}")
            return response.strip()
        except Exception as e:
            print(f"Error sending G-code command: {e}")
            return None

    def initialize_printer(self):
        """
        Initialize the 3D printer by turning on the motors, homing all axes, 
        and calibrating the Z-axis using a magnetic probe.

        :return: Response from the printer.
        """
        print("Initializing printer (turning on motors, homing all axes, and calibrating Z-axis)...")
        
        # Turn on the motors
        response_m80 = self.send_gcode("M80")  # M80 is the G-code to turn on motors
        if response_m80:
            print(f"Motors turned on: {response_m80}")
        
        # Home all axes
        response_g28 = self.send_gcode("G28")  # G28 is the G-code for homing all axes
        if response_g28:
            print(f"Axes homed: {response_g28}")
        
        # Fast move close to the bottom
        response_fast_z = self.send_gcode(f"G1 Z{self.FAST_Z_MOVE} F3000")
        if response_fast_z:
            print(f"Fast Z move response: {response_fast_z}")
        
        # Calibrate Z-axis using magnetic probe
        #response_g30 = self.send_gcode("G30")  # Removed Z parameter for compatibility
        #if response_g30:
        #    print(f"Z-axis calibration response: {response_g30}")
        
        return response_fast_z

    def move_probe(self, x, y, z=None, feedrate=3000):
        """
        Move the probe to a specific (X, Y, Z) position and wait for the movement to complete.

        :param x: X-coordinate in mm.
        :param y: Y-coordinate in mm.
        :param z: Z-coordinate in mm (optional).
        :param feedrate: Movement speed in mm/min (default: 3000).
        :return: Response from the printer after ensuring the movement is complete.
        """
        gcode_command = f"G1 X{x:.3f} Y{y:.3f}"
        if z is not None:
            gcode_command += f" Z{z:.3f}"
        gcode_command += f" F{feedrate}"
        
        # Send the movement command
        response = self.send_gcode(gcode_command)
        
        # Ensure the movement is complete
        self.send_gcode("M400")  # Wait for all movements to finish
        
        return response

if __name__ == "__main__":
    # IP address and port configuration for standalone testing
    PRINTER_IP = "192.168.1.100"  # Replace with the actual IP address of the 3D printer
    PRINTER_PORT = 23  # Default Telnet port for G-code communication

    # Create a PrinterConnection instance
    printer = PrinterConnection(PRINTER_IP, PRINTER_PORT)

    # Connect to the printer
    printer.connect()

    # Test printer initialization (homing all axes and calibrating Z-axis)
    response = printer.initialize_printer()
    if response:
        print(f"Printer initialization response: {response}")

    # Test moving the probe to a specific position
    response = printer.move_probe(x=10, y=20, z=5, feedrate=3000)
    if response:
        print(f"Move probe response: {response}")

    # Disconnect from the printer
    printer.disconnect()