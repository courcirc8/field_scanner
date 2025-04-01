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

def get_power_dBm(streamer, gain, nb_avera=10):
    """
    Perform multiple power measurements, average them in linear scale, and return the averaged power in dBm.

    Args:
        streamer: The RX streamer object.
        gain (float): Receiver gain in dB.
        nb_avera (int): Number of measurements to average.

    Returns:
        float: Averaged input power in dBm.
    """
    linear_powers = []

    for _ in range(nb_avera):
        frame = receive_frame(streamer)
        if frame is not None:
            power_linear = np.mean(np.abs(frame) ** 2)  # Calculate power in linear scale
            linear_powers.append(power_linear)
        else:
            print("Failed to measure power.")
            return None

    if linear_powers:
        avg_linear_power = np.mean(linear_powers)
        avg_power_dbm = 10 * np.log10(avg_linear_power + 1e-12) + 30 - gain
        print(f"Measured power: {avg_power_dbm:.2f} dBm (averaged over {nb_avera} frames)")
        return avg_power_dbm
    else:
        return None

def main():
    """
    Continuously measure power every 200ms and display a graphical representation
    with a moving window of the last 10 seconds.
    """
    freq = 400e6  # Center frequency in Hz
    gain = 76     # Receiver gain in dB
    rx_bw = 10e6  # Receiver bandwidth in Hz
    nb_avera = 100 # Number of measurements to average

    print("Initializing radio...")
    usrp, streamer = initialize_radio(freq, gain, rx_bw)
    if not usrp or not streamer:
        print("Failed to initialize radio.")
        return

    # Initialize the plot
    plt.ion()
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.set_title("Power Over Time")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Power (dBm)")
    power_data = deque(maxlen=50)  # Store the last 10 seconds of data (50 samples at 200ms intervals)
    time_data = deque(maxlen=50)  # Corresponding time values
    line, = ax.plot([], [], label="Power (dBm)")
    ax.legend()

    # Start time for the x-axis
    start_time = time.time()

    def update_plot(frame):
        """Update the plot with new power measurements."""
        current_time = time.time() - start_time
        avg_power_dbm = get_power_dBm(streamer, gain, nb_avera)
        if avg_power_dbm is not None:
            power_data.append(avg_power_dbm)
            time_data.append(current_time)
            print(f"Averaged power: {avg_power_dbm:.2f} dBm")

        # Update the line data
        line.set_data(time_data, power_data)
        ax.relim()
        ax.autoscale_view()

    # Use FuncAnimation to update the plot every 200ms
    ani = FuncAnimation(fig, update_plot, interval=200)

    # Show the plot and wait for user input to stop
    input("Press Enter to stop measurements...\n")
    plt.close(fig)
    print("Measurement stopped.")

if __name__ == "__main__":
    main()
