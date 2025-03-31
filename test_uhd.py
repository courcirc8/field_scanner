"""
USRP Test Script

This script tests the basic functionality of a USRP device, including initialization, 
streaming, and power estimation. It is intended for debugging and verifying the USRP 
setup before integrating it into the field scanner.

Implemented Features:
- USRP initialization with configurable frequency, gain, and bandwidth.
- Streaming and reception of samples.
- Power estimation in dBm from received samples.

Missing Features:
- Comprehensive testing for edge cases (e.g., invalid configurations).
- Support for testing multiple channels or advanced USRP features.
- Integration with automated test frameworks for continuous testing.
"""

import uhd
import time
import numpy as np

usrp = uhd.usrp.MultiUSRP()
print("USRP successfully connected.")

freq=400e6  # Center frequency in Hz
rx_bandwidth=10e6  # Receiver bandwidth in Hz
gain = 50  # Receiver gain in dB from 0 to 76 for B200 radio

# Configure USRP settings
usrp.set_rx_freq(freq, 0)  # Set center frequency to 400 MHz
usrp.set_rx_gain(gain, 0)     # Set gain to 50 dB
usrp.set_rx_bandwidth(rx_bandwidth, 0)  # Set receiver bandwidth to 10 MHz

# Print a summary
print(usrp.get_usrp_rx_info())

# Set up the stream and receive buffer
st_args = uhd.usrp.StreamArgs("fc32", "sc16")
st_args.channels = [0]  # Explicitly set the channel
streamer = usrp.get_rx_stream(st_args)
recv_buffer = np.zeros((1, streamer.get_max_num_samps()), dtype=np.complex64)
metadata = uhd.types.RXMetadata()

# Start the stream
stream_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.start_cont)
stream_cmd.stream_now = True
streamer.issue_stream_cmd(stream_cmd)

# Receive samples
try:
    streamer.recv(recv_buffer, metadata, timeout=1.0)
    if metadata.error_code != uhd.types.RXMetadataErrorCode.none:
        print(f"Metadata error: {metadata.error_code}")
    else:
        print("Received samples successfully.")
        print(recv_buffer[0][:10])  # Print the first 10 samples
except Exception as e:
    print(f"Error receiving samples: {e}")


def estimate_power(samples):
    """Estimate input power in dBm, subtracting receiver gain."""
    power_linear = np.mean(np.abs(samples)**2)  # Calculate power in linear scale
    power_dbm = 10 * np.log10(power_linear + 1e-12) + 30  # Convert to dBm
    input_power_dbm = power_dbm - gain  # Subtract receiver gain
    print(f"Estimated input power: {input_power_dbm:.2f} dBm (input)")
    return input_power_dbm

# Estimate input power
estimate_power(recv_buffer[0])

# Stop the stream
stream_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.stop_cont)
streamer.issue_stream_cmd(stream_cmd)
