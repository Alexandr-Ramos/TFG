import threading
import numpy as np

# config.py - Shared objects
audio_stream_ext_in=None
audio_stream_out_to_sys=None
audio_stream_in_from_sys=None
audio_stream_bypass = None

buffer_data = None # Input buffer with 2 channesl
buffer_output = None
buffer_lock = threading.Lock()
delay_buffer = None

delay_samples = None

update_enabled = True

last_update_time = 10000  # Timestamp of last buffer update

gain_values = None # Gain read from 31 Bands analysis and applyed in DSP

