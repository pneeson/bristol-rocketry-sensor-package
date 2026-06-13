# Bristol Rocketry Tournament — Sensor Package

Flight sensor package for the **Bristol Rocketry Tournament (BristolSEDS), Season 1 2025/26**.

**Author:** Tatiana Neeson

A Raspberry Pi Zero 2 W payload that, during flight, logs **altitude / pressure / temperature**
(Bosch BMP388 altimeter) and **air quality** (Sensirion SEN55 — PM1.0/2.5/10, VOC, NOx) to the
SD card, with a status LED, a power-up self-test, and robust, power-loss-safe data logging.
A separate PC script turns the logged data into graphs, and a virtual test rig lets the whole
thing be tested on a laptop with no hardware.

---

## Features

- **State-machine flight logic:** Pre-launch → sensor warm-up → flight → recovery, with an
  error state and failsafes so a single sensor fault never stops the logger.
- **Boot self-test:** at power-on it checks the SD card and both sensors, prints the result to
  the console (for a monitor on the Pi) and saves it to `boot_<timestamp>.txt`.
- **Status-LED "language":** distinct, distance-readable blink patterns for booting, waiting,
  armed, in-flight, landed, and error.
- **Power-loss-safe logging:** every row is `flush`ed and `fsync`ed to the card periodically and
  before shutdown, so a sudden power cut loses at most a fraction of a second of data.
- **Correct altitude:** logs height **above the launch pad (AGL)** and writes a
  `flight_summary_<timestamp>.txt` with the ground baseline and the **apogee** (m and ft),
  updated as the rocket climbs so the peak survives a power loss on descent.
- **Timestamped output files:** every run stamps its files with one shared timestamp, so a
  reboot on the pad can never overwrite a previous flight.
- **Virtual test rig:** simulates a full physics-based flight (boost → coast → apogee →
  parachute) to exercise the real flight code and the plotting script on a PC, with fault
  injection and an automated test suite.

---

## Hardware

- Raspberry Pi Zero 2 W (Raspberry Pi OS)
- Bosch **BMP388** barometric altimeter (I2C, address auto-detected: 0x77 or 0x76)
- Sensirion **SEN55** air-quality sensor (I2C, 0x69)
- Status LED + resistor on a GPIO pin

Full wiring and a step-by-step install/test guide are in **[SETUP_GUIDE.md](SETUP_GUIDE.md)**.

---

## Repository layout

```
.
├── README.md                 # this file
├── SETUP_GUIDE.md            # full Raspberry Pi setup + I2C check + run instructions
├── code/                     # the flight + analysis code
│   ├── launch_sequence.py    # main flight logger (runs on the Pi)
│   ├── bmp388.py             # BMP388 altimeter driver wrapper (auto-detects 0x77/0x76)
│   ├── sen55.py              # SEN55 air-quality driver wrapper
│   ├── led_patterns.py       # status-LED signal patterns
│   ├── requirements-hardware.txt  # Pi libraries to install
│   └── Data_Plotting_Code.py # PC-side script: turns the CSV into 8 graphs
└── testrig/                  # virtual test rig (simulator + automated tests)
    ├── run_sim.py            # runs the real flight code against a simulated flight
    ├── sim/                  # flight physics model, virtual clock, scenarios
    ├── stubs/                # fake bmp388 / sen55 / gpiozero hardware
    └── tests/                # pytest suite
```

---

## Quick start

### On the Raspberry Pi (capture the flight)

```bash
# enable I2C once:  sudo raspi-config -> Interface Options -> I2C -> Enable
cd code
pip3 install -r requirements-hardware.txt
i2cdetect -y 1          # confirm 0x77 (BMP388) and 0x69 (SEN55) appear
python3 launch_sequence.py
```

This produces `boot_<timestamp>.txt`, `flight_data_<timestamp>.csv`, and
`flight_summary_<timestamp>.txt`. See **[SETUP_GUIDE.md](SETUP_GUIDE.md)** for wiring, the LED
signal table, and troubleshooting.

### On a PC (make the graphs)

```bash
pip install pandas numpy matplotlib
# copy the run's flight_data_<timestamp>.csv next to the script and rename it flight_data.csv
cd code
python Data_Plotting_Code.py     # writes 8 PNG graphs
```

### Test it without hardware (virtual rig)

```bash
cd testrig
pip install -r requirements.txt
python run_sim.py                 # simulate a nominal flight + produce graphs
python run_sim.py --list          # list fault-injection scenarios
python -m pytest -q               # run the automated test suite
```

---

## Credits

Built for the Bristol Rocketry Tournament (BristolSEDS), Season 1 2025/26, by Tatiana Neeson.
