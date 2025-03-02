import sounddevice as sd
import numpy as np
import librosa

# Audio parameters
SR = 44100  # Sampling rate (Hz)
BUFFER_SIZE = 1024  # Buffer size for real-time processing

def process_audio(indata, frames, time, status):
    """Callback function to process real-time audio."""
    if status:
        print(status, flush=True)
    
    # Convert input buffer to numpy array
    audio = indata[:, 0]  # Take only one channel (mono)

    # Analyze with Librosa: compute root mean square (RMS) energy
    energy = np.sum(librosa.feature.rms(y=audio))

    # Apply a simple effect: amplification
    processed_audio = audio * 1.5  # Increase volume by 50%

    # Normalize to avoid distortion
    processed_audio = np.clip(processed_audio, -1.0, 1.0)

    # Send processed audio to output
    sd.play(processed_audio, samplerate=SR)

# Start audio capture
with sd.InputStream(callback=process_audio, channels=1, samplerate=SR, blocksize=BUFFER_SIZE):
    print("Listening... (Press Ctrl+C to stop)")
    try:
        while True:
            pass  # Keep the process running
    except KeyboardInterrupt:
        print("\nCapture stopped.")
