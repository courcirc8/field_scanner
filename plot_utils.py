import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button
from plot_field import plot_field
import tkinter as tk

def initialize_plot():
    """Initialize the interactive plot."""
    plt.ion()  # Turn on interactive mode
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.set_xlabel("X (cm)")
    ax.set_ylabel("Y (cm)")
    ax.set_title("EM Field Strength (Interactive)")
    ax.set_aspect('equal', adjustable='box')

    # Create an empty 2D array for the initial contour plot
    empty_x = [0, 1]  # Two points for x-axis
    empty_y = [0, 1]  # Two points for y-axis
    empty_z = [[0, 0], [0, 0]]  # 2x2 array of zeros for z-axis
    contour = ax.contourf(empty_x, empty_y, empty_z, cmap="viridis", levels=50, alpha=0.35)
    colorbar = plt.colorbar(contour, ax=ax, label="Field Strength (dBm)")
    return fig, ax, contour, colorbar

def update_plot(ax, contour, colorbar, results, x_values, y_values):
    """Update the plot with new data."""
    x = [point["x"] for point in results]
    y = [point["y"] for point in results]
    field_strength = [point["field_strength"] for point in results]

    unique_x = sorted(set(x_values))
    unique_y = sorted(set(y_values))
    X, Y = plt.meshgrid(unique_x, unique_y)
    Z = [[None for _ in unique_x] for _ in unique_y]

    for point in results:
        xi = unique_x.index(point["x"])
        yi = unique_y.index(point["y"])
        Z[yi][xi] = point["field_strength"]

    for artist in ax.collections:
        artist.remove()

    contour = ax.contourf(X, Y, Z, cmap="viridis", levels=50, alpha=0.35)
    colorbar.update_normal(contour)
    ax.set_xlabel("X (cm)")
    ax.set_ylabel("Y (cm)")
    ax.set_title("EM Field Strength (Interactive)")
    ax.set_aspect('equal', adjustable='box')
    plt.pause(0.1)

    return contour

def plot_with_selector(file_0d, file_90d):
    """Plot results with angle selector."""
    current_plot = {"figure": None, "ax": None}  # Track the current plot

    def plot_orientation(file_path, title):
        # Reuse the same figure and axis if they exist
        if current_plot["figure"] is None or current_plot["ax"] is None:
            current_plot["figure"], current_plot["ax"] = plt.subplots()
        else:
            current_plot["ax"].clear()  # Clear the existing axis

        # Plot the field
        plot_field(file_path, "./pcb_die.jpg", ax=current_plot["ax"])  # Pass the existing axis to plot_field
        current_plot["figure"].suptitle(title, fontsize=14)
        current_plot["figure"].canvas.draw_idle()

    # Ensure only one Tkinter window is created
    if "root" in globals() and globals()["root"] is not None:
        globals()["root"].destroy()

    # Create a simple Tkinter window for angle selection
    root = tk.Tk()
    globals()["root"] = root  # Store the root globally to prevent duplicates
    root.title("Select Scan Orientation")
    root.geometry("300x250")

    tk.Label(root, text="Select Scan Orientation:", font=("Helvetica", 12)).pack(pady=10)
    tk.Button(root, text="0° Scan", font=("Helvetica", 12), command=lambda: plot_orientation(file_0d, "0° Scan")).pack(pady=5)
    tk.Button(root, text="90° Scan", font=("Helvetica", 12), command=lambda: plot_orientation(file_90d, "90° Scan")).pack(pady=5)
    tk.Button(root, text="Combined", font=("Helvetica", 12), command=lambda: plot_orientation(file_0d.replace('_0d.json', '_combined.json'), "Combined Scan")).pack(pady=5)
    tk.Button(root, text="Done", font=("Helvetica", 12), command=lambda: [plt.close('all'), root.destroy()]).pack(pady=5)

    # Display the default 0° plot
    plot_orientation(file_0d, "0° Scan")

    root.mainloop()
    globals()["root"] = None  # Reset the global root after the window is closed