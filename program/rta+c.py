import numpy as np
import sounddevice as sd
import librosa as lb
import tkinter as tk
# from tkinter import messagebox
from tkinter import ttk

# Settings Window
def open_settings():
    global ext_in_dev, ext_in_ch  # Ensure we can modify global variables

    settings_window = tk.Toplevel(root)
    settings_window.title("Settings")
    settings_window.geometry("400x250")

    # Label for the device selection
    label_device = tk.Label(settings_window, text="External audio source:")
    label_device.pack(pady=5)

    # Get available input devices (store index instead of name)
    devices = sd.query_devices()
    input_devices = {i: d for i, d in enumerate(devices) if d['max_input_channels'] > 0}

    # Extract list of names for UI, but store the ID internally
    device_names = [f"{i}: {d['name']}" for i, d in input_devices.items()]
    
    # Variable to store selected device index
    selected_device = tk.StringVar()

    # Dropdown menu for device selection
    device_dropdown = ttk.Combobox(settings_window, textvariable=selected_device, values=device_names, state="readonly")
    device_dropdown.pack(pady=5)

    # Select first device by default if available
    if input_devices:
        first_device = list(input_devices.keys())[0]
        device_dropdown.current(0)
    else:
        first_device = None

    # Label for channel selection
    label_channel = tk.Label(settings_window, text="Select channel:")
    label_channel.pack(pady=5)

    # Variable to store selected channel
    selected_channel_var = tk.StringVar()

    # Function to update channel options based on selected device
    def update_channels(*args):
        device_index = int(selected_device.get().split(":")[0])  # Extract device index
        if device_index in input_devices:
            max_channels = input_devices[device_index]['max_input_channels']
            channel_options = [str(i + 1) for i in range(max_channels)]  # Channels start at 1
            channel_dropdown["values"] = channel_options
            channel_dropdown.current(0)  # Default to first channel

    # Dropdown menu for channel selection
    channel_dropdown = ttk.Combobox(settings_window, textvariable=selected_channel_var, state="readonly")
    channel_dropdown.pack(pady=5)

    # Link device selection change to update_channels function
    selected_device.trace_add("write", update_channels)

    # Set default values
    if first_device is not None:
        update_channels()

    # Function to confirm selection
    def confirm_selection():
        ext_in_dev = int(selected_device.get().split(":")[0])  # Store device ID as integer
        ext_in_ch = int(selected_channel_var.get())  # Store channel as integer
        device_name = sd.query_devices(ext_in_dev)['name']  # Get device name from ID
        selection_label.config(text=f"External input: Device: {device_name}, Channel: {ext_in_ch}")
        print(f"Selected External Input Device: {device_name}, Channel: {ext_in_ch}")  # Debugging output
        settings_window.destroy()

    # Confirm button
    confirm_button = tk.Button(settings_window, text="Confirm", command=confirm_selection)
    confirm_button.pack(pady=10)


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
menubar.add_command(label="Settings", command=open_settings)
root.config(menu=menubar)

root.mainloop()