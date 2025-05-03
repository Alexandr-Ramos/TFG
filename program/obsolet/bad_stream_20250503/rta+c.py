import numpy as np
import sounddevice as sd
import librosa as lb
import tkinter as tk
# from tkinter import messagebox
from tkinter import ttk

from settings import open_settings  # Import open_settings function
from analysis import open_analysis
from dsp import open_dsp
import config  # Import shared configuration


# Create a principal Window
root = tk.Tk()
root.title("RTA+C by ARS")
root.geometry("800x600")

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

# Create menu bar with settings button.
menubar = tk.Menu(root)

# Create selected info
lbl_ext_in = tk.Label(root, text="Selected external input device: None, channel: None")
lbl_ext_in.pack(pady=5)

lbl_out_to_sys = tk.Label(root, text="Selected output to system device: None, channel: None")
lbl_out_to_sys.pack(pady=5)

lbl_in_from_sys = tk.Label(root, text="Selected input from system device: None, channel: None")
lbl_in_from_sys.pack(pady=5)
 
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


root.mainloop()