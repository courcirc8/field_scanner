"""
Test UHD Transmitter and Receiver

This script transmits a continuous single tone at a specified frequency and power
using a USRP device. Simultaneously, it receives frames and displays the FFT in dB
in real time.

Configuration:
- Frequency: 400 MHz
- Output Power: -40 dBm
"""

import uhd
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import welch
import threading
import queue
import time

# Transmission parameters
freq_tx = 400e6  # Transmit frequency in Hz (400 MHz)
pout_tx = 60  # Transmit gain in dB (increased for better visibility)
sample_rate = 1e6  # Sample rate in samples per second (1 MS/s)
tone_freq = 100e3  # Tone frequency in Hz (increased to 100 kHz for better visibility)
amplitude = 1.0  # Maximum amplitude

# Reception parameters
rx_gain = 60  # Increased receive gain in dB
fft_size = 2048  # Increased FFT size for better resolution
buffer_multiplier = 10  # Number of buffers to average

def generate_tone(sample_rate, tone_freq, amplitude, duration=1.0):
    """
    Generate a sine wave tone.

    Args:
        sample_rate (float): Sample rate in samples per second.
        tone_freq (float): Frequency of the tone in Hz.
        amplitude (float): Amplitude of the tone (0 to 1).
        duration (float): Duration of the tone in seconds.

    Returns:
        np.ndarray: Array containing the generated tone samples.
    """
    t = np.arange(0, duration, 1 / sample_rate)
    tone = amplitude * np.exp(2j * np.pi * tone_freq * t)  # Complex sine wave
    return tone.astype(np.complex64)

def transmit(tx_streamer, tone, tx_metadata, stop_event):
    """Transmit the tone continuously in a separate thread."""
    chunk_size = min(tx_streamer.get_max_num_samps(), 1024)  # Limit chunk size
    print(f"Using chunk size: {chunk_size}")
    
    # Pre-generate tone buffer
    num_chunks = 10  # Keep several chunks in memory
    tone_buffer = np.tile(tone[:chunk_size], num_chunks)
    
    while not stop_event.is_set():
        try:
            tx_streamer.send(tone_buffer, tx_metadata)
            tx_metadata.start_of_burst = False
        except RuntimeError as e:
            print(f"Tx Error: {e}")
            time.sleep(0.1)  # Back off on error

def receive(rx_streamer, rx_metadata, sample_queue, stop_event):
    """Receive samples and put them into a queue."""
    max_samps = min(rx_streamer.get_max_num_samps(), 2048)
    buffer = np.zeros(max_samps, dtype=np.complex64)
    
    while not stop_event.is_set():
        try:
            num_rx_samps = rx_streamer.recv(buffer, rx_metadata)
            if num_rx_samps > 0:
                if sample_queue.qsize() < 2:  # Keep only recent samples
                    sample_queue.put(buffer[:num_rx_samps].copy())
            time.sleep(0.001)  # Small delay to prevent tight loop
        except RuntimeError as e:
            if "timeout" in str(e).lower():
                continue
            print(f"Rx Error: {e}")

def plot_fft(sample_queue, fft_size, sample_rate, stop_event):
    """Plot the FFT of received samples in real time."""
    plt.ion()
    fig = plt.figure(figsize=(10, 6))
    ax = fig.add_subplot(111)
    
    # Configure plot
    freqs = np.fft.fftshift(np.fft.fftfreq(fft_size, 1/sample_rate))
    line, = ax.plot(freqs, np.zeros(fft_size))
    ax.set_ylim(-120, -20)
    ax.set_xlim(-sample_rate/4, sample_rate/4)
    ax.grid(True)
    ax.set_title("Real-Time FFT")
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("Magnitude (dB)")
    plt.tight_layout()
    
    # Initialize averaging
    avg_buffer = np.zeros(fft_size)
    alpha = 0.3
    
    while not stop_event.is_set():
        try:
            if sample_queue.empty():
                plt.pause(0.05)
                continue
                
            samples = sample_queue.get_nowait()
            if len(samples) >= fft_size:
                # Process the samples
                fft_data = np.fft.fftshift(np.fft.fft(samples[:fft_size]))
                fft_mag = 20 * np.log10(np.abs(fft_data) + 1e-12)
                
                # Update average
                avg_buffer = (1 - alpha) * avg_buffer + alpha * fft_mag
                
                # Update plot
                line.set_ydata(avg_buffer)
                fig.canvas.draw_idle()
                plt.pause(0.05)
                
        except queue.Empty:
            plt.pause(0.05)
        except Exception as e:
            print(f"Plot error: {e}")
            plt.pause(0.05)

