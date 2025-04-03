"""
USRP Power Measurement Module

This module provides functions to initialize a USRP (Universal Software Radio Peripheral) 
and measure the input power of received signals. It is used as part of the field scanner 
to estimate the EM field strength at each point on the PCB grid.

Implemented Features:
- USRP initialization with configurable frequency, gain, and bandwidth.
- Frame reception and power estimation in dBm.
- Error handling for USRP initialization and frame reception.

Missing Features:
- Support for multiple channels or advanced USRP configurations.
- Integration with other SDR platforms for broader compatibility.
- Improved error handling and logging for debugging.
"""

import uhd
import numpy as np
import time
import matplotlib.pyplot as plt
from collections import deque
from matplotlib.animation import FuncAnimation

def initialize_radio(freq, gain, rx_bw):
    """
    Initialize the USRP radio with the given parameters.
    
    Args:
        freq (float): Center frequency in Hz.
        gain (float): Receiver gain in dB.
        rx_bw (float): Receiver bandwidth in Hz.
    
    Returns:
        tuple: (usrp, streamer) where `usrp` is the initialized USRP object and `streamer` is the RX streamer.
    """
    try:
        # Initialize USRP
        usrp = uhd.usrp.MultiUSRP()
        print("USRP successfully connected.")

        # Configure USRP settings
        usrp.set_rx_freq(freq, 0)  # Set center frequency
        usrp.set_rx_gain(gain, 0)  # Set gain
        usrp.set_rx_bandwidth(rx_bw, 0)  # Set receiver bandwidth

        # Display frequency and bandwidth in MHz
        print(f"Center Frequency: {freq / 1e6:.2f} MHz")
        print(f"Bandwidth: {rx_bw / 1e6:.2f} MHz")

        # Print USRP info
        print(usrp.get_usrp_rx_info())

        # Set up the stream
        st_args = uhd.usrp.StreamArgs("fc32", "sc16")
        st_args.channels = [0]  # Explicitly set the channel
        streamer = usrp.get_rx_stream(st_args)

        return usrp, streamer
    except Exception as e:
        print(f"Error initializing USRP: {e}")
        return None, None

def receive_frame(streamer):
    """
    Receive a frame of samples.

    Args:
        streamer: The RX streamer object.

    Returns:
        numpy.ndarray: Received frame as a numpy array.
    """
    try:
        # Prepare receive buffer
        recv_buffer = np.zeros((1, streamer.get_max_num_samps()), dtype=np.complex64)
        metadata = uhd.types.RXMetadata()

        # Start the stream
        stream_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.start_cont)
        stream_cmd.stream_now = True
        streamer.issue_stream_cmd(stream_cmd)

        # Receive samples
        streamer.recv(recv_buffer, metadata, timeout=1.0)
        if metadata.error_code != uhd.types.RXMetadataErrorCode.none:
            return None

        # Stop the stream
        stream_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.stop_cont)
        streamer.issue_stream_cmd(stream_cmd)

        return recv_buffer[0]
    except Exception:
        return None

def get_power_dBm(usrp, streamer, gain, nb_avera=10, freq=400e6, rx_bw=10e6):
    """
    Perform multiple power measurements, average them in linear scale, and return the averaged power in dBm.
    If measurements fail, attempt a lower-level reset of the radio before re-initializing.

    Args:
        usrp: The USRP object.
        streamer: The RX streamer object.
        gain (float): Receiver gain in dB.
        nb_avera (int): Number of measurements to average.
        freq (float): Center frequency in Hz (used for re-initialization).
        rx_bw (float): Receiver bandwidth in Hz (used for re-initialization).

    Returns:
        float: Averaged input power in dBm, or None if re-initialization fails.
    """
    linear_powers = []

    def reset_radio(usrp, streamer):
        """Perform a lower-level reset of the USRP."""
        try:
            print("Performing a lower-level reset of the USRP...")
            if streamer and hasattr(streamer, "issue_stream_cmd"):
                # Stop any ongoing streams
                streamer.issue_stream_cmd(uhd.types.StreamCMD(uhd.types.StreamMode.stop_cont))
            # Reset command time on the USRP object
            if usrp and hasattr(usrp, "set_command_time"):
                usrp.set_command_time(0.0)
                usrp.clear_command_time()
            time.sleep(1)  # Allow the USRP to stabilize
            print("USRP reset complete.")
        except Exception as e:
            print(f"Error during USRP reset: {e}")

    for attempt in range(3):  # Allow up to two retries after re-initialization
        for _ in range(nb_avera):
            frame = receive_frame(streamer)
            if frame is not None:
                power_linear = np.mean(np.abs(frame) ** 2)  # Calculate power in linear scale
                linear_powers.append(power_linear)
            else:
                print("Failed to measure power. Retrying...")
                break  # Exit the loop to attempt a reset or re-initialization

        if linear_powers:
            avg_linear_power = np.mean(linear_powers)
            avg_power_dbm = 10 * np.log10(avg_linear_power + 1e-12) + 30 - gain
            print(f"Measured power: {avg_power_dbm:.2f} dBm (averaged over {nb_avera} frames)")
            return avg_power_dbm
        else:
            if attempt == 0:  # Perform a lower-level reset on the first failure
                print("Attempting a lower-level reset of the radio...")
                reset_radio(usrp, streamer)
            else:
                print(f"Re-initializing the radio (attempt {attempt + 1})...")
                time.sleep(1)  # Add a delay before re-initialization
                usrp, streamer = initialize_radio(freq, gain, rx_bw)
                if not usrp or not streamer:
                    print("Failed to re-initialize the radio.")
                    return None

    print("Measurement failed after multiple re-initialization attempts.")
    return None

