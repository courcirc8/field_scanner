import os
import tkinter as tk
from plot_utils import plot_field, plot_with_selector
from scan_utils import scan_field
from file_utils import display_scan, get_user_choice
from config import PCB_IMAGE_PATH, OUTPUT_FILE  # Import constants from config

if __name__ == "__main__":
    choice, file_name = get_user_choice(OUTPUT_FILE)
    
    if choice == "display":
        display_scan(file_name, PCB_IMAGE_PATH)
    elif choice == "scan":
        scan_field(file_name)
    else:
        print("No valid choice made. Exiting.")