def main():
    # Create a USRP device
    usrp = uhd.usrp.MultiUSRP()

    # Set the transmit and receive center frequency
    usrp.set_tx_freq(freq_tx)
    usrp.set_rx_freq(freq_tx)
    print(f"Frequency set to {freq_tx / 1e6} MHz")
    print(f"Transmit frequency: {usrp.get_tx_freq()} Hz")
    print(f"Receive frequency: {usrp.get_rx_freq()} Hz")

    # Set the transmit gain
    usrp.set_tx_gain(pout_tx)
    print(f"Transmit power set to {pout_tx} dBm")

    # Set the receive gain
    usrp.set_rx_gain(rx_gain)
    print(f"Receive gain set to {rx_gain} dB")

    # Set the sample rate
    usrp.set_tx_rate(sample_rate)
    usrp.set_rx_rate(sample_rate)
    print(f"Sample rate set to {sample_rate / 1e6} MS/s")
    print(f"Transmit sample rate: {usrp.get_tx_rate()} samples/s")
    print(f"Receive sample rate: {usrp.get_rx_rate()} samples/s")

    # Generate shorter tone buffer
    tone = generate_tone(sample_rate, tone_freq, amplitude, duration=0.01)  # 10ms of data
    print(f"Generated a {tone_freq} Hz tone with amplitude {amplitude}")

    # Create streamers with specific CPU format
    stream_args = uhd.usrp.StreamArgs("fc32", "sc16")
    stream_args.channels = [0]
    tx_streamer = usrp.get_tx_stream(stream_args)
    rx_streamer = usrp.get_rx_stream(stream_args)
    print("Streamers created successfully")

    # Issue stream command with specific buffer size
    stream_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.start_cont)
    stream_cmd.stream_now = True
    stream_cmd.num_samps = 0  # Continuous streaming
    rx_streamer.issue_stream_cmd(stream_cmd)
    print("RX stream started")
    
    # Create buffers with fixed size
    rx_max_samps = min(rx_streamer.get_max_num_samps(), 2048)
    rx_buffer = np.zeros((rx_max_samps,), dtype=np.complex64)
    print(f"Created receive buffer with {rx_max_samps} samples")

    # Create a TXMetadata object for continuous transmission
    tx_metadata = uhd.types.TXMetadata()
    tx_metadata.start_of_burst = True  # Indicate the start of a burst
    tx_metadata.end_of_burst = False  # Indicate that this is not the end of the burst
    tx_metadata.has_time_spec = False  # No specific time spec is required

    # Create an RXMetadata object for receiving samples
    rx_metadata = uhd.types.RXMetadata()

    # Create a queue for received samples
    sample_queue = queue.Queue(maxsize=10)  # Limit queue size

    # Create a stop event for thread termination
    stop_event = threading.Event()

    # Create threads
    tx_thread = threading.Thread(target=transmit, 
                               args=(tx_streamer, tone, tx_metadata, stop_event),
                               daemon=True)
    
    rx_thread = threading.Thread(target=receive,
                               args=(rx_streamer, rx_metadata, sample_queue, stop_event),
                               daemon=True)

    try:
        # Start reception first
        rx_thread.start()
        print("Receive thread started")
        time.sleep(0.5)  # Give receiver more time to start
        
        # Then start transmission
        tx_thread.start()
        print("Transmit thread started")
        
        plot_fft(sample_queue, fft_size, sample_rate, stop_event)
    except KeyboardInterrupt:
        print("\nTransmission and reception stopped by user.")
    finally:
        # Signal the threads to stop
        stop_event.set()
        
        # Stop streaming
        stop_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.stop_cont)
        rx_streamer.issue_stream_cmd(stop_cmd)
        print("RX stream stopped")
        
        # Wait for threads
        tx_thread.join()
        rx_thread.join()

        # End the transmission
        tx_metadata.end_of_burst = True
        tx_streamer.send(np.zeros(fft_size, dtype=np.complex64), tx_metadata)
        print("Transmission ended.")

if __name__ == "__main__":
    main()
