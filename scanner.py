import os
import tkinter as tk
from plot_utils import plot_field, plot_with_selector
from scan_utils import scan_field
from file_utils import display_scan, get_user_choice
from config import PCB_IMAGE_PATH, OUTPUT_FILE  # Import constants from config

# Main entry point for the Field Scanner application
# This module orchestrates the workflow for either displaying existing scans
# or performing new scans of electromagnetic fields on PCBs.
# The system was designed to handle multiple scan orientations (0°, 45°, 90°, etc.)
# to provide a more complete picture of the field distribution.

# IMPORTANT REMARK FOR COPILOT: do not change code if not specifically asked in order to avoid
# unnecessary bugs and errors. The code is already well-structured and modular.
# if you see something to improve, always ask first before making changes. 

if __name__ == "__main__":
    # Present the user with a choice to display existing scan or perform a new one
    choice, file_name = get_user_choice(OUTPUT_FILE)
    
    if choice == "display":
        # Display an existing scan, handling both single files and multiple orientation pairs
        file_to_display, second_file, third_file, has_multiple = display_scan(file_name, PCB_IMAGE_PATH)
        if has_multiple:
            # If multiple orientation files exist, use the angle selector for advanced visualization
            plot_with_selector(file_to_display, second_file, third_file)
        elif file_to_display:
            # If only one file exists, display it directly
            plot_field(file_to_display, PCB_IMAGE_PATH)
    elif choice == "scan":
        # Perform a new field scan using the 3D printer and USRP
        scan_field(file_name)
    else:
        print("No valid choice made. Exiting.")