def get_fft(streamer, ax_fft, freq, rx_bw):
    """
    Compute and plot the FFT of a received frame in dB.

    Args:
        streamer: The RX streamer object.
        ax_fft: The Matplotlib axis for the FFT plot.
        freq (float): Center frequency in Hz.
        rx_bw (float): Receiver bandwidth in Hz.
    """
    frame = receive_frame(streamer)
    if frame is None:
        print("Failed to acquire frame for FFT.")
        return

    # Compute FFT
    fft_data = np.fft.fftshift(np.fft.fft(frame))
    fft_magnitude = 20 * np.log10(np.abs(fft_data) + 1e-12)  # Convert to dB

    # Frequency axis
    num_samples = len(frame)
    freq_axis = np.linspace(freq - rx_bw / 2, freq + rx_bw / 2, num_samples)

    # Clear and update the FFT plot
    ax_fft.clear()
    ax_fft.plot(freq_axis / 1e6, fft_magnitude, label="FFT (dB)")
    ax_fft.set_title("Real-Time FFT")
    ax_fft.set_xlabel("Frequency (MHz)")
    ax_fft.set_ylabel("Magnitude (dB)")
    ax_fft.legend()

def main():
    """
    Continuously measure power every 200ms and display a graphical representation
    with a moving window of the last 10 seconds, along with a real-time FFT.
    """
    freq = 384e6  # Center frequency in Hz
    gain = 76     # Receiver gain in dB
    rx_bw =5e6  # Receiver bandwidth in Hz
    nb_avera = 100  # Number of measurements to average

    print("Initializing radio...")
    usrp, streamer = initialize_radio(freq, gain, rx_bw)
    if not usrp or not streamer:
        print("Failed to initialize radio.")
        return

    # Initialize the plots
    fig, (ax_rssi, ax_fft) = plt.subplots(2, 1, figsize=(10, 8))
    fig.suptitle("Power and FFT Over Time")

    # RSSI plot
    ax_rssi.set_title("Power Over Time")
    ax_rssi.set_xlabel("Time (s)")
    ax_rssi.set_ylabel("Power (dBm)")
    power_data = deque(maxlen=50)  # Store the last 10 seconds of data (50 samples at 200ms intervals)
    time_data = deque(maxlen=50)  # Corresponding time values
    line_rssi, = ax_rssi.plot([], [], label="Power (dBm)")
    ax_rssi.legend()

    # Start time for the x-axis
    start_time = time.time()

    def update_plot(frame):
        """Update the RSSI and FFT plots."""
        current_time = time.time() - start_time

        # Update RSSI plot
        avg_power_dbm = get_power_dBm(usrp, streamer, gain, nb_avera, freq, rx_bw)
        if avg_power_dbm is not None:
            power_data.append(avg_power_dbm)
            time_data.append(current_time)
            print(f"Averaged power: {avg_power_dbm:.2f} dBm")

        # Update the line data for RSSI
        line_rssi.set_data(time_data, power_data)
        ax_rssi.relim()
        ax_rssi.autoscale_view()

        # Update FFT plot
        get_fft(streamer, ax_fft, freq, rx_bw)

    # Use FuncAnimation to update the plots every 200ms
    ani = FuncAnimation(fig, update_plot, interval=200)

    # Show the plots and block execution until the user closes them
    plt.show()
    print("Measurement stopped.")

if __name__ == "__main__":
    # Run the main function for debugging and FFT display
    main()
