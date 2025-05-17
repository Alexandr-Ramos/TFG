import numpy as np
import tkinter as tk
import config
from collections import deque # kind of list but more eficient for some methods (using for circular buffer)

def open_dsp(root, lbl_ext_in, lbl_out_to_sys, lbl_in_from_sys,
        ext_in_dev, ext_in_ch, out_to_sys_dev, out_to_sys_ch, in_from_sys_dev, in_from_sys_ch,
        fs, bit_depth, block_size):

    # Create DSP window
    dsp_window = tk.Toplevel(root)
    dsp_window.title("Digital Signal Processor")
    dsp_window.geometry("800x600")

    # Parameters for the circular buffer
    ring_buffer_size = 20  # Number of blocks to keep
    block_len = block_size.get()
    ring_buffer = deque(maxlen=ring_buffer_size)
    last_processed_counter = -1


    # Pre-fill with silent blocks
    for _ in range(ring_buffer_size):
        ring_buffer.append(np.zeros(block_len, dtype=np.float32))
    
    # DSP processing: Bypass external input to output buffer
    def start_bypass():
        if ext_in_ch.get() < 1 or out_to_sys_ch.get() < 1:
            status_label.config(text="Please select valid input/output channels", fg="red")
            return
        
        # Reschedule using correct timing
        interval_ms = int(block_size.get() / fs.get() * 1000)

        def bypass_update():
            nonlocal last_processed_counter

            if not config.update_enabled:
                return  # Skip update if global updates disabled

            try:
                with config.buffer_lock:
                    # Check for invalid conditions
                    if (
                        config.buffer_data is None or
                        config.buffer_output is None or
                        ext_in_ch.get() < 1 or
                        out_to_sys_ch.get() < 1 or
                        config.buffer_data.shape[0] != block_len
                    ):
                        print("[DEBUG] buffer_data:", config.buffer_data.shape) ##########################################
                        print("[DEBUG] buffer_output:", config.buffer_output.shape)

                        # Generate a hash or ID to detect if buffer_data changed
                        buffer_id = id(config.buffer_data)
                        if buffer_id == last_processed_counter:
                            return  # same buffer, skip
                        last_processed_counter = buffer_id


                        return
                    
                    print("[DEBUG] buffer_data shape:", config.buffer_data.shape)############################################


                    # Extract selected mono input channel
                    signal = config.buffer_data[:, ext_in_ch.get() - 1]

                    # Store new signal block in circular buffer
                    ring_buffer.append(signal.copy())

                    # Get the latest valid block from the ring buffer
                    latest = ring_buffer[-1]

                    # Clear all channels in the output buffer
                    config.buffer_output[:] = 0

                    # Write the latest block to the selected output channel
                    config.buffer_output[:, out_to_sys_ch.get() - 1] = latest

            except Exception as e:
                print(f"[ERROR] DSP bypass failed: {e}")

            dsp_window.after(interval_ms, bypass_update)

            print("[DEBUG] Wrote block to output buffer") ###################################################


        status_label.config(text="Bypass ACTIVE", fg="green")
        dsp_window.after(0, bypass_update)

    # UI: Bypass control
    bypass_btn = tk.Button(dsp_window, text="Start Bypass", font=("Arial", 16), command=start_bypass)
    bypass_btn.pack(pady=40)

    # UI: Status label
    status_label = tk.Label(dsp_window, text="", fg="green")
    status_label.pack(pady=10)
