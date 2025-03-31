import uhd
import numpy as np

usrp = uhd.usrp.MultiUSRP()

num_samps = 10000 # number of samples received
center_freq = 100e6 # Hz
sample_rate = 1e6 # Hz
gain = 50 # dB from 0 to 76 for B200 radio

usrp.set_rx_rate(sample_rate, 0)
usrp.set_rx_freq(uhd.libpyuhd.types.tune_request(center_freq), 0)
usrp.set_rx_gain(gain, 0)

# Set up the stream and receive buffer
st_args = uhd.usrp.StreamArgs("fc32", "sc16")
st_args.channels = [0]
metadata = uhd.types.RXMetadata()
streamer = usrp.get_rx_stream(st_args)
recv_buffer = np.zeros((1, 1000), dtype=np.complex64)

# Start Stream
stream_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.start_cont)
stream_cmd.stream_now = True
streamer.issue_stream_cmd(stream_cmd)

# Receive Samples
samples = np.zeros(num_samps, dtype=np.complex64)
try:
    for i in range(num_samps // 1000):
        streamer.recv(recv_buffer, metadata)
        if metadata.error_code != uhd.types.RXMetadataErrorCode.none:
            print(f"Metadata error: {metadata.error_code}")
            break
        samples[i * 1000:(i + 1) * 1000] = recv_buffer[0]
except Exception as e:
    print(f"Error receiving samples: {e}")

# Stop Stream
stream_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.stop_cont)
streamer.issue_stream_cmd(stream_cmd)

print(len(samples))
print(samples[0:10])

def estimate_power(samples):
    """Estimate input power in dBm, subtracting receiver gain."""
    power_linear = np.mean(np.abs(samples)**2)  # Calculate power in linear scale
    power_dbm = 10 * np.log10(power_linear + 1e-12) + 30  # Convert to dBm
    input_power_dbm = power_dbm - gain  # Subtract receiver gain
    print(f"Estimated input power: {input_power_dbm:.2f} dBm (input)")
    return input_power_dbm

# Estimate input power
estimate_power(samples)