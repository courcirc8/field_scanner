"""
3D Printer Communication Module

This module provides functions to initialize and communicate with a 3D printer
using the Duet HTTP API. It supports sending G-code commands over an HTTP
connection.

Implemented Features:
- Connect to the 3D printer via HTTP.
- Send G-code commands to the printer.
- Initialize the printer (e.g., homing axes).
- Move the probe to specific positions.
"""

import requests
import time
from config import DEFAULT_Z, DEBUG_ALL, PRINTER_PASSWORD, PRINTER_WAIT

class PrinterConnection:
    """Class to handle 3D printer connection and control via the Duet HTTP API."""
    
    def __init__(self, ip, port):
        """
        Initialize the printer connection with the given IP and port.
        
        Args:
            ip: IP address of the printer
            port: Port number (usually 80 for HTTP)
        """
        self.ip = ip
        self.port = port
        self.base_url = f"http://{ip}:{port}"
        self.connected = False
        self.session = requests.Session()
        print(f"DEBUG: Initializing PrinterConnection with IP={ip}, PORT={port}")
    
    def connect(self):
        """
        Connect to the 3D printer via HTTP.
        
        Returns:
            bool: True if connection succeeded, False otherwise
        """
        try:
            print(f"DEBUG: Attempting to connect to printer at {self.base_url}")
            # Test connection by sending a simple status request
            status_url = f"{self.base_url}/rr_status?type=1"
            response = self.session.get(status_url, timeout=5)
            
            if response.status_code == 200:
                self.connected = True
                print(f"DEBUG: Successfully connected to printer at {self.base_url}")
                return True
            print(f"ERROR: Failed to connect to printer: {response.status_code} - {response.text}")
            return False
        except Exception as e:
            print(f"ERROR: Failed to connect to printer: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from the printer."""
        self.session.close()
        self.connected = False
        print("DEBUG: Printer connection closed.")
    
    def send_gcode(self, command, debug=True):
        """
        Send a G-code command to the printer via HTTP.
        
        Args:
            command: G-code command string
            debug: Whether to print debug messages
            
        Returns:
            str: Response from the printer, or None if there was an error
        """
        if not self.connected:
            print("ERROR: Not connected to printer. Use connect() first.")
            return None
        
        try:
            if debug:
                print(f"DEBUG: Sending G-code: {command}")
            gcode_url = f"{self.base_url}/rr_gcode?gcode={command}"
            response = self.session.get(gcode_url, timeout=10)
            if response.status_code == 200:
                return response.text.strip()
            print(f"ERROR: Failed to send G-code: {response.status_code} - {response.text}")
            return None
        except Exception as e:
            print(f"ERROR: Failed to send G-code: {e}")
            return None
    
    def move_probe(self, x=None, y=None, z=None, feedrate=3000, debug=True):
        """Move the probe to the specified coordinates."""
        command = "G1"
        if x is not None:
            command += f" X{x:.3f}"
        if y is not None:
            command += f" Y{y:.3f}"
        if z is not None:
            command += f" Z{z:.3f}"
        command += f" F{feedrate}"
        
        if debug:
            print(f"DEBUG: Moving probe to: X={x}, Y={y}, Z={z}, F={feedrate}")
        
        # Step 1: Schedule the movement
        response = self.send_gcode(command, debug=debug)
        
        # Step 2: Wait for movement completion
        self.send_gcode("M400", debug=debug)
        
        # Step 3: Wait for stabilization
        time.sleep(PRINTER_WAIT)
        
        return response
    
    def initialize_printer(self):
        """Initialize the printer (home axes, set units, etc.)."""
        if not self.connected:
            print("ERROR: Not connected to printer. Use connect() first.")
            return False
        
        try:
            # Turn on power supply first
            print("DEBUG: Turning on power supply")
            self.send_gcode("M80")
            time.sleep(1)  # Wait a moment for power to stabilize
            
            # Set to absolute positioning mode
            print("DEBUG: Setting absolute positioning mode")
            self.send_gcode("G90")
            
            # Home all axes
            print("DEBUG: Homing all axes")
            self.send_gcode("G28")
            
            # Set units to millimeters
            print("DEBUG: Setting units to millimeters")
            self.send_gcode("G21")
            
            # Wait for all moves to complete
            print("DEBUG: Waiting for moves to complete")
            self.send_gcode("M400")
            
            # Move to default Z height
            z_height = DEFAULT_Z
            print(f"DEBUG: Moving to default Z height: {z_height} mm")
            self.send_gcode(f"G1 Z{z_height} F3000")
            self.send_gcode("M400")
            print(f"DEBUG: Z-height set to {z_height} mm")
            
            print("DEBUG: Printer initialization completed successfully")
            return True
        except Exception as e:
            print(f"ERROR: Failed to initialize printer: {e}")
            return False

if __name__ == "__main__":
    # IP address and port configuration for standalone testing
    PRINTER_IP = "192.168.1.100"  # Replace with the actual IP address of the 3D printer
    PRINTER_PORT = 80  # Default HTTP port for G-code communication

    # Create a PrinterConnection instance
    printer = PrinterConnection(PRINTER_IP, PRINTER_PORT)

    # Connect to the printer
    if printer.connect():
        # Test printer initialization (homing all axes and calibrating Z-axis)
        if printer.initialize_printer():
            print("Printer initialized successfully.")

        # Test moving the probe to a specific position
        response = printer.move_probe(x=10, y=20, z=5, feedrate=3000)
        if response:
            print(f"Move probe response: {response}")

        # Disconnect from the printer
        printer.disconnect()