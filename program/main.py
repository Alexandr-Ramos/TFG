import sounddevice as sd
import numpy as np
import librosa as lb


def list_audio_devices():
    """List only valid audio input and output devices."""
    devices = sd.query_devices()
    
    print("\nAvailable input devices:")
    input_devices = {i: device for i, device in enumerate(devices) if device['max_input_channels'] > 0}
    for i, device in input_devices.items():
        print(f"{i}: {device['name']} (Input Channels: {device['max_input_channels']})")

    print("\nAvailable output devices:")
    output_devices = {i: device for i, device in enumerate(devices) if device['max_output_channels'] > 0}
    for i, device in output_devices.items():
        print(f"{i}: {device['name']} (Output Channels: {device['max_output_channels']})")

    return input_devices, output_devices

def select_device(prompt, devices):
    """Prompt the user to select a valid audio device and return the actual device information."""
    while True:
        try:
            device_index = int(input(f"{prompt}: "))
            if device_index in devices:
                device_info = sd.query_devices(device_index)
                max_channels = device_info['max_input_channels'] if 'Input' in prompt else device_info['max_output_channels']
                return device_index, max_channels
            else:
                print("Invalid selection. Please choose a valid device from the list.")
        except ValueError:
            print("Invalid input. Please enter a valid device number.")

def select_channel(prompt, max_channels):
    """Prompt the user to select a valid audio channel within a device."""
    while True:
        try:
            channel = int(input(f"{prompt} (0-{max_channels-1}): "))
            if 0 <= channel < max_channels:
                return channel
            else:
                print(f"Invalid selection. Please choose a channel between 0 and {max_channels-1}.")
        except ValueError:
            print("Invalid input. Please enter a valid channel number.")

# List available devices
input_devices, output_devices = list_audio_devices()

# Select devices and channels in the new order
print("\nSelect your audio devices and channels:")

# 1. Reference Input (Unprocessed Signal)
reference_input_device, ref_max_channels = select_device("Enter the number of the Reference Input Device (Unprocessed Signal)", input_devices)
reference_input_channel = select_channel("Select the Reference Input Channel", ref_max_channels)

# 2. Output to System (Processed Reference Signal)
output_to_sys_device, out_max_channels = select_device("Enter the number of the Output to System Device (Output to System Signal)", output_devices)
output_to_sys_channel = select_channel("Select the Output to System Channel", out_max_channels)

# 3. Input from System (Signal Captured from System)
input_from_sys_device, sys_max_channels = select_device("Enter the number of the Input from System Device (Captured System Signal)", input_devices)
input_from_sys_channel = select_channel("Select the Input from System Channel", sys_max_channels)

# Display selected devices and channels
print("\nSelected devices and channels:")
print(f"Reference Input Device: {sd.query_devices(reference_input_device)['name']} (Channel: {reference_input_channel})")
print(f"Output to System Device: {sd.query_devices(output_to_sys_device)['name']} (Channel: {output_to_sys_channel})")
print(f"Input from System Device: {sd.query_devices(input_from_sys_device)['name']} (Channel: {input_from_sys_channel})")
