import numpy as np
import sounddevice as sd
import time
#import librosa as lb
import scipy.signal as signal
import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# from config import buffer_data, buffer_lock, delay_buffer
import config


block_size_ms = 100  # 100 ms


def open_analysis(root, lbl_ext_in, lbl_out_to_sys, lbl_in_from_sys,
        ext_in_dev, ext_in_ch, out_to_sys_dev, out_to_sys_ch, in_from_sys_dev, in_from_sys_ch,
        fs, bit_depth, block_size): 
    
    
    
    # Calculate number of samples from milliseconds
    block_size_fft = int(fs.get() * block_size_ms / 1000)

    # Find next power of two for N_FFT
    N_FFT = 2**int(np.ceil(np.log2(block_size_fft)))

    # Define delay buffer
    MAX_DELAY_SAMPLES = int(fs.get()*1) # 1 second size
    if config.delay_buffer is None or config.delay_buffer.shape[0] != MAX_DELAY_SAMPLES:
        config.delay_buffer = np.zeros((MAX_DELAY_SAMPLES,), dtype=np.float32) # Put zeros in the buffer
    if config.delay_samples == None:
        config.delay_samples = 0    # Initialize delay_samples

    global audio_stream
    audio_stream = None
    global stream_stop
    stream_stop = False

    analysis_window = tk.Toplevel(root)
    analysis_window.title("Analysis")
    analysis_window.geometry("800x600")

    # Stop stream when close window
    def on_closing():
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
            elif page_name == "Delay":
                load_delay_page()

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

            #Buffer to make FT
            long_buffer_sys = [] 
            long_buffer_ext = []
            def update_buffer(size: int, out_buffer: list, in_buffer: list, out_second: list, in_second: list) -> int:
                out_buffer.extend(in_buffer)
                out_second.extend(in_second)
                if len(out_buffer) > size:
                    # Erase first values
                    out_buffer[:] = out_buffer[-size:]
                if len(out_second) > size:
                    out_second[:] = out_second[-size:]
                return len(out_buffer)


            # Create canvas for the spectrogram plot --> Ext_In
            fig_ext, ax_ext = plt.subplots(figsize=(5, 3))
            canvas_ext = FigureCanvasTkAgg(fig_ext, master=ft_page)
            canvas_ext.get_tk_widget().pack(fill="both", expand=True)

            # Create canvas for the spectrogram plot --> In_from_Sys
            fig_sys, ax_sys = plt.subplots(figsize=(5, 3))
            canvas_sys = FigureCanvasTkAgg(fig_sys, master=ft_page)
            canvas_sys.get_tk_widget().pack(fill="both", expand=True)

            # Initialize plot line --> Ext_in
            freqs = np.fft.rfftfreq(N_FFT, d=1/fs.get())
            line_ext, = ax_ext.plot(freqs, np.zeros_like(freqs))
            ax_ext.set_xlim(10, 40000)  # Limit to 20kHz
            ax_ext.set_ylim(-80, 0)  # dB scale
            ax_ext.set_xscale("log")
            ax_ext.set_xlabel("Frequency (Hz)")
            ax_ext.set_ylabel("Amplitude (dB) EXT_IN")
            ax_ext.tick_params(axis='x', which='both', labelsize=8)
            ax_ext.grid(True, which='both', linestyle='--', linewidth=0.5)

            # Initialize plot line
            line_sys, = ax_sys.plot(freqs, np.zeros_like(freqs))
            ax_sys.set_xlim(10, 40000)  # Limit to 20kHz
            ax_sys.set_ylim(-80, 0)  # dB scale
            ax_sys.set_xscale("log")
            ax_sys.set_xlabel("Frequency (Hz)")
            ax_sys.set_ylabel("Amplitude (dB) IN_FROM_SYS")
            ax_sys.tick_params(axis='x', which='both', labelsize=8)
            ax_sys.grid(True, which='both', linestyle='--', linewidth=0.5)

            # Update spectrogram
            def update_spectrogram():
                from config import buffer_data, buffer_lock, delay_buffer, delay_samples

                if ext_in_ch.get() is None or ext_in_ch.get() < 1:
                    return
                if in_from_sys_ch.get() is None or in_from_sys_ch.get() < 1:
                    return

                with buffer_lock:
                    if buffer_data is None:
                        return
                    indata = buffer_data.copy()
                
                # Select the correct channel (convert 1-based index to 0-based)
                ext_data = indata[:, ext_in_ch.get() - 1]
                sys_data = indata[:, in_from_sys_ch.get() - 1]
                
                # Fill long buffer from short buffer
                while update_buffer(N_FFT, long_buffer_sys, sys_data, long_buffer_ext, ext_data) < N_FFT:
                    sys_data = indata[:, in_from_sys_ch.get() - 1]
                    ext_data = indata[:, ext_in_ch.get() - 1]

                sys_data=long_buffer_sys
                ext_data=long_buffer_ext        
    
                # Shift delay_buffer and insert new ext_in samples
                if config.delay_buffer is not None and config.delay_buffer.shape[0] >= len(ext_data):
                    config.delay_buffer[:] = np.roll(config.delay_buffer, -len(ext_data))
                    config.delay_buffer[-len(ext_data):] = ext_data

                if delay_buffer is None or len(delay_buffer) < delay_samples + N_FFT:
                    analysis_window.after(100, update_spectrogram)
                    return  # not enought sampes to start
                                
                if config.delay_samples is None or config.delay_samples < 0:
                    print("[ERROR] delay_samples is invalid")
                    analysis_window.after(100, update_spectrogram)
                    return

                if len(config.delay_buffer) < config.delay_samples + N_FFT:
                    print("[DEBUG] delay_buffer too short")
                    analysis_window.after(100, update_spectrogram)
                    return
                
                # Get delayed data
                if config.delay_samples == 0:
                    ext_data = config.delay_buffer[-N_FFT:]
                else:
                    ext_data = config.delay_buffer[-(config.delay_samples + N_FFT):-config.delay_samples]
                                
                if ext_data is None or len(ext_data) < N_FFT:
                    analysis_window.after(100, update_spectrogram)
                    print("[DEBUG] Delayed ext_data too short")
                    return

                # Apply window (Blackman)
                window_ext = np.blackman(len(ext_data))
                ext_data *= window_ext
                window_sys = np.blackman(len(sys_data))
                sys_data *= window_sys       

                # FFT
                ext_spectrum = np.abs(np.fft.rfft(ext_data, n=N_FFT))
                ext_spectrum = np.abs(ext_spectrum) / (np.sum(window_ext)/2) # Normalize energy
                ext_spectrum = 20 * np.log10(ext_spectrum + 1e-6)  # avoid log(0)
                
                sys_spectrum = np.abs(np.fft.rfft(sys_data, n=N_FFT))
                sys_spectrum = np.abs(sys_spectrum) / (np.sum(window_sys)/2) # Normalize energy
                sys_spectrum = 20 * np.log10(sys_spectrum + 1e-6)  # avoid log(0)

                # Update the plot
                line_ext.set_data(freqs, ext_spectrum)
                canvas_ext.draw()
                line_sys.set_data(freqs, sys_spectrum)
                canvas_sys.draw()
                
                analysis_window.after(20, update_spectrogram)

            analysis_window.after(0, update_spectrogram)


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
            def update_rta_bars():
                global buffer_data, buffer_lock

                with buffer_lock:
                    if buffer_data is None:
                        return
                    indata=buffer_data.copy()

                print(f"[DEBUG] indata shape: {indata.shape}") ######################## DEBUG
                
                # # global stream_stop
                # if stream_stop:
                #     return

                # if ext_in_dev.get() is None or ext_in_ch.get() is None:
                #     return
                
                # if not canvas_rta.get_tk_widget().winfo_exists():
                #     return  # If it isn't updatable, do not update.
                
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

            # # Start stream for 31-band RTA
            # def start_rta_stream():
            #     global audio_stream
            #     # stop_current_stream()

            #     # try:
            #     #     if audio_stream:
            #     #         audio_stream.stop()
            #     #         audio_stream.close()
            #     # except Exception:
            #     #     pass

            #     # if ext_in_dev.get() <= 0:
            #     #     return
                
            #     # audio_stream.stop()
            #     # audio_stream.close()
            #     #######################################################################33
            #     try: # Heare is not the problem

            #         audio_stream = sd.InputStream(
            #             device=ext_in_dev.get(),
            #             channels=ext_in_ch.get(),
            #             samplerate=fs.get(),
            #             blocksize=block_size_fft,
            #             callback=update_rta_bars
            #         )
            #         audio_stream.start()

            #         print("[INFO] Stream started")
            #     except Exception as e:
            #         print(f"[ERROR] Could not open input stream(RTA): {e}")
            #         audio_stream = None

            # analysis_window.after(0, start_rta_stream) #Start after GUI

            def periodic_update():
                from config import update_enabled
                if not update_enabled:
                    return

                update_rta_bars()
                root.after(100, periodic_update)  # actualització cada 100 ms

            analysis_window.after(0, periodic_update)


    #### PAGE 3: Delay ####
    def load_delay_page():
        if not loaded_pages.get("Delay"):
            loaded_pages["Delay"] = True 
            
            delay_page = tk.Frame(content, bg="white")
            pages["Delay"] = delay_page

            label_delay = tk.Label(delay_page, text="Delay Measurement", font=("Arial", 14))
            label_delay.pack(pady=10)

            delay_info = tk.Label(delay_page, text="Delay: -- samples / -- ms", font=("Arial", 12))
            delay_info.pack(pady=10)

            # Frame for plot
            plot_frame = tk.Frame(delay_page)
            plot_frame.pack(pady=10, fill="both", expand=True)

            # Create Matplotlib figure for correlation
            fig_corr, ax_corr = plt.subplots(figsize=(5, 3))
            canvas_corr = FigureCanvasTkAgg(fig_corr, master=plot_frame)
            canvas_corr.get_tk_widget().pack(fill="both", expand=True)

            # Line to update
            corr_line, = ax_corr.plot([], [])
            ax_corr.set_xlabel("Lag (samples)")
            ax_corr.set_ylabel("Correlation")
            ax_corr.grid(True, linestyle='--', linewidth=0.5)

            # Buffer size for 500 ms
            buffer_size = int(fs.get() * 0.5)  # 500 ms

            def update_delay():
                global buffer_data, buffer_lock

                with buffer_lock:
                    if buffer_data is None:
                        return
                    indata = buffer_data.copy()

                print(f"[DEBUG] indata shape: {indata.shape}") ######################## DEBUG
                
                # # global stream_stop
                # if stream_stop:
                #     return

                # if ext_in_dev.get() is None or ext_in_ch.get() is None or in_from_sys_dev.get() is None or in_from_sys_ch.get() is None:
                #     return

                sig1 = indata[:, ext_in_ch.get() - 1]
                sig2 = indata[:, in_from_sys_ch.get() - 1]

                # Normalize by RMS
                sig1 /= (np.sqrt(np.mean(sig1**2)) + 1e-6)
                sig2 /= (np.sqrt(np.mean(sig2**2)) + 1e-6)

                # Cross-correlation
                corr = signal.correlate(sig2, sig1, mode='full')
                lags = signal.correlation_lags(len(sig2), len(sig1), mode='full')

                #Absolute correlation
                corr_abs = np.abs(corr)

                #Mask positive delay
                min_samples = int(fs.get() * -0.010)  # -10 ms in samples
                idx_start = np.where(lags >= min_samples)[0][0]  # first index where lag >= min_samples

                corr_abs = corr_abs[idx_start:]
                lags = lags[idx_start:]

                lag_samples = lags[np.argmax(corr_abs)]
                delay_ms = (lag_samples / fs.get()) * 1000

                # Update labels
                delay_info.config(text=f"Delay: {lag_samples} samples / {delay_ms:.2f} ms")

                # Update correlation plot
                corr_line.set_data(lags, corr_abs)
                ax_corr.relim()
                ax_corr.autoscale_view()
                canvas_corr.get_tk_widget().after(0, canvas_corr.draw)


            # def start_delay_stream():
            #     global audio_stream

            #     try:
            #         audio_stream = sd.InputStream(
            #             device=ext_in_dev.get(),  # assuming same device for simplicity
            #             channels=max(ext_in_ch.get(), in_from_sys_ch.get()),
            #             samplerate=fs.get(),
            #             blocksize=buffer_size,
            #             callback=update_delay
            #         )
            #         audio_stream.start()
            #         print("[INFO] Delay stream started")
            #     except Exception as e:
            #         print(f"[ERROR] Could not open delay input stream: {e}")
            #         audio_stream = None

            # analysis_window.after(0, start_delay_stream)

            def periodic_update():
                from config import update_enabled
                if not update_enabled:
                    return

                update_delay()
                root.after(100, periodic_update)  # actualització cada 100 ms

            analysis_window.after(0, periodic_update)


            # Button to pause/resume stream
            def toggle_stream():
                global stream_stop
                stream_stop = not stream_stop
                if stream_stop:
                    btn_pause.config(text="Resume")
                else:
                    btn_pause.config(text="Pause")

            btn_pause = tk.Button(delay_page, text="Pause", command=toggle_stream, font=("Arial", 12))
            btn_pause.pack(pady=10)

    #### Sidebar Buttons ####
    buttons = [
        ("FT", lambda: show_page("FT", pages, loaded_pages)),
        ("31 Bands", lambda: show_page("31 Bands", pages, loaded_pages)),
        ("Delay", lambda: show_page("Delay", pages, loaded_pages)),
    ]

    for text, cmd in buttons:
        btn = tk.Button(sidebar, text=text, command=cmd, anchor="w", padx=10)
        btn.pack(fill="x", pady=2)

    # Show first page by default
    # show_page("31 Bands")
    # show_page("FT")