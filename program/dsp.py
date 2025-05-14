import numpy as np
import tkinter as tk
import sounddevice as sd
import config
import threading

def open_dsp(root, lbl_ext_in, lbl_out_to_sys, lbl_in_from_sys,
        ext_in_dev, ext_in_ch, out_to_sys_dev, out_to_sys_ch, in_from_sys_dev, in_from_sys_ch,
        fs, bit_depth, block_size): 
    
    global audio_stream_bypass

    # Create DSP window
    dsp_window = tk.Toplevel(root)
    dsp_window.title("Digital Signal Processor")
    dsp_window.geometry("800x600")

     # Callback function for bypass
    def audio_callback(indata, outdata, frames, time, status):
        # Pass-through signal from input to output
        outdata[:] = indata

    # Start the bypass stream
    def start_bypass():
        # stop_bypass_stream()
        global audio_stream_bypass

        try:
            if ext_in_dev.get() < 0 or ext_in_ch.get() < 1 or out_to_sys_dev.get() < 0 or out_to_sys_ch.get() < 1:
                status_label.config(text="Please select valid input and output devices", fg="red")
                return

            # Prepare shared buffer
            buffer = np.zeros(block_size.get(), dtype='float32')

            # Input stream
            input_stream = sd.InputStream(
                samplerate=fs.get(),
                blocksize=block_size.get(),
                dtype='float32',
                device=ext_in_dev.get(),
                channels=sd.query_devices(ext_in_dev.get())['max_input_channels'], ############################
            )

            # Output stream
            output_stream = sd.OutputStream(
                samplerate=fs.get(),
                blocksize=block_size.get(),
                dtype='float32',
                device=out_to_sys_dev.get(),
                channels=sd.query_devices(out_to_sys_dev.get())['max_output_channels'], #################
            )

            # Real-time forwarding loop
            def audio_loop():
                input_stream.start()
                output_stream.start()

                while audio_stream_bypass is not None:
                    indata, _ = input_stream.read(block_size.get())
                    buffer[:] = indata[:, ext_in_ch.get() - 1]  # Select desired input channel
                    out_block = np.zeros((block_size.get(), output_stream.channels), dtype='float32')
                    out_block[:, out_to_sys_ch.get() - 1] = buffer
                    output_stream.write(out_block)

            audio_stream_bypass = threading.Thread(target=audio_loop, daemon=True)
            audio_stream_bypass.start()

            status_label.config(text="Bypass stream running (single channel)", fg="green")

        except Exception as e:
            status_label.config(text=f"Error: {e}", fg="red")
            print(f"[ERROR] Could not start bypass stream: {e}")


    # Bypass button
    bypass_btn = tk.Button(dsp_window, text="Start Bypass", font=("Arial", 16), command=start_bypass)
    bypass_btn.pack(pady=40)

    # Status label
    status_label = tk.Label(dsp_window, text="", fg="green")
    status_label.pack(pady=10)
