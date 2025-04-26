import numpy as np
import sounddevice as sd
import time
#import librosa as lb
import scipy.signal as signal
import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

block_size_fft = 2**13 #Fixed data for FFT
N_FFT = 2**14 #Fixed size for FFT


def open_analysis(root, lbl_ext_in, lbl_out_to_sys, lbl_in_from_sys,
        ext_in_dev, ext_in_ch, out_to_sys_dev, out_to_sys_ch, in_from_sys_dev, in_from_sys_ch,
        fs, bit_depth, block_size): 
    
    global audio_stream
    audio_stream = None
    global stream_stop
    stream_stop = False

    # Define a stop stream with some debugging
    def stop_current_stream():
        global audio_stream, stream_stop
    
        try:
            if audio_stream:
                stream_stop = True
                time.sleep(0.5)
                audio_stream.stop()
                audio_stream.close()
                audio_stream = None
                time.sleep(0.5)
                stream_stop = False
                print("[INFO] Stream stopped successfully")
        except Exception as e:
            print(f"[WARN] Could not stop stream: {e}")

  
    analysis_window = tk.Toplevel(root)
    analysis_window.title("Analysis")
    analysis_window.geometry("800x600")

    # Stop stream when close window
    def on_closing():
        stop_current_stream()
        analysis_window.destroy()

    analysis_window.protocol("WM_DELETE_WINDOW", on_closing)

    # Create container frames
    sidebar = tk.Frame(analysis_window, width=150, bg="#ddd")
    content = tk.Frame(analysis_window, bg="white")

    sidebar.pack(side="left", fill="y")
    content.pack(side="right", expand=True, fill="both")

    # Dictionary to hold pages ################################################
    pages = {}
    loaded_pages = {}

    def show_page(page_name, pages,loaded_pages):
        global audio_stream

        try:
            # Stop any existing stream
            stop_current_stream() 

            # Destroy and unload current pages
            for name, frame in pages.items():
                frame.pack_forget()
                frame.after(10, frame.destroy)  # Destroy the frame's widgets
            pages.clear()
            loaded_pages.clear()
            print("[INFO] Cleared previous pages")

            time.sleep(0.1) #Time for ALSA to close previous stream

            # Load and show new page
            if page_name == "FT":
                load_ft_page()
            elif page_name == "31 Bands":
                load_31bands_page()

            pages[page_name].pack(fill="both", expand=True)

        except Exception as e:
            print(f"[ERROR] Could not stop: {e}")


    #### PAGE 1: FT ####

    def load_ft_page():
        if not loaded_pages.get("FT"):
            loaded_pages["FT"] = True

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
            
                if stream_stop:
                    return

                if ext_in_dev.get() is None or ext_in_ch.get() is None: ##############################3
                    return  # Don't update if no device is selected
                
                if not canvas.get_tk_widget().winfo_exists():
                    return  # If it isn't updatable, do not update.

                # Select the correct channel (convert 1-based index to 0-based)
                audio_data = indata[:, ext_in_ch.get() - 1]

                # Apply window (Blackman)
                window = np.blackman(len(audio_data))
                window /= np.sum(window)
                windowed = audio_data * window

                # Zero-padding to N_FFT
                # if len(windowed) < N_FFT:
                #     padded = np.zeros(N_FFT)
                #     padded[:len(windowed)] = windowed
                # else:
                #     padded = windowed[:N_FFT]

                # FFT log
                # windowed[:]=1
                spectrum = np.abs(np.fft.rfft(windowed, n=N_FFT)) # recovering energy lost by zero-padding --> Not really
                spectrum = 20 * np.log10(spectrum + 1e-6)  # avoid log(0)

                # Update the plot
                line.set_ydata(spectrum)
                canvas.get_tk_widget().after(0, canvas.draw)

            # Start audio stream
            def start_ft_stream():
                global audio_stream

                try: # When opening second time, it go to error ###################################3
                    audio_stream = sd.InputStream(
                        device=ext_in_dev.get(),
                        channels=ext_in_ch.get(),
                        samplerate=fs.get(),
                        blocksize=block_size_fft, #Data input for fft
                        callback=update_spectrogram
                    )
                    audio_stream.start()

                except Exception as e:
                    print(f"[ERROR] Coud not open input stream (FT): {e}")

            # Start Stream
            analysis_window.after(0, start_ft_stream) #Start after GUI

    #### PAGE 2: 31 Bands ####
    def load_31bands_page():
        if not loaded_pages.get("31 Bands"):
            loaded_pages["31 Bands"] = True 
            
            band31_page = tk.Frame(content, bg="white")
            pages["31 Bands"] = band31_page

            label_31band = tk.Label(band31_page, text="31 Bands", font=("Arial", 14))
            label_31band.pack(pady=10)

            tk.Label(band31_page, text="31-Band RTA", font=("Arial", 14), bg="white").pack(pady=10)

            # Frequencies for 1/3 octave bands --> IEC 61260-3
            center_freqs = np.array([ # Change to logspace################################
                20, 25, 31.5, 40, 50, 63, 80, 100, 125, 160,
                200, 250, 315, 400, 500, 630, 800, 1000, 1250, 1600,
                2000, 2500, 3150, 4000, 5000, 6300, 8000, 10000, 12500, 16000, 20000
            ])

            # Create frame and canvas for bar plot
            rta_frame = tk.Frame(band31_page)
            rta_frame.pack(fill="both", expand=True, padx=20, pady=10)

            fig_rta, ax_rta = plt.subplots(figsize=(8, 3))
            x_positions = np.arange(len(center_freqs))
            bars = ax_rta.bar(x_positions, np.zeros_like(center_freqs), width=0.8, align='center', bottom = -80) #-80 = origin
            ax_rta.set_xticks(x_positions)
            ax_rta.set_xlim(20, 20000)
            ax_rta.set_ylim(-80, 0)
            ax_rta.set_xticks(x_positions)
            ax_rta.set_xticklabels([str(f) for f in center_freqs], rotation=45)
            ax_rta.set_xlabel("Frequency (Hz)")
            ax_rta.set_ylabel("Level (dB RMS)")
            ax_rta.grid(True, which='both', linestyle='--', linewidth=0.5)
            ax_rta.set_xlim(-0.5, len(center_freqs) - 0.5)

            canvas_rta = FigureCanvasTkAgg(fig_rta, master=rta_frame)
            canvas_rta.get_tk_widget().pack(fill="both", expand=True)

            # Design bandpass filters for each 1/3 octave band
            sos_filters = []
            for fc in center_freqs:
                low = fc / (2 ** (1/6))
                high = fc * (2 ** (1/6))

                # Skip bands that exceed Nyquist frequency
                if high >= fs.get() / 2:
                    continue

                # Butterworh filter
                sos = signal.butter(N=4, Wn=[low, high], btype='band', fs=fs.get(), output='sos')
                sos_filters.append(sos)

            # Callback to update bar graph
            def update_rta_bars(indata, frames, time, status):

                if stream_stop:
                    return

                if ext_in_dev.get() is None or ext_in_ch.get() is None:
                    return
                
                if not canvas_rta.get_tk_widget().winfo_exists():
                    return  # If it isn't updatable, do not update.
                
                audio_data = indata[:, ext_in_ch.get() - 1]
                # window = np.blackman(len(audio_data)) ###############################
                # audio_data *= window

                # Compute RMS in each band
                levels_db = []
                for sos in sos_filters:
                    filtered = signal.sosfilt(sos, audio_data)
                    rms = np.sqrt(np.mean(filtered ** 2))
                    db = 20 * np.log10(rms + 1e-6)
                    levels_db.append(db)

                # Update bar heights
                for bar, level in zip(bars, levels_db):
                    bar.set_height(level + 80) # form -80 dB to value.

                canvas_rta.get_tk_widget().after(0, canvas_rta.draw)

            # Start stream for 31-band RTA
            def start_rta_stream():
                global audio_stream
                # stop_current_stream()

                # try:
                #     if audio_stream:
                #         audio_stream.stop()
                #         audio_stream.close()
                # except Exception:
                #     pass

                # if ext_in_dev.get() <= 0:
                #     return
                
                # audio_stream.stop()
                # audio_stream.close()
                #######################################################################33
                try: # Heare is not the problem

                    audio_stream = sd.InputStream(
                        device=ext_in_dev.get(),
                        channels=ext_in_ch.get(),
                        samplerate=fs.get(),
                        blocksize=block_size_fft,
                        callback=update_rta_bars
                    )
                    audio_stream.start()

                    print("[INFO] Stream started")
                except Exception as e:
                    print(f"[ERROR] Could not open input stream(RTA): {e}")
                    audio_stream = None

            analysis_window.after(0, start_rta_stream) #Start after GUI

    #### Sidebar Buttons ####
    buttons = [
        ("FT", lambda: show_page("FT", pages, loaded_pages)),
        ("31 Bands", lambda: show_page("31 Bands", pages, loaded_pages)),
    ]

    for text, cmd in buttons:
        btn = tk.Button(sidebar, text=text, command=cmd, anchor="w", padx=10)
        btn.pack(fill="x", pady=2)

    # Show first page by default
    # show_page("31 Bands")
    # show_page("FT")