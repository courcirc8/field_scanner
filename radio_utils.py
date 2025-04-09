# This module provides interfaces to the USRP software-defined radio for field measurements.
# It includes functions for initializing the radio, configuring parameters, and measuring
# field strength at specified frequencies.
#
# The module addresses several challenges:
# 1. Reliable signal strength measurement in potentially noisy environments
# 2. Proper initialization and configuration of the USRP hardware
# 3. Averaging and processing of measurements for consistent results

import numpy as np
import uhd
from uhd.types import RXMetadata  # Correct import for RXMetadata
from uhd.usrp import StreamArgs  # Correct import for StreamArgs

def measure_field_strength(streamer, rx_gain):
    """
    Measure field strength using USRP streamer.
    
    This function captures a buffer of I/Q samples from the USRP,
    calculates the power, and converts it to dBm while accounting
    for the receiver gain.
    
    Args:
        streamer: USRP RX streamer object
        rx_gain: Receiver gain in dB
        
    Returns:
        Field strength in dBm, or None if measurement fails
    """
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
    """
    Initialize the USRP radio with specified parameters.
    
    This function sets up the USRP with the appropriate frequency,
    gain, bandwidth, and sample rate for field measurements.
    
    Args:
        center_frequency: Center frequency in Hz
        rx_gain: Receiver gain in dB
        equivalent_bw: Bandwidth in Hz
        
    Returns:
        Tuple of (usrp, streamer) objects, or (None, None) on failure
    """
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
    
    This is an enhanced version of measure_field_strength that performs
    multiple measurements and averages them for more stable results.
    It's particularly important for accurate field mapping in environments
    with temporal variations.
    
    Args:
        streamer: The USRP RX streamer object
        rx_gain: The receiver gain in dB
        num_samples: Number of samples to receive per measurement
        num_averages: Number of measurements to average
        
    Returns:
        float: The average power in dBm, or None on error
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