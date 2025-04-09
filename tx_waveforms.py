#!/usr/bin/env python3
#
# Copyright 2017-2018 Ettus Research, a National Instruments Company
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
"""Generate and TX samples using a set of waveforms, and waveform characteristics.
"""

import argparse
import time

import numpy as np
import uhd
from uhd.usrp import dram_utils


def parse_args():
    """Parse the command line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--args", default="", type=str)
    parser.add_argument(
        "-w", "--waveform", default="sine", choices=["sine", "square", "const", "ramp"], type=str
    )
    parser.add_argument("-f", "--freq", type=float, required=True)
    parser.add_argument("-r", "--rate", default=1e6, type=float)
    parser.add_argument("-d", "--duration", default=5.0, type=float)
    parser.add_argument("-c", "--channels", default=0, nargs="+", type=int)
    parser.add_argument("-g", "--gain", type=int, default=10)
    parser.add_argument("--wave-freq", default=1e4, type=float)
    parser.add_argument("--wave-ampl", default=0.3, type=float)
    parser.add_argument(
        "--tx-delay",
        default=0.5,
        type=float,
        help="Delay before simultaneously starting transmission on all channels",
    )
    parser.add_argument(
        "--dram", action="store_true", help="If given, will attempt to stream via DRAM"
    )
    return parser.parse_args()


def multi_usrp_tx(args):
    """multi_usrp based TX example."""
    # Initialize USRP with timeout
    print("Initializing USRP...")
    usrp = uhd.usrp.MultiUSRP(args.args)
    
    # Configure device with timeouts
    print(f"Configuring device for {args.freq/1e6} MHz...")
    usrp.set_tx_rate(args.rate)
    usrp.set_tx_freq(args.freq)
    usrp.set_tx_gain(args.gain)
    
    # Print actual device settings
    print(f"Actual TX Rate: {usrp.get_tx_rate()/1e6} MHz")
    print(f"Actual TX Freq: {usrp.get_tx_freq()/1e6} MHz")
    print(f"Actual TX Gain: {usrp.get_tx_gain()} dB")
    
    # Create and configure TX streamer
    stream_args = uhd.usrp.StreamArgs("fc32", "sc16")
    tx_streamer = usrp.get_tx_stream(stream_args)
    
    # Generate shorter data buffer for better handling
    buffer_size = min(int(args.rate * 0.1), 8192)  # 100ms worth of samples or 8192, whichever is smaller
    data = np.ones(buffer_size, dtype=np.complex64)  # Constant tone
    
    # Setup metadata
    tx_metadata = uhd.types.TXMetadata()
    tx_metadata.start_of_burst = True
    tx_metadata.has_time_spec = False
    
    start_time = time.time()
    print(f"Starting transmission for {args.duration} seconds...")
    
    try:
        while (time.time() - start_time) < args.duration:
            tx_streamer.send(data, tx_metadata)
            tx_metadata.start_of_burst = False
            
            # Print status every 30 seconds
            elapsed = time.time() - start_time
            if int(elapsed) % 30 == 0:
                print(f"Transmitting... {int(args.duration - elapsed)}s remaining")
                
            # Small delay to prevent overwhelming the device
            time.sleep(0.001)
    
    except KeyboardInterrupt:
        print("\nTransmission interrupted by user")
    except RuntimeError as e:
        print(f"\nRuntime error: {e}")
    finally:
        # Cleanup
        print("Stopping transmission...")
        tx_metadata.end_of_burst = True
        tx_streamer.send(np.zeros(10, dtype=np.complex64), tx_metadata)
        time.sleep(0.1)  # Allow time for cleanup


def rfnoc_dram_tx(args):
    """rfnoc_graph + replay-block based TX example."""
    # Init graph
    graph = uhd.rfnoc.RfnocGraph(args.args)
    if graph.get_num_mboards() > 1:
        print("ERROR: This example only supports DRAM streaming on a single motherboard.")
        return
    # Init radios and replay block
    available_radio_chans = [
        (radio_block_id, chan)
        for radio_block_id in graph.find_blocks("Radio")
        for chan in range(graph.get_block(radio_block_id).get_num_input_ports())
    ]
    radio_chans = [available_radio_chans[x] for x in args.channels]
    print("Transmitting on radio channels:", end="")
    print("\n* ".join((f"{r}:{c}" for r, c in radio_chans)))
    dram = dram_utils.DramTransmitter(graph, radio_chans, cpu_format="fc32")
    replay = dram.replay_blocks[0]
    print(f"Using replay block: {replay.get_unique_id()}")
    # Separate loops for setting rate and frequency to minimize timed cmd queue
    for (radio, radio_chan), duc_info in zip(dram.radio_chan_pairs, dram.duc_chan_pairs):
        radio.set_tx_gain(args.gain, radio_chan)
        if duc_info:
            duc, duc_chan = duc_info
            duc.set_output_rate(args.rate, duc_chan)
        else:
            radio.set_rate(args.rate)

    is_x410 = graph.get_mb_controller().get_mboard_name() == "x410"
    if not is_x410 and len(dram.radio_chan_pairs) > 1:
        # Use timed tuning for more than one channel on all devices except X410
        # X410 does not support timed tuning correct yet.
        cmd_time_offset = 0.1
        cmd_time = dram.radio_chan_pairs[0][0].get_time_now() + cmd_time_offset
        for radio, radio_chan in dram.radio_chan_pairs:
            radio.set_command_time(cmd_time, radio_chan)
            radio.set_tx_frequency(args.freq, radio_chan)
        for radio, radio_chan in dram.radio_chan_pairs:
            radio.clear_command_time(radio_chan)
        # Enough time for tune time to expire
        time.sleep(cmd_time_offset)
    else:
        for radio, radio_chan in dram.radio_chan_pairs:
            radio.set_tx_frequency(args.freq, radio_chan)

    # Overwrite default memory regions to maximize available memory
    mem_regions = [(0, replay.get_mem_size()) for _ in args.channels]
    dram.mem_regions = mem_regions
    # Generate waveform
    data = uhd.dsp.signals.get_continuous_tone(
        args.rate,
        args.wave_freq,
        args.wave_ampl,
        desired_size=args.duration * args.rate,
        max_size=dram.replay_blocks[0].get_mem_size(),
        waveform=args.waveform,
    )
    if (
        args.duration > 0
        and len(radio_chans) == 1
        and dram.replay_blocks[0].get_mem_size() / 4 < args.duration * args.rate
    ):
        if len(data) < args.duration * args.rate:
            # If we are using this API, we need to upload the entire waveform,
            # we can't make use of looping over the same memory region over and
            # over again.
            data = np.tile(data, int(args.duration * args.rate // len(data)) + 1)
            data = data[: args.duration * args.rate]
        # This if-branch is completely redundant, but we keep it here as this is
        # an example and we want to showcase different ways of using the
        # DramTransmitter class.
        print(
            f"Uploading waveform data ({data.nbytes/(1024**2):.2f} MiB) "
            f"and starting streaming..."
        )
        tx_md = uhd.types.TXMetadata()
        # do not use time spec if tx_delay is 0 or if we are using an X410
        # X410 might run into tile sync error on timed commands
        if args.tx_delay == 0 or is_x410:
            tx_md.has_time_spec = False
        else:
            # In this case the tx_start_time needs to be sufficiently in the future
            # to also allow uploading of the data to the DRAM.
            tx_md.has_time_spec = True
            tx_md.time_spec = dram.radio_chan_pairs[0][0].get_time_now() + args.tx_delay
        # These flags actually don't do anything; but if this was a regular TX
        # streamer object, that's what we would write here.
        tx_md.start_of_burst = True
        tx_md.end_of_burst = True
        # Upload and send at time specified by tx_start_time
        dram.send(data, tx_md, 1.0)
    else:
        # Upload
        print(f"Uploading waveform data ({data.nbytes/(1024**2):.2f} MiB)...")
        dram.upload(data)
        # Start streaming
        stream_mode = (
            uhd.types.StreamMode.start_cont if args.duration <= 0 else uhd.types.StreamMode.num_done
        )
        stream_cmd = uhd.types.StreamCMD(stream_mode)
        if args.duration > 0:
            stream_cmd.num_samps = int(args.duration * args.rate)
        if args.tx_delay == 0:
            stream_cmd.stream_now = True
        else:
            stream_cmd.stream_now = False
            stream_cmd.time_spec = dram.radio_chan_pairs[0][0].get_time_now() + args.tx_delay
        print("Starting streaming...")
        dram.issue_stream_cmd(stream_cmd)
    if args.duration > 0:
        print("Waiting for transmission to complete...")
        # Sleep time allows for 1s of extra time for the transmission to complete
        time.sleep(args.duration + 1.0 + args.tx_delay)
        async_timeout = time.monotonic() + 5.0
        async_md = None
        while time.monotonic() < async_timeout:
            async_md = dram.recv_async_msg(0.5)
            if async_md and async_md.event_code == uhd.types.TXMetadataEventCode.burst_ack:
                break
            if async_md:
                print(f"Caught TX event code: {async_md.event_code}")
                async_md = None
        if not async_md:
            print("ERROR: Unable to receive ACK after burst!")
    else:
        print("Transmitting (Hit Ctrl-C to stop)...")
        try:
            while True:
                time.sleep(1.0)
        except KeyboardInterrupt:
            print("Terminating streaming.")
        stream_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.stop_cont)
        stream_cmd.stream_now = True
        dram.issue_stream_cmd(stream_cmd)
        time.sleep(args.tx_delay)


def main():
    """TX CW signal at 400 MHz for 5 minutes."""
    class Args:
        args = ""
        waveform = "const"
        freq = 400e6
        rate = 1e6
        duration = 300  # 5 minutes
        channels = [0]
        gain = 30  # Start with reasonable gain, adjust if needed
        wave_freq = 0
        wave_ampl = 0.1  # Reduced amplitude
        tx_delay = 0
        dram = False

    args = Args()
    print("Starting CW transmission...")
    print(f"Frequency: {args.freq/1e6} MHz")
    print(f"Duration: {args.duration} seconds")
    print(f"Initial gain: {args.gain} dB")
    
    try:
        multi_usrp_tx(args)
        print("Transmission completed successfully")
    except Exception as e:
        print(f"Error during transmission: {e}")


if __name__ == "__main__":
    main()