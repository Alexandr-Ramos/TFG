import tkinter as tk
from tkinter import ttk
import sounddevice as sd
import time
import config  # Import shared config variables

# Settings Window
def open_settings(root, lbl_ext_in, lbl_out_to_sys, lbl_in_from_sys,
        ext_in_dev, ext_in_ch, out_to_sys_dev, out_to_sys_ch, in_from_sys_dev, in_from_sys_ch,
        fs, bit_depth, block_size):  # Accept arguments 

    settings_window = tk.Toplevel(root)
    settings_window.title("Settings")
    settings_window.geometry("700x400")

    # Create container frames
    sidebar = tk.Frame(settings_window, width=150, bg="#ddd")
    content = tk.Frame(settings_window, bg="white")

    sidebar.pack(side="left", fill="y")
    content.pack(side="right", expand=True, fill="both")

    # Dictionary to hold pages
    pages = {}

    def show_page(page_name):
        for name, frame in pages.items():
            frame.pack_forget()
        pages[page_name].pack(fill="both", expand=True)

    #### PAGE 1: Device ####
    device_page = tk.Frame(content, bg="white")
    pages["Device"] = device_page

    label_device = tk.Label(device_page, text="Device Settings", font=("Arial", 14))
    label_device.pack(pady=10)


    #### Row 1: External input device selection ####
    row_ext_in = tk.Frame(device_page, bg="white")
    row_ext_in.pack(pady=5)

    # Label for external input
    tk.Label(row_ext_in, text="External audio source:", bg="white").grid(row=0, column=0, padx=5)

    # Get list of input devices, add "Internal" option (device = -1)
    device_names_ext_in = ["-1: Internal"] + [f"{i}: {d['name']}" for i, d in enumerate(sd.query_devices()) if d['max_input_channels'] > 0]
    device_selected_ext_in = tk.StringVar()

    # Dropdown for external input device selection
    device_dropdown_ext_in = ttk.Combobox(row_ext_in, textvariable=device_selected_ext_in, values=device_names_ext_in, state="readonly", width=30)
    device_dropdown_ext_in.grid(row=0, column=1, padx=5)
    device_dropdown_ext_in.current(0)

    # Label and dropdown for channel selection
    tk.Label(row_ext_in, text="Channel:", bg="white").grid(row=0, column=2, padx=5)
    channel_selected_ext_in = tk.StringVar()
    channel_dropdown_ext_in = ttk.Combobox(row_ext_in, textvariable=channel_selected_ext_in, state="readonly", width=5)
    channel_dropdown_ext_in.grid(row=0, column=3, padx=5)

    # Update available channels depending on selected device
    def update_channels_ext_in(*args):
        index_str = device_selected_ext_in.get().split(":")[0]
        if index_str == "-1":
            # "Internal" selected → disable channel selection
            channel_dropdown_ext_in["values"] = []
            channel_selected_ext_in.set("")
        else:
            device_index = int(index_str)
            max_channels = sd.query_devices(device_index)['max_input_channels']
            channels = [str(i + 1) for i in range(max_channels)]
            channel_dropdown_ext_in["values"] = channels
            channel_dropdown_ext_in.current(0)

    device_selected_ext_in.trace_add("write", update_channels_ext_in)
    update_channels_ext_in()

    #### Row 2: Output to system device selection ####
    row_out_to_sys = tk.Frame(device_page, bg="white")
    row_out_to_sys.pack(pady=5)

    tk.Label(row_out_to_sys, text="Output to system device:", bg="white").grid(row=0, column=0, padx=5)

    # Get list of output-capable devices
    device_names_out_to_sys = [f"{i}: {d['name']}" for i, d in enumerate(sd.query_devices()) if d['max_output_channels'] > 0]
    device_selected_out_to_sys = tk.StringVar()

    # Dropdown for output device
    device_dropdown_out_to_sys = ttk.Combobox(row_out_to_sys, textvariable=device_selected_out_to_sys, values=device_names_out_to_sys, state="readonly", width=30)
    device_dropdown_out_to_sys.grid(row=0, column=1, padx=5)

    # Channel selection for output
    tk.Label(row_out_to_sys, text="Channel:", bg="white").grid(row=0, column=2, padx=5)
    channel_selected_out_to_sys = tk.StringVar()
    channel_dropdown_out_to_sys = ttk.Combobox(row_out_to_sys, textvariable=channel_selected_out_to_sys, state="readonly", width=5)
    channel_dropdown_out_to_sys.grid(row=0, column=3, padx=5)

    # Update output channel list when device changes
    def update_channels_out_to_sys(*args):
        device_index = int(device_selected_out_to_sys.get().split(":")[0])
        max_channels = sd.query_devices(device_index)['max_output_channels']
        channels = [str(i + 1) for i in range(max_channels)]
        channel_dropdown_out_to_sys["values"] = channels
        channel_dropdown_out_to_sys.current(0)

    device_selected_out_to_sys.trace_add("write", update_channels_out_to_sys)
    if device_names_out_to_sys:
        device_dropdown_out_to_sys.current(0)
        update_channels_out_to_sys()

    #### Row 3: Input from system device selection ####
    row_in_from_sys = tk.Frame(device_page, bg="white")
    row_in_from_sys.pack(pady=5)

    tk.Label(row_in_from_sys, text="Input from system device:", bg="white").grid(row=0, column=0, padx=5)

    # Get list of input-capable devices
    device_names_in_from_sys = [f"{i}: {d['name']}" for i, d in enumerate(sd.query_devices()) if d['max_input_channels'] > 0]
    device_selected_in_from_sys = tk.StringVar()

    # Dropdown for system input device
    device_dropdown_in_from_sys = ttk.Combobox(row_in_from_sys, textvariable=device_selected_in_from_sys, values=device_names_in_from_sys, state="readonly", width=30)
    device_dropdown_in_from_sys.grid(row=0, column=1, padx=5)

    # Channel selection for system input
    tk.Label(row_in_from_sys, text="Channel:", bg="white").grid(row=0, column=2, padx=5)
    channel_selected_in_from_sys = tk.StringVar()
    channel_dropdown_in_from_sys = ttk.Combobox(row_in_from_sys, textvariable=channel_selected_in_from_sys, state="readonly", width=5)
    channel_dropdown_in_from_sys.grid(row=0, column=3, padx=5)

    # Update input channel list when device changes
    def update_channels_in_from_sys(*args):
        device_index = int(device_selected_in_from_sys.get().split(":")[0])
        max_channels = sd.query_devices(device_index)['max_input_channels']
        channels = [str(i + 1) for i in range(max_channels)]
        channel_dropdown_in_from_sys["values"] = channels
        channel_dropdown_in_from_sys.current(0)

    device_selected_in_from_sys.trace_add("write", update_channels_in_from_sys)
    if device_names_in_from_sys:
        device_dropdown_in_from_sys.current(0)
        update_channels_in_from_sys()


    # Function to confirm selection
    def confirm_selection():
        #### Get external input device and channel ####
        dev_ext_in_str = device_selected_ext_in.get()
        dev_ext_in_id = int(dev_ext_in_str.split(":")[0])
        ch_ext_in = -1 if dev_ext_in_id == -1 else int(channel_selected_ext_in.get())

        #### Get input from system device and channel ####
        dev_in_from_sys_id = int(device_selected_in_from_sys.get().split(":")[0])
        ch_in_from_sys = int(channel_selected_in_from_sys.get())

        #### Check for conflict: same device and same channel ####
        if dev_ext_in_id == dev_in_from_sys_id and ch_ext_in == ch_in_from_sys:
            status_label.config(
                text="ERROR: External input and input from system cannot be the same device and channel.",
                fg="red"
            )
            settings_window.after(5000, lambda: status_label.config(text="", fg="green"))
            return  # Abort update

        #### No conflict, proceed with update ####

        # External input
        ext_in_dev.set(dev_ext_in_id)
        ext_in_ch.set(ch_ext_in)
        name_ext_in = "Internal" if dev_ext_in_id == -1 else sd.query_devices(dev_ext_in_id)["name"]
        channel_text_ext_in = "N/A" if ch_ext_in == -1 else str(ch_ext_in)
        lbl_ext_in.config(text=f"External input: {name_ext_in}, Channel: {channel_text_ext_in}")

        # Output to system
        dev_out_to_sys_id = int(device_selected_out_to_sys.get().split(":")[0])
        out_to_sys_dev.set(dev_out_to_sys_id)
        out_to_sys_ch.set(int(channel_selected_out_to_sys.get()))
        name_out_to_sys = sd.query_devices(dev_out_to_sys_id)["name"]
        lbl_out_to_sys.config(text=f"Output to system: {name_out_to_sys}, Channel: {out_to_sys_ch.get()}")

        # Input from system
        in_from_sys_dev.set(dev_in_from_sys_id)
        in_from_sys_ch.set(ch_in_from_sys)
        name_in_from_sys = sd.query_devices(dev_in_from_sys_id)["name"]
        lbl_in_from_sys.config(text=f"Input from system: {name_in_from_sys}, Channel: {ch_in_from_sys}")

        # Confirmation message
        status_label.config(text="Device configuration updated.", fg="green")
        settings_window.after(5000, lambda: status_label.config(text=""))


    # Confirm button
    confirm_button = tk.Button(device_page, text="Confirm", command=confirm_selection)
    confirm_button.pack(pady=10)

    # Status message label (initially empty)
    status_label = tk.Label(device_page, text="", fg="green", bg=device_page["bg"])
    status_label.pack(pady=5)

    #### PAGE 2: Audio Settings ####
    audio_page = tk.Frame(content, bg="white")
    pages["Audio"] = audio_page

    label_audio = tk.Label(audio_page, text="Audio Settings", font=("Arial", 14))
    label_audio.pack(pady=10)

    # Frame for all audio parameters
    audio_params_frame = tk.Frame(audio_page, bg="white")
    audio_params_frame.pack(pady=10)

    #### Sample Rate ####
    tk.Label(audio_params_frame, text="Sample Rate (Hz):", bg="white").grid(row=0, column=0, sticky="e", padx=5, pady=5)
    sample_rate_values = [44100, 48000, 96000, 192000]
    sample_rate_var = tk.StringVar(value=str(fs.get()))
    sample_rate_dropdown = ttk.Combobox(audio_params_frame, textvariable=sample_rate_var, values=[str(v) for v in sample_rate_values], width=10)
    sample_rate_dropdown.grid(row=0, column=1, padx=5)

    #### Bit Depth ####
    tk.Label(audio_params_frame, text="Bit Depth:", bg="white").grid(row=1, column=0, sticky="e", padx=5, pady=5)
    bit_depth_values = [16, 24, 32]
    bit_depth_var = tk.StringVar(value=str(bit_depth.get()))
    bit_depth_dropdown = ttk.Combobox(audio_params_frame, textvariable=bit_depth_var, values=[str(v) for v in bit_depth_values], width=10)
    bit_depth_dropdown.grid(row=1, column=1, padx=5)

    #### Block Size ####
    tk.Label(audio_params_frame, text="Block Size:", bg="white").grid(row=2, column=0, sticky="e", padx=5, pady=5)
    block_size_values = [128, 256, 512, 1024, 2048, 4096]
    block_size_var = tk.StringVar(value=str(block_size.get()))
    block_size_dropdown = ttk.Combobox(audio_params_frame, textvariable=block_size_var, values=[str(v) for v in block_size_values], width=10)
    block_size_dropdown.grid(row=2, column=1, padx=5)

    #### Save button ####
    # Utility: show status message for 5 seconds, canceling previous timers
    def show_status_audio_message(message, color):
        status_label_audio.config(text=message, fg=color)
        try:
            settings_window.after_cancel(show_status_audio_message.after_id)
        except AttributeError:
            pass  # First time, nothing to cancel
        show_status_audio_message.after_id = settings_window.after(5000, lambda: status_label_audio.config(text=""))


    def save_audio_settings():
        try:
            fs_val = int(sample_rate_var.get())
            bd_val = int(bit_depth_var.get())
            bs_val = int(block_size_var.get())

            warning = False

            # Recommended values
            recommended_fs = [44100, 48000, 96000, 192000]
            recommended_bd = [16, 24, 32]
            recommended_bs = [128, 256, 512, 1024, 2048, 4096]

            # Check sample rate and bit depth
            if fs_val not in recommended_fs or bd_val not in recommended_bd:
                warning = True

            # Check block size: must be power of 2
            if bs_val & (bs_val - 1) != 0:
                show_status_audio_message("Error: Block size must be a power of 2.", "red")
                return
            elif bs_val not in recommended_bs:
                warning = True

            # Apply values
            fs.set(fs_val)
            bit_depth.set(bd_val)
            block_size.set(bs_val)

            # Show messages
            if warning:
                show_status_audio_message(
                    "Warning: One or more values are not standard, but have been applied.",
                    "orange"
                )
            else:
                show_status_audio_message("Audio settings updated successfully.", "green")

        except ValueError:
            show_status_audio_message("Error: All values must be integers.", "red")


    # Create the Confirm button
    save_audio_btn = tk.Button(audio_page, text="Confirm", command=save_audio_settings)
    save_audio_btn.pack(pady=10)

    # Status message label (initially empty)
    status_label_audio = tk.Label(audio_page, text="", fg="green", bg="white")
    status_label_audio.pack(pady=5)

    #### Sidebar Buttons ####
    buttons = [
        ("Device", lambda: show_page("Device")),
        ("Audio", lambda: show_page("Audio")),
    ]

    for text, cmd in buttons:
        btn = tk.Button(sidebar, text=text, command=cmd, anchor="w", padx=10)
        btn.pack(fill="x", pady=2)

    # Show first page by default
    show_page("Device")

    # Close Window
    def on_close_set():
        time.sleep(0.5)
        settings_window.destroy()
    
    settings_window.protocol("WM_DELETE_WINDOW", on_close_set)