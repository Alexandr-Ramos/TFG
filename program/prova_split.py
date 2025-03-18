import numpy as np
import sounddevice as sd
import librosa as lb
import tkinter as tk
# from tkinter import messagebox
from tkinter import ttk

from settings import open_settings  # Import open_settings function
import config  # Import shared configuration


# Create a principal Window
root = tk.Tk()
root.title("RTA+C by ARS")
root.geometry("800x600")

# Create menu bar with settings button.
menubar = tk.Menu(root)
# Create selected info
selection_label = tk.Label(root, text="Selected external input device: None, channel: None")
selection_label.pack(pady=5)

#Window structure
menubar.add_command(label="Settings", command=lambda: open_settings(root, selection_label))
root.config(menu=menubar)

root.mainloop()