import numpy as np
import sounddevice as sd
import librosa as lb
import tkinter as tk
# from tkinter import messagebox
from tkinter import ttk
import threading
import time

from settings import open_settings  # Import open_settings function
from analysis import open_analysis
from dsp import open_dsp
import config #import audio_stream_ext_in, buffer_data, buffer_lock  # Import shared configuration

last_update_time = 0

# Create a principal Window
root = tk.Tk()
root.title("RTA+C by ARS")
root.geometry("800x600")

# Create LED indicator canvas
led_canvas = tk.Canvas(root, width=20, height=20, highlightthickness=0)
led_canvas.place(x=10, y=10)
led = led_canvas.create_oval(2, 2, 18, 18, fill="red")


# "Global" objects
# dummy1 = tk.IntVar(master=root, value=0)
# dummy2 = tk.StringVar(master=root, value="default")
ext_in_dev = tk.IntVar(value=-1)
ext_in_ch = tk.IntVar(value=-1)
out_to_sys_dev = tk.IntVar(value=-1)
out_to_sys_ch = tk.IntVar(value=-1)
in_from_sys_dev = tk.IntVar(value=-1)
in_from_sys_ch = tk.IntVar(value=-1)
fs = tk.IntVar(value=44100)
bit_depth = tk.IntVar(value=16)
block_size = tk.IntVar(value=1024)

# Stream management #########################################
if config.audio_stream_ext_in is not None:
    print("[INFO] Stream is active")


def start_global_stream():
    # from config import audio_stream_ext_in, buffer_data, buffer_lock

    if config.audio_stream_ext_in is not None:
        print("[INFO] Stream is active.")
        return

    channels = max(ext_in_ch.get(), in_from_sys_ch.get())
    blocksize = block_size.get()
    samplerate = fs.get()

    def audio_callback(indata, frames, time_info, status):
        # global buffer_data
        # Write incoming audio to the shared buffer
        with config.buffer_lock:
            config.buffer_data = indata.copy()

        config.last_update_time = time.time()  # Track last update timestamp

        # Debug
        # print(f"[DEBUG] Stream callback: buffer updated with shape {indata.shape}")

    try:
        stream = sd.InputStream(
            device=ext_in_dev.get(),
            channels=channels,
            samplerate=samplerate,
            blocksize=blocksize,
            callback=audio_callback
        )
        stream.start()
        config.audio_stream_ext_in = stream
        print("[INFO] Global stream started.")
    except Exception as e:
        print(f"[ERROR] It is not possible to start global Stream: {e}")
    
def stop_global_stream():
    # from config import audio_stream_ext_in
    if config.audio_stream_ext_in:
        config.audio_stream_ext_in.stop()
        config.audio_stream_ext_in.close()
        config.audio_stream_ext_in = None
        print("[INFO] Stream global aturat.")

def update_led():
    now = time.time()
    # If the buffer has been updated in the last 0.5 seconds, set to green
    if now - config.last_update_time < 0.5:
        led_canvas.itemconfig(led, fill="green")
    else:
        led_canvas.itemconfig(led, fill="red")

    root.after(300, update_led)

# Create menu bar with settings button.
menubar = tk.Menu(root)

# Create selected info
lbl_ext_in = tk.Label(root, text="Selected external input device: None, channel: None")
lbl_ext_in.pack(pady=5)

lbl_out_to_sys = tk.Label(root, text="Selected output to system device: None, channel: None")
lbl_out_to_sys.pack(pady=5)

lbl_in_from_sys = tk.Label(root, text="Selected input from system device: None, channel: None")
lbl_in_from_sys.pack(pady=5)

# Butons to control global stream ############################################
stream_button_frame = tk.Frame(root)
stream_button_frame.pack(pady=10)

btn_start_stream = tk.Button(stream_button_frame, text="Start Stream", command=start_global_stream)
btn_start_stream.pack(side="left", padx=5)

btn_stop_stream = tk.Button(stream_button_frame, text="Stop Stream", command=stop_global_stream)
btn_stop_stream.pack(side="left", padx=5)
 
#Window structure
menubar.add_command(label="Settings", command=lambda: open_settings(root,
    lbl_ext_in, lbl_out_to_sys, lbl_in_from_sys,
    ext_in_dev, ext_in_ch, out_to_sys_dev, out_to_sys_ch, in_from_sys_dev, in_from_sys_ch,
    fs, bit_depth, block_size))
root.config(menu=menubar)

# Container for analysis and correction buttons
main_button_frame = tk.Frame(root)
main_button_frame.pack(pady=20)

# Big Analysis button
analysis_button = tk.Button(main_button_frame, text="Analysis", font=("Arial", 16), width=15, height=4,
    command=lambda: open_analysis(root, lbl_ext_in, lbl_out_to_sys, lbl_in_from_sys,
    ext_in_dev, ext_in_ch, out_to_sys_dev, out_to_sys_ch, in_from_sys_dev, in_from_sys_ch,
    fs, bit_depth, block_size)
    )
analysis_button.grid(row=0, column=0, padx=10)

# # Placeholder (for future content in between)
# middle_placeholder = tk.Label(main_button_frame, text="", width=10)
# middle_placeholder.grid(row=0, column=1)

# Big Correction button
correction_button = tk.Button(main_button_frame, text="Correction (DSP)", font=("Arial", 16), width=15, height=4, 
    command=lambda: open_dsp(root, lbl_ext_in, lbl_out_to_sys, lbl_in_from_sys,
    ext_in_dev, ext_in_ch, out_to_sys_dev, out_to_sys_ch, in_from_sys_dev, in_from_sys_ch,
    fs, bit_depth, block_size)
    )
correction_button.grid(row=0, column=2, padx=10)

def on_root_close():
    config.update_enabled=False # Prevent all periodic updates
    stop_global_stream()  # Ensure the stream is stopped
    root.destroy()        # Close the GUI safely

root.protocol("WM_DELETE_WINDOW", on_root_close)

update_led()  # Start monitoring buffer updates

root.mainloop()