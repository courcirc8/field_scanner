import os
import tkinter as tk
from plot_utils import plot_field, plot_with_selector
from scan_utils import scan_field
from file_utils import display_scan, get_user_choice
from config import PCB_IMAGE_PATH, OUTPUT_FILE  # Import constants from config

if __name__ == "__main__":
    choice, file_name = get_user_choice(OUTPUT_FILE)
    
    if choice == "display":
        file_to_display, second_file, has_both = display_scan(file_name, PCB_IMAGE_PATH)
        if has_both:
            # If both _0d and _90d files exist, use the angle selector
            plot_with_selector(file_to_display, second_file)
        elif file_to_display:
            # If only one file exists, display it directly
            plot_field(file_to_display, PCB_IMAGE_PATH)
    elif choice == "scan":
        scan_field(file_name)
    else:
        print("No valid choice made. Exiting.")