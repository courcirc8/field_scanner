# Near-Field EM Scanner

This project implements a near-field scanner to visualize the electromagnetic (EM) field strength at a given frequency. The system uses a 3D printer to move a probe across a grid and a software-defined radio (SDR) to measure the EM field strength at each point. The results are saved in a JSON file and can be visualized using a separate script.

## Features

- **3D Printer Control**: The 3D printer (using RepRap Duet 2) is controlled via G-code commands over Ethernet.
- **EM Field Measurement**: The EM field strength is measured using a USRP B205 SDR.
- **Simulation Mode**: Both the 3D printer and USRP can be simulated for testing purposes.
- **Data Visualization**: A separate script (`plot_field.py`) is used to visualize the scanned field data.
- **Configurable Parameters**: Frequency, grid size, resolution, and other parameters can be easily adjusted.
- **Interactive PCB Height Adjustment**: A graphical interface allows users to adjust the Z height of the probe before scanning.
- **Perimeter Adjustment Loop**: The 3D printer cycles around the PCB perimeter until the user confirms the placement via a graphical "Done" button.

## Project Structure

- `scanner.py`: Main script to perform the scanning process and save results to a JSON file.
- `d3d_printer.py`: Module for 3D printer communication and control.
- `plot_field.py`: Script to visualize the scanned field data (not included in the provided code).
- `password.txt`: File containing the 3D printer password (excluded from version control via `.gitignore`).

## How It Works

1. **Grid Generation**: A scanning grid is generated based on the PCB size and resolution.
2. **Probe Movement**: The 3D printer moves the probe to each point on the grid.
3. **Field Measurement**: The EM field strength is measured at each point using the USRP B205 or simulated data.
4. **Interactive PCB Adjustment**:
   - The user adjusts the PCB height using a graphical interface.
   - The 3D printer cycles around the PCB perimeter until the user confirms the placement.
5. **Data Storage**: The results are saved in a JSON file for further analysis or visualization.

## Requirements

- Python 3.6+
- Libraries: `numpy`, `json`, `socket`, `matplotlib`, `tkinter`
- Optional: `uhd` library for USRP B205 support
- A 3D printer with Ethernet connectivity (e.g., RepRap Duet 2)
- A USRP B205 SDR for field measurements

## Configuration

The following parameters can be configured in `scanner.py`:

- **Frequency**: Set the frequency of interest (default: 400 MHz).
- **Grid Size**: Define the size of the scanning grid.
- **PCB Size**: Specify the size of the PCB in centimeters.
- **Resolution**: Set the resolution in points per millimeter.
- **Simulation Mode**: Enable or disable simulation for the printer and USRP.

## Usage

1. **Run the Scanner**:
   ```bash
   python scanner.py
   ```
2. **Adjust PCB Height**:
   - Use the graphical interface to adjust the Z height of the probe.
   - Press "Done" when the height is set correctly.
3. **Confirm PCB Placement**:
   - The 3D printer will cycle around the PCB perimeter.
   - Press the "Done" button in the graphical interface to confirm the placement.
4. **View Results**:
   - The scanned data is saved in `scan_results.json`.
   - Use `plot_field.py` to visualize the results.