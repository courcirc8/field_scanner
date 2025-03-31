import uhd
import numpy as np

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

def receive_frame(streamer, gain):
    """
    Receive a frame of samples and estimate the input power.
    
    Args:
        streamer: The RX streamer object.
        gain (float): Receiver gain in dB.
    
    Returns:
        float: Estimated input power in dBm.
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
            print(f"Metadata error: {metadata.error_code}")
            return None
        else:
            print("Received samples successfully.")

        # Stop the stream
        stream_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.stop_cont)
        streamer.issue_stream_cmd(stream_cmd)

        # Estimate power
        power_linear = np.mean(np.abs(recv_buffer[0])**2)  # Calculate power in linear scale
        power_dbm = 10 * np.log10(power_linear + 1e-12) + 30  # Convert to dBm
        input_power_dbm = power_dbm - gain  # Subtract receiver gain
        print(f"Estimated input power: {input_power_dbm:.2f} dBm (input)")
        return input_power_dbm
    except Exception as e:
        print(f"Error receiving frame: {e}")
        return None

if __name__ == "__main__":
    # Test and debug the measure_power function
    freq = 400e6  # Center frequency in Hz
    gain = 50     # Receiver gain in dB
    rx_bw = 10e6  # Receiver bandwidth in Hz

    print("Initializing radio...")
    usrp, streamer = initialize_radio(freq, gain, rx_bw)
    if usrp and streamer:
        print("Receiving frame...")
        power = receive_frame(streamer, gain)
        if power is not None:
            print(f"Measured power: {power:.2f} dBm")
        else:
            print("Failed to measure power.")
    else:
        print("Failed to initialize radio.")
