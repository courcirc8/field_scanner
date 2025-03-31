import uhd
import time

usrp = uhd.usrp.MultiUSRP()
print("USRP successfully connected.")

usrp.set_rx_freq(400e6)
usrp.set_rx_gain(20)
usrp.set_rx_rate(1e6)  # 1 MS/s

# Print a summary
print(usrp.get_usrp_rx_info())

# Try to receive samples
streamer = usrp.get_rx_stream(uhd.usrp.StreamArgs("fc32"))
buffer = [0] * streamer.get_max_num_samps()
md = uhd.types.RXMetadata()

streamer.recv(buffer, md, timeout=1.0)
print("Received samples successfully.")
