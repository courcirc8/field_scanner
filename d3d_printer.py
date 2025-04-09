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
import getpass
import os
from config import DEFAULT_Z, DEBUG_ALL  # Import DEBUG_ALL

class PrinterConnection:
    """Class to handle 3D printer connection and control."""
    
    def __init__(self, ip, port, password=None):
        """
        Initialize the printer connection with the given IP, port, and optional password.
        
        Args:
            ip: IP address of the printer
            port: Port number (usually 23 for Telnet)
            password: Optional password for authentication, if None will try to read from password.txt
        """
        self.ip = ip
        self.port = port
        self.password = password
        # Try to load password from file if not provided
        if self.password is None:
            self.password = self._read_password_from_file()
        self.socket = None
        self.timeout = 5  # Socket timeout in seconds
        self.authenticated = False
        print(f"DEBUG: Initializing PrinterConnection with IP={ip}, PORT={port}")
    
    def _read_password_from_file(self):
        """Read printer password from password.txt file."""
        password_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "password.txt")
        try:
            if os.path.exists(password_file):
                with open(password_file, 'r') as f:
                    password = f.read().strip()
                print("DEBUG: Successfully read password from password.txt")
                return password
            else:
                print("WARNING: password.txt not found, will prompt for password if needed")
                return None
        except Exception as e:
            print(f"ERROR: Failed to read password from file: {e}")
            return None
    
    def connect(self):
        """
        Connect to the 3D printer via Telnet and handle authentication.
        
        Returns:
            bool: True if connection and authentication succeeded, False otherwise
        """
        try:
            print(f"DEBUG: Attempting to connect to printer at {self.ip}:{self.port}")
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)
            self.socket.connect((self.ip, self.port))
            
            # Wait for initial welcome message
            response = self.socket.recv(1024).decode('utf-8', errors='ignore')
            print(f"DEBUG: Received initial response: {response}")
            
            # Check if password authentication is required
            if "password" in response.lower():
                # If no password was provided during initialization, prompt the user
                if self.password is None:
                    self.password = getpass.getpass("Please enter the printer password: ")
                
                # Send the password
                print("DEBUG: Sending password")
                self.socket.sendall(f"{self.password}\n".encode())
                
                # Wait for response after password attempt
                time.sleep(0.5)
                response = self.socket.recv(1024).decode('utf-8', errors='ignore')
                print(f"DEBUG: Authentication response: {response}")
                
                # Check if authentication succeeded
                if "invalid password" in response.lower():
                    print("ERROR: Authentication failed - Invalid password")
                    self.authenticated = False
                    self.socket.close()
                    self.socket = None
                    return False
                else:
                    print("DEBUG: Authentication successful")
                    self.authenticated = True
            else:
                # No password required
                self.authenticated = True
            
            # Send a test command to verify connection
            print("DEBUG: Sending test command (M115)")
            test_response = self.send_gcode("M115")
            
            if test_response and "invalid password" not in test_response.lower():
                print("DEBUG: Successfully connected and authenticated to printer")
                return True
            else:
                print("ERROR: Failed to verify connection with test command")
                self.socket.close()
                self.socket = None
                self.authenticated = False
                return False
                
        except socket.timeout:
            print(f"ERROR: Connection timed out to {self.ip}:{self.port}")
            self.socket = None
            return False
        except ConnectionRefusedError:
            print(f"ERROR: Connection refused to {self.ip}:{self.port}. Make sure the printer is on and Telnet is enabled.")
            self.socket = None
            return False
        except Exception as e:
            print(f"ERROR: Failed to connect to printer: {e}")
            self.socket = None
            return False
    
    def send_gcode(self, command, debug=True):
        """
        Send a G-code command to the printer and return the response.
        
        Args:
            command: G-code command string
            debug: Whether to print debug messages
            
        Returns:
            str: Response from the printer, or None if there was an error
        """
        if not self.socket:
            print("ERROR: Not connected to printer. Use connect() first.")
            return None
        
        if not self.authenticated:
            print("ERROR: Not authenticated to printer. Authentication failed during connect.")
            return None
        
        try:
            if debug:
                print(f"DEBUG: Sending G-code: {command}")
            self.socket.sendall(f"{command}\n".encode())
            time.sleep(0.1)  # Short delay to ensure response is complete
            response = self.socket.recv(1024).decode('utf-8', errors='ignore')
            if debug:
                print(f"DEBUG: Received response: {response}")
            
            # Check if we're still getting authentication errors
            if "invalid password" in response.lower():
                print("WARNING: Command rejected - authentication issue")
                self.authenticated = False
                
            return response
        except Exception as e:
            print(f"ERROR: Failed to send command: {e}")
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
        return self.send_gcode(command, debug=debug)
    
    def initialize_printer(self):
        """Initialize the printer (home axes, set units, etc.)."""
        if not self.socket:
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
            
            # Move to default Z height - ensure this is executed
            z_height = DEFAULT_Z  # Get Z height from config
            print(f"DEBUG: Moving to default Z height: {z_height} mm")
            # Use explicit G1 command to set Z height
            self.send_gcode(f"G1 Z{z_height} F3000")
            # Wait for move to complete
            self.send_gcode("M400")
            print(f"DEBUG: Z-height set to {z_height} mm")
            
            print("DEBUG: Printer initialization completed successfully")
            return True
        except Exception as e:
            print(f"ERROR: Failed to initialize printer: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from the printer."""
        if self.socket:
            try:
                print("DEBUG: Turning off power supply")
                self.send_gcode("M81")  # Turn off power supply before disconnecting
                time.sleep(0.5)  # Give the command time to complete
                
                print("DEBUG: Disconnecting from printer")
                self.socket.close()
                print("DEBUG: Successfully disconnected from printer")
            except Exception as e:
                print(f"ERROR: Error disconnecting from printer: {e}")
            finally:
                self.socket = None

if __name__ == "__main__":
    # IP address and port configuration for standalone testing
    PRINTER_IP = "192.168.1.100"  # Replace with the actual IP address of the 3D printer
    PRINTER_PORT = 23  # Default Telnet port for G-code communication

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