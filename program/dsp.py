import numpy as np
import tkinter as tk
from scipy import signal
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

    # State of window
    next_mode = tk.StringVar(value="Stop")  # Modes: Stop, Bypass, EQ
    eq_active = False
    bypass_active = False

    # Frequencies for 1/3 octave bands --> IEC 61260-3
    center_freqs = np.array([
        20, 25, 31.5, 40, 50, 63, 80, 100, 125, 160,
        200, 250, 315, 400, 500, 630, 800, 1000, 1250, 1600,
        2000, 2500, 3150, 4000, 5000, 6300, 8000, 10000, 12500, 16000, 20000
    ])
    current_gain = np.zeros(31, dtype=np.float32) # Default gain values for each band
    current_gain_label = [] # Needed to show on the feedback greed
    if config.gain_values is None:
        analysis_gain_label = [0.0] * len(center_freqs)
    else:
        analysis_gain_label = config.gain_values
        if len(analysis_gain_label) < len(center_freqs):
            analysis_gain_label += [0.0] * (len(center_freqs) - len(analysis_gain_label))
    manual_gain = [tk.StringVar(value="0.00") for _ in center_freqs] # We will use this to manually edit gains.

    # Frame for EQ interface
    eq_panel = tk.Frame(dsp_window)
    eq_panel.pack(pady=10)

    # Row 0: Band labels
    for col, freq in enumerate(center_freqs):
        lbl = tk.Label(eq_panel, text=f"{freq:.1f}", font=("Arial", 8), width=6)
        lbl.grid(row=0, column=col)

    # Row 1: Current applied gain (updatable)
    for col in range(len(center_freqs)):
        lbl = tk.Label(eq_panel, text=f"{current_gain[col]:.1f}", width=6)
        lbl.grid(row=1, column=col)
        current_gain_label.append(lbl)

    # # Row 2: Analysis gain (from config)
    for col in range(len(center_freqs)):
        val = analysis_gain_label[col]
        lbl = tk.Label(eq_panel, text=f"{val:.1f}", fg="blue", width=6)
        lbl.grid(row=2, column=col)
        analysis_gain_label.append(lbl)

    # Row 3: Manual input fields
    for col, var in enumerate(manual_gain):
        entry = tk.Entry(eq_panel, textvariable=var, width=6)
        entry.grid(row=3, column=col)


    #### Bypass external input to output buffer ####
    def start_bypass():
        if ext_in_ch.get() < 1 or out_to_sys_ch.get() < 1:
            status_label.config(text="Please select valid input/output channels", fg="red")
            return
        
        # Reschedule using correct timing
        interval_ms = int(block_size.get() / fs.get() * 1000)

        def bypass_update():
            nonlocal bypass_active, last_processed_counter
            
            if not bypass_active:
                print("Bypass unabled")
                dsp_window.after(interval_ms, bypass_update)
                return


            if not config.update_enabled:

                print("Update Unabled")
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
                    dsp_window.after(interval_ms, bypass_update) # Once I have data, countdown for next block.

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

            print("[DEBUG] Wrote block to output buffer") ###################################################


        status_label.config(text="Bypass ACTIVE", fg="green")
        dsp_window.after(0, bypass_update)

    def start_EQ():
        # Design bandpass filters for each 1/3 octave band
        sos_filters = []
        for fc in center_freqs:
            low = fc / (2 ** (1/6))
            high = fc * (2 ** (1/6))

            # Skip bands that exceed Nyquist frequency
            if high >= fs.get() / 2:
                continue

            # Butterworh filter
            sos = signal.butter(N=4, Wn=[low, high], btype='band', fs=fs.get(), output='sos')
            sos_filters.append(sos)

        # Reschedule using correct timing
        interval_ms = int(block_size.get() / fs.get() * 1000)

        def update_EQ():
            nonlocal eq_active, last_processed_counter, current_gain

            if not eq_active:
                return

            # Read the input buffer and apply 31-band equalization
            with config.buffer_lock:
                # Validate input
                if (
                    config.buffer_data is None or
                    config.buffer_output is None or
                    ext_in_ch.get() < 1 or
                    out_to_sys_ch.get() < 1
                ):
                    return

                # Extract selected mono input channel
                signal_in = config.buffer_data[:, ext_in_ch.get() - 1]
                dsp_window.after(interval_ms, update_EQ) # Once I have data, countdown for next block.

                # Prepare accumulation buffer
                acc = np.zeros_like(signal_in)

                # Apply each band filter and gain
                for i, sos in enumerate(sos_filters):
                    band = signal.sosfilt(sos, signal_in)
                    gain = 10 ** (current_gain[i] / 20)  # Convert dB to linear gain
                    acc += band * gain

                # Clear output buffer and write to selected output channel
                config.buffer_output[:] = 0
                config.buffer_output[:, out_to_sys_ch.get() - 1] = acc

                print("EQ active") ####################################
            
                status_label.config(text="EQ ACTIVE", fg="green")
            
        update_EQ()

    #### Buttons ####
    def apply_analysis_values():
        for i in range(len(center_freqs)):
            manual_gain[i].set(f"{config.gain[i]:.2f}")

    def apply_manual_values():
        for i, var in enumerate(manual_gain):
            try:
                val = float(var.get())
            except ValueError:
                val = 0.0
            current_gain[i] = val
            current_gain[i].config(text=f"{val:.2f}")

    def refresh_analysis_values():
        if config.gain_values is None:
            data = [0.0] * len(center_freqs)
        else:
            data = list(config.gain_values)
            if len(data) < len(center_freqs):
                data += [0.0] * (len(center_freqs) - len(data))

        for i in range(len(center_freqs)):
            analysis_gain_label[i].config(text=f"{data[i]:.1f}")



    def toggle_mode():
        nonlocal bypass_active, eq_active

        # Cycle through states
        if next_mode.get() == "Stop":
            next_mode.set("Bypass")
            bypass_active = True
            eq_active = False
            start_bypass()
            mode_btn.config(text="EQ")
            status_label.config(text=" Current mode: Bypass", fg="green")

        elif next_mode.get() == "Bypass":
            next_mode.set("EQ")
            bypass_active = False
            eq_active = True
            start_EQ()
            mode_btn.config(text="Stop")
            status_label.config(text="Current mode: EQ", fg="blue")

        elif next_mode.get() == "EQ":
            next_mode.set("Stop")
            eq_active = False
            bypass_active = False

            # Clear output buffer one time
            with config.buffer_lock:
                if config.buffer_output is not None:
                    config.buffer_output[:] = np.zeros_like(config.buffer_output)

            mode_btn.config(text="Bypass")
            status_label.config(text="Current mode: Stopped", fg="red")

    btn_frame = tk.Frame(dsp_window)
    btn_frame.pack(pady=10)

    tk.Button(btn_frame, text="Refresh", command=refresh_analysis_values).pack(side="left", padx=5)
    tk.Button(btn_frame, text="Apply Analysis values", command=apply_analysis_values).pack(side="left", padx=5)
    tk.Button(btn_frame, text="Apply Manual values", command=apply_manual_values).pack(side="left", padx=5)

    top_frame = tk.Frame(dsp_window)
    top_frame.pack(pady=10)

    # Mode cycle button
    mode_btn = tk.Button(top_frame, text="Bypass", font=("Arial", 16), command=toggle_mode)
    mode_btn.pack(side="left", padx=10)

    # UI: Status label
    status_label = tk.Label(top_frame, text="", fg="green")
    status_label.pack(side="left", padx=10)
