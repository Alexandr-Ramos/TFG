import threading

# config.py - Shared objects
audio_stream_ext_in=None
audio_stream_out_to_sys=None
audio_stream_in_from_sys=None
audio_stream_bypass = None

buffer_data = None
buffer_lock = threading.Lock()

update_enabled = True

last_update_time = 0  # Timestamp of last buffer update

