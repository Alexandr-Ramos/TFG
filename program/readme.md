## RTA+C Program

This directory contains the Python source code for the entire program. The code is split into five main files:

- `rta+c.py` – The main entry point of the program. This file must be executed to launch the application. It also acts as a central hub that connects and manages the other modules.

- `config.py` – Manages key configuration variables that need to be accessed across multiple modules of the program.

- `settings.py` – Responsible for the settings window, where the user can configure important parameters such as input/output devices and sample rate.

- `analysis.py` – Responsible for the entire analysis window, including all implemented algorithms and visual plots (e.g., FFT, RTA, and delay measurement).

- `dsp.py` – Manages the correction window, including its graphical interface and processing algorithms such as the 31-band equalizer and signal bypass.

It also contains some incomplete or experimental versions in the `old_versions` folder.

For more accurate details about how the source code works, refer to the __Development of the Proposed Solution__ chapter of the report.