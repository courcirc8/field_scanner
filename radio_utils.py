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
import time
from config import DEBUG_ALL  # Import DEBUG_ALL
import threading  # Add this import for thread synchronization

# Global lock for synchronized printing
_print_lock = threading.Lock()

def synchronized_print(*args, **kwargs):
    """Thread-safe print function to prevent output corruption"""
    with _print_lock:
        print(*args, **kwargs)

def measure_field_strength(streamer, rx_gain, debug=True):
    """
    Measure field strength using USRP streamer.
    
    This function captures a buffer of I/Q samples from the USRP,
    calculates the power, and converts it to dBm while accounting
    for the receiver gain.
    
    Args:
        streamer: USRP RX streamer object
        rx_gain: Receiver gain in dB
        debug: Whether to print debug messages
        
    Returns:
        Field strength in dBm, or None if measurement fails
    """
    try:
        # Increase attempts to 4 for more reliable measurements
        max_attempts = 4
        for attempt in range(1, max_attempts + 1):
            # Issue a fresh stream command to ensure streaming is active
            stream_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.num_done)
            stream_cmd.num_samps = 1024  # Request specific number of samples
            stream_cmd.stream_now = True
            streamer.issue_stream_cmd(stream_cmd)
            
            # Receive samples
            buffer = np.zeros(1024, dtype=np.complex64)
            metadata = RXMetadata()
            num_rx_samps = streamer.recv(buffer, metadata, 0.5)  # Add timeout of 0.5s

            if metadata.error_code != uhd.types.RXMetadataErrorCode.none:
                if debug:
                    synchronized_print(f"WARNING: RX Metadata error on attempt {attempt}/{max_attempts}: {metadata.error_code}")
                
                # Try to recover by resetting the stream
                stop_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.stop_cont)
                streamer.issue_stream_cmd(stop_cmd)
                time.sleep(0.1)
                continue
            
            if num_rx_samps == 0:
                if debug:
                    synchronized_print(f"WARNING: No samples received on attempt {attempt}/{max_attempts}")
                continue
                
            # Check for valid signal (non-zero amplitude)
            valid_samples = buffer[:num_rx_samps]
            sample_amplitude = np.mean(np.abs(valid_samples))
            
            if sample_amplitude < 1e-9:  # Extremely low signal - likely no transmission
                if debug:
                    synchronized_print(f"WARNING: Signal amplitude too low on attempt {attempt}/{max_attempts}: {sample_amplitude:.2e}")
                continue
            
            # If we got here, we have a valid measurement
            power_linear = np.mean(np.abs(valid_samples)**2)
            power_dbm = 10 * np.log10(power_linear + 1e-12) + 30  # Convert to dBm
            input_power_dbm = power_dbm - rx_gain  # Subtract receiver gain
            
            if debug:
                synchronized_print(f"DEBUG: Success on attempt {attempt}/{max_attempts}, received {num_rx_samps} samples, amplitude: {sample_amplitude:.2e}, power: {input_power_dbm:.2f} dBm")
                
            return input_power_dbm
            
        # If we get here, all attempts failed
        if debug:
            synchronized_print(f"ERROR: All {max_attempts} measurement attempts failed")
        return None
            
    except RuntimeError as e:
        if debug:
            synchronized_print(f"Error measuring field strength: {e}")
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
        synchronized_print("DEBUG: Starting USRP initialization...")
        usrp = uhd.usrp.MultiUSRP()
        synchronized_print("DEBUG: USRP object created successfully")
        
        synchronized_print(f"DEBUG: Setting RX frequency to {center_frequency/1e6} MHz")
        usrp.set_rx_freq(center_frequency)
        synchronized_print(f"DEBUG: Actual RX frequency: {usrp.get_rx_freq()/1e6} MHz")
        
        synchronized_print(f"DEBUG: Setting RX gain to {rx_gain} dB")
        usrp.set_rx_gain(rx_gain)
        synchronized_print(f"DEBUG: Actual RX gain: {usrp.get_rx_gain()} dB")
        
        synchronized_print(f"DEBUG: Setting RX bandwidth to {equivalent_bw/1e6} MHz")
        usrp.set_rx_bandwidth(equivalent_bw)
        synchronized_print(f"DEBUG: Actual RX bandwidth: {usrp.get_rx_bandwidth()/1e6} MHz")
        
        synchronized_print(f"DEBUG: Setting RX sample rate to 1 MHz")
        usrp.set_rx_rate(1e6)  # Default sample rate
        synchronized_print(f"DEBUG: Actual RX sample rate: {usrp.get_rx_rate()/1e6} MHz")
        
        synchronized_print("DEBUG: Creating stream arguments")
        stream_args = StreamArgs("fc32", "sc16")
        synchronized_print("DEBUG: Stream arguments created, now getting RX stream")
        
        # This is often where programs can hang - add a timeout mechanism
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Timed out getting RX stream from USRP")
        
        # Set 10-second timeout for getting the stream
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(10)
        
        try:
            synchronized_print("DEBUG: Calling get_rx_stream() - this may take a moment...")
            streamer = usrp.get_rx_stream(stream_args)
            signal.alarm(0)  # Disable alarm
            synchronized_print("DEBUG: RX stream obtained successfully")
        except TimeoutError as e:
            synchronized_print(f"ERROR: {e}")
            signal.alarm(0)  # Disable alarm
            return None, None
        finally:
            signal.signal(signal.SIGALRM, old_handler)  # Restore original handler
        
        synchronized_print("DEBUG: USRP initialization complete")
        return usrp, streamer
    except RuntimeError as e:
        synchronized_print(f"ERROR initializing USRP: {e}")
        return None, None
    except Exception as e:
        synchronized_print(f"UNEXPECTED ERROR initializing USRP: {e}")
        import traceback
        traceback.print_exc()
        return None, None

