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

# Scroll bar for Window
class ScrollableFrame(tk.Frame):
    """A scrollable frame that expands horizontally and scrolls vertically."""
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)

        canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0)
        scrollbar = tk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.scrollable_frame = tk.Frame(canvas)

        # Add the scrollable frame to the canvas with a tag
        canvas_window = canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw", tags="frame")

        # Scroll region updates when scrollable frame resizes
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        # Adjust frame width to match canvas width
        def _on_canvas_configure(event):
            canvas.itemconfig("frame", width=event.width)

        canvas.bind("<Configure>", _on_canvas_configure)

        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")


block_size_ms = 100  # 100 ms for FT

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
        config.delay_samples = 100    # Initialize delay_samples

    global audio_stream
    audio_stream = None
    global stream_stop
    stream_stop = False

    analysis_window = tk.Toplevel(root)
    analysis_window.title("Analysis")
    analysis_window.geometry("1300x900")

    # Create scrollable area for main content
    scroll_frame = ScrollableFrame(analysis_window)
    scroll_frame.pack(side="right", fill="both", expand=True)

    # Stop stream when close window
    def on_closing():
        try:
 
            # Destroy and unload current pages
            config.update_enabled = False
            time.sleep(0.3) #Give time for end whatever was executing
            
            # Close all matplotlib figures to prevent memory leak
            for fig in plt.get_fignums():
                plt.close(fig)
            print("[INFO] Killed previous plots")

            for name, frame in pages.items():
                frame.pack_forget()
                frame.destroy()  # Destroy the frame's widgets
            pages.clear()
            loaded_pages.clear()
            print("[INFO] Cleared previous pages")
            
            # Destroy any active page
            for name in list(pages.keys()):
                pages[name].destroy()  # remove from memory
                del pages[name]
                del loaded_pages[name]
            print("[INFO] Deleted previous pages")

            time.sleep(0.3) #Give more time

            config.update_enabled = True
        
        except Exception as e:
            print(f"[ERROR] Could not stop: {e}")

        time.sleep(0.5)
        analysis_window.destroy()

    analysis_window.protocol("WM_DELETE_WINDOW", on_closing)

    # # Create container frames
    # sidebar = tk.Frame(scroll_frame.scrollable_frame, width=150, bg="#ddd")
    # content = tk.Frame(scroll_frame.scrollable_frame, bg="white")

    # Create sidebar (not scrollable)
    sidebar = tk.Frame(analysis_window, width=150, bg="#ddd")
    sidebar.pack(side="left", fill="y")

    # Use scrollable_frame for content
    content = tk.Frame(scroll_frame.scrollable_frame, bg="white")
    content.pack(fill="both", expand=True)

    # sidebar.pack(side="left", fill="y")
    # content.pack(side="right", expand=True, fill="both")

    # Dictionary to hold pages
    pages = {}
    loaded_pages = {}

    def show_page(page_name, pages,loaded_pages):
        from config import update_enabled
        global audio_stream

        try:
 
            # Destroy and unload current pages
            config.update_enabled = False
            time.sleep(0.3) #Give time for end whatever was executing
            
            # Close all matplotlib figures to prevent memory leak
            for fig in plt.get_fignums():
                plt.close(fig)
            print("[INFO] Killed previous plots")

            for name, frame in pages.items():
                frame.pack_forget()
                frame.destroy()  # Destroy the frame's widgets
            pages.clear()
            loaded_pages.clear()
            print("[INFO] Cleared previous pages")
            
            # Destroy any active page
            for name in list(pages.keys()):
                pages[name].destroy()  # remove from memory
                del pages[name]
                del loaded_pages[name]
            print("[INFO] Deleted previous pages")

            time.sleep(0.3) #Give more time

            config.update_enabled = True
            print(page_name)

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

            # Create canvas for the spectrogram plot --> Diference = System Gain
            fig_dif, ax_dif = plt.subplots(figsize=(5, 3))
            canvas_dif = FigureCanvasTkAgg(fig_dif, master=ft_page)
            canvas_dif.get_tk_widget().pack(fill="both", expand=True)

            # Initialize plot line --> Ext_in
            freqs = np.fft.rfftfreq(N_FFT, d=1/fs.get())
            line_ext, = ax_ext.plot(freqs, np.zeros_like(freqs))
            ax_ext.set_xlim(10, 40000)  # Limit to 20kHz
            ax_ext.set_ylim(-80, 0)  # dB scale
            ax_ext.set_xscale("log")
            # ax_ext.set_xlabel("Frequency [Hz]")
            ax_ext.set_ylabel("Amplitude [dB] EXT_IN")
            fig_ext.suptitle("External Input")
            ax_ext.tick_params(axis='x', which='both', labelsize=8)
            ax_ext.grid(True, which='both', linestyle='--', linewidth=0.5)

            # Initialize plot line --> in_from_sys
            line_sys, = ax_sys.plot(freqs, np.zeros_like(freqs))
            ax_sys.set_xlim(10, 40000)  # Limit to 20kHz
            ax_sys.set_ylim(-80, 0)  # dB scale
            ax_sys.set_xscale("log")
            # ax_sys.set_xlabel("Frequency [Hz]")
            ax_sys.set_ylabel("Amplitude [dB]")
            fig_sys.suptitle("Input from System")
            ax_sys.tick_params(axis='x', which='both', labelsize=8)
            ax_sys.grid(True, which='both', linestyle='--', linewidth=0.5)

            # Initialize plot line --> Diference / Gain
            line_dif, = ax_dif.plot(freqs, np.zeros_like(freqs))
            ax_dif.set_xlim(10, 40000)  # Limit to 20kHz
            ax_dif.set_ylim(-20, 20)  # dB scale
            ax_dif.set_xscale("log")
            ax_dif.set_xlabel("Frequency [Hz]")
            ax_dif.set_ylabel("Gain [dB]")
            fig_dif.suptitle("System Gain")
            ax_dif.tick_params(axis='x', which='both', labelsize=8)
            ax_dif.grid(True, which='both', linestyle='--', linewidth=0.5)

            # Frame to hold the entry and the Apply button in one line
            avarage_frame = tk.Frame(ft_page, bg="white")
            avarage_frame.pack(pady=10)

            #Label
            tk.Label(avarage_frame, text="Time avarage:", bg="white").pack(side="left", padx=(0, 5))

            # Entry box for integer value
            avar_entry = tk.Entry(avarage_frame, width=10)
            avar_entry.pack(side="left", padx=10)

            #Label
            tk.Label(avarage_frame, text="Frequency avarage:", bg="white").pack(side="left", padx=(0, 5))

            # Entry box for integer value
            avar_freq_entry = tk.Entry(avarage_frame, width=10)
            avar_freq_entry.pack(side="left", padx=10)

            # Apply button next to entry
            global avarage, freq_avarage
            avarage = 1
            freq_avarage = 1

            def apply_value():
                try:
                    global avarage, freq_avarage
                    avarage = int(avar_entry.get())
                    freq_avarage = int(avar_freq_entry.get())
                    print(f"[INFO] Applied value: {avarage} and {freq_avarage}")
                    
                except ValueError:
                    print("[WARN] Invalid integer input")

            apply_button = tk.Button(avarage_frame, text="Apply", command=apply_value)
            apply_button.pack(side="left", padx=5)

            # Create objects to store FFT and calculate avarage
            global avarage_ext_in, avarage_in_from_sys
            avarage_ext_in = None
            avarage_in_from_sys = None


            # Update spectrogram
            def update_spectrogram():
                from config import buffer_data, buffer_lock, delay_buffer, delay_samples

                global avarage_ext_in, avarage_in_from_sys, avarage, freq_avarage

                # global stream_stop
                if stream_stop:
                    return

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
              
                # Avarage
                if avarage_ext_in is None:
                    avarage_ext_in = ext_spectrum
                else:
                    avarage_ext_in = np.vstack([ext_spectrum, avarage_ext_in])
                    while avarage < avarage_ext_in.shape[0]:
                        avarage_ext_in = avarage_ext_in[:-1] # Delete last row

                if avarage_in_from_sys is None:
                    avarage_in_from_sys = sys_spectrum
                else:
                    avarage_in_from_sys = np.vstack([sys_spectrum, avarage_in_from_sys])
                    while avarage < avarage_in_from_sys.shape[0]:
                        avarage_in_from_sys = avarage_in_from_sys[:-1] # Delete last row

                ext_spectrum = np.mean(avarage_ext_in, axis=0)
                sys_spectrum = np.mean(avarage_in_from_sys, axis=0)

                #Frequency avarage
                if freq_avarage > 1:
                    if freq_avarage % 2 == 1: # Have to be odd
                        window = np.ones(freq_avarage) / freq_avarage
                        ext_spectrum = np.convolve(ext_spectrum, window, mode='same')
                        sys_spectrum = np.convolve(sys_spectrum, window, mode='same')
                    else:
                        freq_avarage = freq_avarage + 1 # Make it odd. 
                        window = np.ones(freq_avarage) / freq_avarage
                        ext_spectrum = np.convolve(ext_spectrum, window, mode='same')
                        sys_spectrum = np.convolve(sys_spectrum, window, mode='same')

                if ext_spectrum.ndim != 1 or ext_spectrum.shape[0] != freqs.shape[0]: # Ussually in first iteration happens.
                    # print("[ERROR] Averaged spectrum shape mismatch:", ext_spectrum.shape)
                    analysis_window.after(100, update_spectrogram)
                    return

                if sys_spectrum.ndim != 1 or sys_spectrum.shape[0] != freqs.shape[0]:
                    print("[ERROR] Averaged spectrum shape SYS mismatch:", sys_spectrum.shape)
                    analysis_window.after(100, update_spectrogram)
                    return

                #Calculations for difference
                dif_spectrum = sys_spectrum - ext_spectrum
               
                # Update the plot
                line_ext.set_data(freqs, ext_spectrum)
                canvas_ext.draw()
                line_sys.set_data(freqs, sys_spectrum)
                canvas_sys.draw()
                line_dif.set_data(freqs, dif_spectrum)
                canvas_dif.draw()

            def periodic_update_ft():
                from config import update_enabled
                if not update_enabled:
                    return

                update_spectrogram()
                root.after(100, periodic_update_ft)

            analysis_window.after(0, periodic_update_ft)

            # Button to pause/resume stream
            def toggle_stream():
                global stream_stop
                stream_stop = not stream_stop
                if stream_stop:
                    btn_pause.config(text="Resume")
                else:
                    btn_pause.config(text="Pause")

            btn_pause = tk.Button(ft_page, text="Pause", command=toggle_stream, font=("Arial", 12))
            btn_pause.pack(pady=10)


    #### PAGE 2: 31 Bands ####
    
    def load_31bands_page():
        if not loaded_pages.get("31 Bands"):
            loaded_pages["31 Bands"] = True 
            
            band31_page = tk.Frame(content, bg="white")
            pages["31 Bands"] = band31_page

            label_31band = tk.Label(band31_page, text="31 Bands RTA", font=("Arial", 14))
            label_31band.pack(pady=10)

            # Frequencies for 1/3 octave bands --> IEC 61260-3
            center_freqs = np.array([
                20, 25, 31.5, 40, 50, 63, 80, 100, 125, 160,
                200, 250, 315, 400, 500, 630, 800, 1000, 1250, 1600,
                2000, 2500, 3150, 4000, 5000, 6300, 8000, 10000, 12500, 16000, 20000
            ])

            # Create frame and canvas for bar plot --> Ext In
            ext_rta_frame = tk.Frame(band31_page)
            ext_rta_frame.pack(fill="both", expand=True, padx=20, pady=10)

            # Create frame and canvas for bar plot --> In from Sys
            sys_rta_frame = tk.Frame(band31_page)
            sys_rta_frame.pack(fill="both", expand=True, padx=20, pady=10)

            # Create frame and canvas for bar plot --> Diference / Gain
            dif_rta_frame = tk.Frame(band31_page)
            dif_rta_frame.pack(fill="both", expand=True, padx=20, pady=10)

            # Initialize plot --> Ext In
            ext_fig_rta, ext_ax_rta = plt.subplots(figsize=(8, 3))
            x_positions = np.arange(len(center_freqs))
            ext_bars = ext_ax_rta.bar(x_positions, np.zeros_like(center_freqs), width=0.8, align='center', bottom = -80) #-80 = origin
            ext_ax_rta.set_xticks(x_positions)
            ext_ax_rta.set_xlim(20, 20000)
            ext_ax_rta.set_ylim(-80, 0)
            ext_ax_rta.set_xticks(x_positions)
            ext_ax_rta.set_xticklabels(["" for f in center_freqs], rotation=45)
            # ext_ax_rta.set_xlabel("Frequency [Hz]")
            ext_ax_rta.set_ylabel("Level [dB RMS]")
            ext_fig_rta.suptitle("External Input")
            ext_ax_rta.grid(True, which='both', linestyle='--', linewidth=0.5)
            ext_ax_rta.set_xlim(-0.5, len(center_freqs) - 0.5)

            # Initialize plot --> In from Sys
            sys_fig_rta, sys_ax_rta = plt.subplots(figsize=(8, 3))
            x_positions = np.arange(len(center_freqs))
            sys_bars = sys_ax_rta.bar(x_positions, np.zeros_like(center_freqs), width=0.8, align='center', bottom = -80) #-80 = origin
            sys_ax_rta.set_xticks(x_positions)
            sys_ax_rta.set_xlim(20, 20000)
            sys_ax_rta.set_ylim(-80, 0)
            sys_ax_rta.set_xticks(x_positions)
            sys_ax_rta.set_xticklabels(["" for f in center_freqs], rotation=45)
            # sys_ax_rta.set_xlabel("Frequency [Hz]")
            sys_ax_rta.set_ylabel("Level [dB RMS]")
            sys_fig_rta.suptitle("Input form System")
            sys_ax_rta.grid(True, which='both', linestyle='--', linewidth=0.5)
            sys_ax_rta.set_xlim(-0.5, len(center_freqs) - 0.5)

            # Initialize plot --> Diference / gain
            dif_fig_rta, dif_ax_rta = plt.subplots(figsize=(8, 3))
            x_positions = np.arange(len(center_freqs))
            dif_bars = dif_ax_rta.bar(x_positions, np.zeros_like(center_freqs), width=0.8, align='center', bottom = -80) #-80 = origin
            dif_ax_rta.set_xticks(x_positions)
            dif_ax_rta.set_xlim(20, 20000)
            dif_ax_rta.set_ylim(-20, 20)
            dif_ax_rta.set_xticks(x_positions)
            dif_ax_rta.set_xticklabels([str(f) for f in center_freqs], rotation=45)
            dif_ax_rta.set_xlabel("Frequency [Hz]")
            dif_ax_rta.set_ylabel("Gain [dB]")
            dif_fig_rta.suptitle("System Gain")
            dif_ax_rta.grid(True, which='both', linestyle='--', linewidth=0.5)
            dif_ax_rta.set_xlim(-0.5, len(center_freqs) - 0.5)

            # Canvas --> Ext in
            ext_canvas_rta = FigureCanvasTkAgg(ext_fig_rta, master=ext_rta_frame)
            ext_canvas_rta.get_tk_widget().pack(fill="both", expand=True)

            # Canvas --> In from Sys
            sys_canvas_rta = FigureCanvasTkAgg(sys_fig_rta, master=sys_rta_frame)
            sys_canvas_rta.get_tk_widget().pack(fill="both", expand=True)

            # Canvas --> Diference / Gain
            dif_canvas_rta = FigureCanvasTkAgg(dif_fig_rta, master=dif_rta_frame)
            dif_canvas_rta.get_tk_widget().pack(fill="both", expand=True)

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

            # Frame to hold the entry and the Apply button in one line
            avarage_frame = tk.Frame(band31_page, bg="white")
            avarage_frame.pack(pady=10)

            #Label
            tk.Label(avarage_frame, text="Time avarage:", bg="white").pack(side="left", padx=(0, 5))

            # Entry box for integer value
            avar_entry = tk.Entry(avarage_frame, width=10)
            avar_entry.pack(side="left", padx=10)

            # Apply button next to entry
            global avarage
            avarage = 1

            def apply_value():
                try:
                    global avarage
                    avarage = int(avar_entry.get())
                    print(f"[INFO] Applied value: {avarage}")
                    
                except ValueError:
                    print("[WARN] Invalid integer input")

            apply_button = tk.Button(avarage_frame, text="Apply", command=apply_value)
            apply_button.pack(side="left", padx=5)

            # Create objects to store 31 bands and calculate avarage
            global avarage_ext_rta, avarage_sys_rta, dif_level_db
            avarage_ext_rta = None
            avarage_sys_rta = None
            dif_level_db = None

            # Callback to update bar graph
            def update_rta_bars():
                from config import buffer_data, buffer_lock, delay_buffer, delay_samples

                global avarage_ext_rta, avarage_sys_rta, avarage, stream_stop, dif_level_db

                # print("[DEBUG] update_rta_bars is alive") # When tkinter freezes, this still works

                # global stream_stop
                if stream_stop:
                    return

                if ext_in_ch.get() is None or ext_in_ch.get() < 1:
                    return
                if in_from_sys_ch.get() is None or in_from_sys_ch.get() < 1:
                    return

                with buffer_lock:
                    if buffer_data is None:
                        return
                    indata=buffer_data.copy()               
               
                # Select the correct channel (convert 1-based index to 0-based)
                ext_data = indata[:, ext_in_ch.get() - 1]
                sys_data = indata[:, in_from_sys_ch.get() - 1]

                # Shift delay_buffer and insert new ext_in samples
                if config.delay_buffer is not None and config.delay_buffer.shape[0] >= len(ext_data):
                    config.delay_buffer[:] = np.roll(config.delay_buffer, -len(ext_data))
                    config.delay_buffer[-len(ext_data):] = ext_data

                if delay_buffer is None or len(delay_buffer) < delay_samples + block_size.get():
                    analysis_window.after(100, update_rta_bars)
                    return  # not enought sampes to start
                                
                if config.delay_samples is None or config.delay_samples < 0:
                    print("[ERROR] delay_samples is invalid")
                    analysis_window.after(100, update_rta_bars)
                    return

                if len(config.delay_buffer) < config.delay_samples + block_size.get():
                    print("[DEBUG] delay_buffer too short")
                    analysis_window.after(100, update_rta_bars)
                    return
                
                # Get delayed data
                if config.delay_samples == 0:
                    ext_data = config.delay_buffer[-block_size.get():]
                else:
                    ext_data = config.delay_buffer[-(config.delay_samples + block_size.get()):-config.delay_samples]
                                
                if ext_data is None or len(ext_data) < block_size.get():
                    analysis_window.after(100, update_rta_bars)
                    print("[DEBUG] Delayed ext_data too short")
                    return

                # Compute RMS in each band --> ext
                ext_levels_db = []
                for sos in sos_filters:
                    filtered = signal.sosfilt(sos, ext_data)
                    rms = np.sqrt(np.mean(filtered ** 2))
                    db = 20 * np.log10(rms + 1e-6)
                    ext_levels_db.append(db)

                # Compute RMS in each band --> sys
                sys_levels_db = []
                for sos in sos_filters:
                    filtered = signal.sosfilt(sos, sys_data)
                    rms = np.sqrt(np.mean(filtered ** 2))
                    db = 20 * np.log10(rms + 1e-6)
                    sys_levels_db.append(db)

                # Avarage --> Same as spectral time Avarage
                if avarage_ext_rta is None:
                    avarage_ext_rta = np.array([ext_levels_db])
                else:
                    avarage_ext_rta = np.vstack([ext_levels_db, avarage_ext_rta])
                    while avarage < avarage_ext_rta.shape[0]:
                        avarage_ext_rta = avarage_ext_rta[:-1]

                if avarage_sys_rta is None:
                    avarage_sys_rta = np.array([sys_levels_db])
                else:
                    avarage_sys_rta = np.vstack([sys_levels_db, avarage_sys_rta])
                    while avarage < avarage_sys_rta.shape[0]:
                        avarage_sys_rta = avarage_sys_rta[:-1]
               
                ext_levels_db = np.mean(avarage_ext_rta, axis=0)
                sys_levels_db = np.mean(avarage_sys_rta, axis=0)

                # Diference / gain
                dif_level_db = [a - b for a, b in zip(sys_levels_db, ext_levels_db)]

                # print("[DEBUG] canvas_rta is being drawn") # When tkinter freezes, this still works

                # Update bar heights --> Ext
                for ext_bar, level in zip(ext_bars, ext_levels_db):
                    ext_bar.set_height(level + 80) # form -80 dB to value.
                ext_canvas_rta.draw()

                # Update bar heights --> Sys
                for sys_bar, level in zip(sys_bars, sys_levels_db):
                    sys_bar.set_height(level + 80) # form -80 dB to value.
                sys_canvas_rta.draw()

                # Update bar heights --> Dif
                for dif_bar, level in zip(dif_bars, dif_level_db):
                    dif_bar.set_height(abs(level))                # Always positive height
                    dif_bar.set_y(0 if level >= 0 else level)     # Start at 0 if positive, or at value if negative
                dif_canvas_rta.draw()
                
            def periodic_update_rta():
                from config import update_enabled
                if not update_enabled:
                    return
                update_rta_bars()
                root.after(100, periodic_update_rta)  # actualització cada 100 ms

            analysis_window.after(0, periodic_update_rta) 

            # Button to pause/resume stream
            def toggle_stream():
                global stream_stop
                stream_stop = not stream_stop
                if stream_stop:
                    btn_pause.config(text="Resume")
                else:
                    btn_pause.config(text="Pause")

            # Save Gain values
            button_frame = tk.Frame(band31_page, bg="white")
            button_frame.pack(pady=10)

            apply_msg = tk.Label(button_frame, text="", font=("Arial", 12), bg="white")
            apply_msg.pack(side="right", padx=5)

            def save_gain():
                global dif_level_db
                if dif_level_db is None:
                    apply_msg.config(text="NOT saved", font=("Arial", 12))
                else:
                    config.gain_values = dif_level_db
                    print(f"[INFO] Gain saved") # : {config.gain_values}")
                    apply_msg.config(text="Saved", font=("Arial", 12))

            btn_pause = tk.Button(button_frame, text="Pause", command=toggle_stream, font=("Arial", 12))
            btn_pause.pack(side="left", pady=10)

            btn_save = tk.Button(button_frame, text="Save Gain", command=save_gain, font=("Arial", 12))
            btn_save.pack(side="right", pady=10)


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

            global lag_samples
            lag_samples = 0

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
                from config import buffer_data, buffer_lock
                global lag_samples

                with buffer_lock:
                    if buffer_data is None:
                        return
                    indata = buffer_data.copy()

                # global stream_stop
                if stream_stop:
                    return

                if ext_in_dev.get() is None or ext_in_ch.get() is None or in_from_sys_dev.get() is None or in_from_sys_ch.get() is None:
                    return

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
                try:
                    delay_info.config(text=f"Delay: {lag_samples} samples / {delay_ms:.2f} ms")
                except tk.TclError:
                    return


                # Update correlation plot
                corr_line.set_data(lags, corr_abs)
                ax_corr.relim()
                ax_corr.autoscale_view()
                canvas_corr.get_tk_widget().after(0, canvas_corr.draw)

            def periodic_update_delay():
                from config import update_enabled
                if not update_enabled:
                    return

                update_delay()
                root.after(100, periodic_update_delay)  # actualització cada 100 ms

            analysis_window.after(0, periodic_update_delay)

            # Button to pause/resume stream
            def toggle_stream():
                global stream_stop
                stream_stop = not stream_stop
                if stream_stop:
                    btn_pause.config(text="Resume")
                else:
                    btn_pause.config(text="Pause")

            # Save delay value
            button_frame = tk.Frame(delay_page, bg="white")
            button_frame.pack(pady=10)

            apply_msg = tk.Label(button_frame, text="", font=("Arial", 12), bg="white")
            apply_msg.pack(side="right", padx=5)

            def save_delay():
                global lag_samples
                config.delay_samples = lag_samples
                apply_msg.config(text=f"Current value is {lag_samples} samples", font=("Arial", 12))

            btn_pause = tk.Button(button_frame, text="Pause", command=toggle_stream, font=("Arial", 12))
            btn_pause.pack(side="left", pady=10)

            btn_apply = tk.Button(button_frame, text="Apply", command=save_delay, font=("Arial", 12))
            btn_apply.pack(side="right", padx=10)

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