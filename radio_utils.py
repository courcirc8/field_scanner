import numpy as np
import uhd
from uhd.types import RXMetadata  # Correct import for RXMetadata
from uhd.usrp import StreamArgs  # Correct import for StreamArgs

def measure_field_strength(streamer, rx_gain):
    """Measure field strength using USRP streamer."""
    try:
        # Receive samples
        buffer = np.zeros(1024, dtype=np.complex64)
        metadata = RXMetadata()
        streamer.recv(buffer, metadata)

        # Calculate power in dBm
        power_linear = np.mean(np.abs(buffer)**2)
        power_dbm = 10 * np.log10(power_linear + 1e-12) + 30  # Convert to dBm
        input_power_dbm = power_dbm - rx_gain  # Subtract receiver gain
        return input_power_dbm
    except RuntimeError as e:
        print(f"Error measuring field strength: {e}")
        return None

def initialize_radio(center_frequency, rx_gain, equivalent_bw):
    """Initialize the USRP radio."""
    try:
        usrp = uhd.usrp.MultiUSRP()
        usrp.set_rx_freq(center_frequency)
        usrp.set_rx_gain(rx_gain)
        usrp.set_rx_bandwidth(equivalent_bw)
        usrp.set_rx_rate(1e6)  # Default sample rate
        stream_args = StreamArgs("fc32", "sc16")
        streamer = usrp.get_rx_stream(stream_args)
        return usrp, streamer
    except RuntimeError as e:
        print(f"Error initializing USRP: {e}")
        return None, None

def get_power_dBm(streamer, rx_gain, num_samples=1024, num_averages=10):
    """
    Measure the average power in dBm from the received samples.

    Args:
        streamer: The USRP RX streamer object.
        rx_gain: The receiver gain in dB.
        num_samples: Number of samples to receive per measurement.
        num_averages: Number of measurements to average.

    Returns:
        float: The average power in dBm.
    """
    try:
        buffer = np.zeros(num_samples, dtype=np.complex64)
        metadata = RXMetadata()
        power_linear = []

        for _ in range(num_averages):
            num_rx_samps = streamer.recv(buffer, metadata)
            if num_rx_samps > 0:
                power_linear.append(np.mean(np.abs(buffer[:num_rx_samps])**2))

        avg_power_linear = np.mean(power_linear)
        power_dbm = 10 * np.log10(avg_power_linear + 1e-12) + 30  # Convert to dBm
        input_power_dbm = power_dbm - rx_gain  # Subtract receiver gain
        return input_power_dbm
    except RuntimeError as e:
        print(f"Error measuring power: {e}")
        return None