def get_power_dBm(streamer, rx_gain, num_samples=1024, num_averages=10, debug=True, fast_mode=False):
    """
    Measure the average power in dBm from the received samples.
    
    Args:
        streamer: The USRP RX streamer object
        rx_gain: The receiver gain in dB
        num_samples: Number of samples to receive per measurement
        num_averages: Number of measurements to average
        debug: Whether to print debug messages
        fast_mode: If True, use minimal averaging for faster response
        
    Returns:
        float: The average power in dBm, or None on error
    """
    try:
        # For interactive/fast mode, use fewer averages
        if fast_mode:
            num_averages = 2  # Reduce averaging drastically
            
        # CRITICAL FIX: Complete stream reset to clear all buffered samples
        # First stop any ongoing streaming
        stop_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.stop_cont)
        streamer.issue_stream_cmd(stop_cmd)
        time.sleep(0.01)  # Small delay to ensure command is processed
        
        # Then issue a new stream command to start fresh
        stream_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.start_cont)
        stream_cmd.stream_now = True
        streamer.issue_stream_cmd(stream_cmd)
        
        # Discard initial samples which might be stale
        discard_count = 10  # Increased from implicit 0
        buffer = np.zeros(num_samples, dtype=np.complex64)
        metadata = uhd.types.RXMetadata()
        
        # Actively discard samples to clear buffers
        for _ in range(discard_count):
            try:
                streamer.recv(buffer, metadata, 0.01)  # Short timeout
            except:
                pass  # Ignore errors during discard
        
        # Fast mode needs less settling time after discard
        if not fast_mode:
            time.sleep(0.05)
        else:
            time.sleep(0.01)
        
        # Reset buffer for actual measurements
        power_linear = []
        
        # Increase max attempts to handle timeout errors
        attempts = 0
        max_attempts = num_averages * (2 if fast_mode else 3)  # Fewer attempts for fast mode
        
        while len(power_linear) < num_averages and attempts < max_attempts:
            attempts += 1
            try:
                # Shorter timeout for fast mode
                timeout = 0.05 if fast_mode else 0.1
                num_rx_samps = streamer.recv(buffer, metadata, timeout)
                
                # Handle metadata errors
                if metadata.error_code != uhd.types.RXMetadataErrorCode.none:
                    if debug and not fast_mode:  # Skip debug in fast mode
                        synchronized_print(f"WARNING: RX Metadata error: {metadata.error_code}")
                    continue
                
                if num_rx_samps > 0:
                    # Calculate power only from valid samples
                    valid_samples = buffer[:num_rx_samps]
                    sample_power = np.mean(np.abs(valid_samples)**2)
                    if not np.isnan(sample_power) and sample_power > 0:
                        power_linear.append(sample_power)
                        if debug and not fast_mode:  # Skip debug in fast mode
                            synchronized_print(f"DEBUG: Good measurement {len(power_linear)}/{num_averages}")
            except RuntimeError as e:
                if "timeout" in str(e).lower() and debug and not fast_mode:
                    synchronized_print(f"NOTE: Timeout during receive, retrying ({attempts}/{max_attempts})")
                elif debug and not fast_mode:
                    synchronized_print(f"ERROR during receive: {e}")
                    
            # Minimal delay between measurements in fast mode
            time.sleep(0.005 if fast_mode else 0.01)
                    
        # Stop continuous streaming
        stop_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.stop_cont)
        streamer.issue_stream_cmd(stop_cmd)
        
        # Check if we have any valid measurements
        if not power_linear:  # Empty list
            if debug and not fast_mode:
                synchronized_print("WARNING: No valid power measurements obtained")
            return None
            
        if debug and not fast_mode:
            synchronized_print(f"DEBUG: Obtained {len(power_linear)} valid power measurements")
            
        avg_power_linear = np.mean(power_linear)
        power_dbm = 10 * np.log10(avg_power_linear + 1e-12) + 30
        input_power_dbm = power_dbm - rx_gain
        return input_power_dbm
    except Exception as e:
        if debug and not fast_mode:
            synchronized_print(f"Error measuring power: {e}")
            import traceback
            traceback.print_exc()
        return None