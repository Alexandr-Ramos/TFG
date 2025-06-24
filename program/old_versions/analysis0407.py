import numpy as np
import sounddevice as sd
#import librosa as lb
#import scipy.signal as signal
import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

block_size_fft = 8192 #Fixed data for FFT
N_FFT = 16384 #Fixed size for FFT

def open_analysis(root, lbl_ext_in, lbl_out_to_sys, lbl_in_from_sys,
        ext_in_dev, ext_in_ch, out_to_sys_dev, out_to_sys_ch, in_from_sys_dev, in_from_sys_ch,
        fs, bit_depth, block_size): 
    
    # global audio_stream
    # audio_stream = None
    
    analysis_window = tk.Toplevel(root)
    analysis_window.title("Analysis")
    analysis_window.geometry("800x600")

    # Create container frames
    sidebar = tk.Frame(analysis_window, width=150, bg="#ddd")
    content = tk.Frame(analysis_window, bg="white")

    sidebar.pack(side="left", fill="y")
    content.pack(side="right", expand=True, fill="both")

    # Dictionary to hold pages
    pages = {}

    def show_page(page_name):
        for name, frame in pages.items():
            frame.pack_forget()
        pages[page_name].pack(fill="both", expand=True)

        # if page_name == "FT":
        #     start_ft_stream()
        # elif page_name == "31 Bands":
        #     start_rta_stream()

    # ---------- PAGE 1: FT ----------

    ft_page = tk.Frame(content, bg="white")
    pages["FT"] = ft_page

    label_ft = tk.Label(ft_page, text="FT", font=("Arial", 14))
    label_ft.pack(pady=10)

    # Create frame for the spectrogram
    spectrogram_frame = tk.Frame(ft_page)
    spectrogram_frame.pack(pady=10, fill="both", expand=True)

    # Create canvas for the spectrogram plot
    fig, ax = plt.subplots(figsize=(5, 3))
    canvas = FigureCanvasTkAgg(fig, master=spectrogram_frame)
    canvas.get_tk_widget().pack(fill="both", expand=True)

    # Initialize plot line
    freqs = np.fft.rfftfreq(N_FFT, d=1/fs.get())
    line, = ax.plot(freqs, np.zeros_like(freqs))
    ax.set_xlim(10, 40000)  # Limit to 20kHz
    ax.set_ylim(-80, 0)  # dB scale
    ax.set_xscale("log")
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("Amplitude (dB)")
    ax.tick_params(axis='x', which='both', labelsize=8)
    ax.grid(True, which='both', linestyle='--', linewidth=0.5)

    # Update spectrogram
    def update_spectrogram(indata, frames, time, status):
        if ext_in_dev.get() is None or ext_in_ch.get() is None:
            return  # Don't update if no device is selected

        # Select the correct channel (convert 1-based index to 0-based)
        audio_data = indata[:, ext_in_ch.get() - 1]

        # Apply window (Blackman)
        window = np.blackman(len(audio_data))
        windowed = audio_data * window

        # Zero-padding to N_FFT
        if len(windowed) < N_FFT:
            padded = np.zeros(N_FFT)
            padded[:len(windowed)] = windowed
        else:
            padded = windowed[:N_FFT]

        # FFT log
        spectrum = np.abs(np.fft.rfft(padded)) / len(windowed) # recovering energy lost by zero-padding
        spectrum = 20 * np.log10(spectrum + 1e-6)  # avoid log(0)

        # Update the plot
        line.set_ydata(spectrum)
        canvas.draw()

    # Start audio stream
    def start_ft_stream():
        # global audio_stream
        # try:
        #     if audio_stream:
        #         audio_stream.stop()
        #         audio_stream.close()
        # except Exception:
        #     pass

        if ext_in_dev.get() <= 0:
            return
    
        audio_stream = sd.InputStream(
            device=ext_in_dev.get(),
            channels=ext_in_ch.get(),
            samplerate=fs.get(),
            blocksize=block_size_fft, #Data input for fft
            callback=update_spectrogram
        )
        audio_stream.start()

    start_ft_stream()

    # ---------- PAGE 2: 31 Bands ----------
    band31_page = tk.Frame(content, bg="white")
    pages["31 Bands"] = band31_page

    label_31band = tk.Label(band31_page, text="31 Bands", font=("Arial", 14))
    label_31band.pack(pady=10)

    # tk.Label(band31_page, text="31-Band RTA", font=("Arial", 14), bg="white").pack(pady=10)

    # # Frequencies for 1/3 octave bands --> IEC 61260-3
    # center_freqs = np.array([
    #     20, 25, 31.5, 40, 50, 63, 80, 100, 125, 160,
    #     200, 250, 315, 400, 500, 630, 800, 1000, 1250, 1600,
    #     2000, 2500, 3150, 4000, 5000, 6300, 8000, 10000, 12500, 16000, 20000
    # ])

    # # Create frame and canvas for bar plot
    # rta_frame = tk.Frame(band31_page)
    # rta_frame.pack(fill="both", expand=True, padx=20, pady=10)

    # fig_rta, ax_rta = plt.subplots(figsize=(8, 3))
    # bars = ax_rta.bar(center_freqs, np.zeros_like(center_freqs), width=10, align='center')
    # ax_rta.set_xscale("log")
    # ax_rta.set_xlim(20, 20000)
    # ax_rta.set_ylim(-80, 0)
    # ax_rta.set_xlabel("Frequency (Hz)")
    # ax_rta.set_ylabel("Level (dB RMS)")
    # ax_rta.grid(True, which='both', linestyle='--', linewidth=0.5)

    # canvas_rta = FigureCanvasTkAgg(fig_rta, master=rta_frame)
    # canvas_rta.get_tk_widget().pack(fill="both", expand=True)

    # # Design bandpass filters for each 1/3 octave band
    # sos_filters = []
    # for fc in center_freqs:
    #     low = fc / (2 ** (1/6))
    #     high = fc * (2 ** (1/6))

    #     # Skip bands that exceed Nyquist frequency
    #     if high >= fs.get() / 2:
    #         continue

    #     sos = signal.butter(N=4, Wn=[low, high], btype='band', fs=fs.get(), output='sos')
    #     sos_filters.append(sos)

    # # Callback to update bar graph
    # def update_rta_bars(indata, frames, time, status):
    #     if ext_in_dev.get() is None or ext_in_ch.get() is None:
    #         return

    #     audio_data = indata[:, ext_in_ch.get() - 1]
    #     window = np.blackman(len(audio_data)) ###############################
    #     audio_data *= window

    #     # Compute RMS in each band
    #     levels_db = []
    #     for sos in sos_filters:
    #         filtered = signal.sosfilt(sos, audio_data)
    #         rms = np.sqrt(np.mean(filtered ** 2))
    #         db = 20 * np.log10(rms + 1e-6)
    #         levels_db.append(db)

    #     # Update bar heights
    #     for bar, level in zip(bars, levels_db):
    #         bar.set_height(level)

    #     canvas_rta.draw()

    # # Start stream for 31-band RTA
    # def start_rta_stream():
    #     global audio_stream
    #     try:
    #         if audio_stream:
    #             audio_stream.stop()
    #             audio_stream.close()
    #     except Exception:
    #         pass

    #     if ext_in_dev.get() <= 0:
    #         return
        
    #     audio_stream = sd.InputStream(
    #         device=ext_in_dev.get(),
    #         channels=ext_in_ch.get(),
    #         samplerate=fs.get(),
    #         blocksize=block_size_fft,
    #         callback=update_rta_bars
    #     )
    #     audio_stream.start()

    # start_rta_stream()



    # ---------- Sidebar Buttons ----------
    buttons = [
        ("FT", lambda: show_page("FT")),
        ("31 Bands", lambda: show_page("31 Bands")),
    ]

    for text, cmd in buttons:
        btn = tk.Button(sidebar, text=text, command=cmd, anchor="w", padx=10)
        btn.pack(fill="x", pady=2)

    # Show first page by default
    show_page("FT")