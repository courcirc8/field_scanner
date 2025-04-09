"""
Simple test script to verify USRP initialization

This script attempts to initialize just the USRP device without the full scanning functionality.
It can help determine if there are issues with the basic USRP communication.
"""

import uhd
import sys
import time

def test_usrp_init():
    """Test basic USRP initialization and print detailed information."""
    try:
        print("Step 1: Creating USRP object...")
        usrp = uhd.usrp.MultiUSRP()
        print("USRP object created successfully")
        
        print("\nStep 2: Getting device information...")
        print(f"Device: {usrp.get_mboard_name()}")
        print(f"Serial: {usrp.get_usrp_rx_info().get('mboard_serial')}")
        
        print("\nStep 3: Setting basic parameters...")
        print("Setting RX frequency to 400 MHz")
        usrp.set_rx_freq(400e6)
        time.sleep(0.5)
        actual_freq = usrp.get_rx_freq()
        print(f"Actual RX frequency: {actual_freq/1e6} MHz")
        
        print("\nSetting RX gain to 50 dB")
        usrp.set_rx_gain(50)
        time.sleep(0.5)
        actual_gain = usrp.get_rx_gain()
        print(f"Actual RX gain: {actual_gain} dB")
        
        print("\nSetting RX rate to 1 MHz")
        usrp.set_rx_rate(1e6)
        time.sleep(0.5)
        actual_rate = usrp.get_rx_rate()
        print(f"Actual RX rate: {actual_rate/1e6} MHz")
        
        print("\nSetting RX bandwidth to 10 MHz")
        usrp.set_rx_bandwidth(10e6)
        time.sleep(0.5)
        actual_bw = usrp.get_rx_bandwidth()
        print(f"Actual RX bandwidth: {actual_bw/1e6} MHz")
        
        print("\nStep 4: Creating RX stream...")
        stream_args = uhd.usrp.StreamArgs("fc32", "sc16")
        print("About to get RX stream (this is where it might hang)...")
        streamer = usrp.get_rx_stream(stream_args)
        print("Successfully created RX stream")
        
        print("\nStep 5: Testing simple reception...")
        # Issue stream command
        stream_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.num_samps_and_done)
        stream_cmd.num_samps = 1000  # Get 1000 samples
        stream_cmd.stream_now = True
        streamer.issue_stream_cmd(stream_cmd)
        
        # Receive some samples
        buffer = [0] * 1000
        metadata = uhd.types.RXMetadata()
        num_rx_samps = streamer.recv(buffer, metadata)
        print(f"Received {num_rx_samps} samples")
        
        print("\nTest completed successfully!")
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=== USRP Initialization Test ===")
    success = test_usrp_init()
    sys.exit(0 if success else 1)
