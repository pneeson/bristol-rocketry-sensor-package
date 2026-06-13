# Rocket Sensor Package — Raspberry Pi Setup Guide

This guide explains, step by step, how to wire the sensors, check the I2C bus, copy the
code onto the Raspberry Pi, install the required libraries, and run the flight logger.

It is written so you can follow it without prior Raspberry Pi experience.

---

## 1. What you need

**Hardware**
- Raspberry Pi Zero 2 W with a microSD card (8 GB or larger)
- Bosch **BMP388** altimeter (I2C)
- Sensirion **SEN55** air-quality sensor (I2C)
- A status **LED** + a resistor (220–330 Ω)
- Jumper wires

**Software (already prepared in this project)**
- `code/launch_sequence.py` — the flight logger (runs on the Pi)
- `code/bmp388.py`, `code/sen55.py` — sensor driver wrappers
- `code/requirements-hardware.txt` — the list of libraries to install
- `code/Data_Plotting_Code.py` — the graphing script (runs on a PC, **not** the Pi)

On the Pi you should have **Raspberry Pi OS** installed and be able to open a **Terminal**
(either directly on the Pi, or remotely over SSH).

---

## 2. Wire the sensors and LED

Both sensors share the one I2C bus. Power them from **3V3** (not 5 V).

| Signal | Connect to Pi pin | Pi pin name |
| --- | --- | --- |
| Sensor **SDA** | physical pin **3** | GPIO2 (SDA) |
| Sensor **SCL** | physical pin **5** | GPIO3 (SCL) |
| Sensor **VCC** | physical pin **1** | 3V3 |
| Sensor **GND** | physical pin **6** | GND |
| **LED +** (long leg, via resistor) | physical pin **11** | GPIO17 |
| **LED −** (short leg) | physical pin **9** | GND |

> Tip: connect both the BMP388 and the SEN55 to the same SDA/SCL/3V3/GND lines. Because
> they have different I2C addresses, they can share the bus without conflict.

**Default I2C addresses (you'll confirm these in Step 4):**
- BMP388 → `0x77` (some breakout boards use `0x76`)
- SEN55 → `0x69`

---

## 3. Enable I2C on the Pi (one time)

I2C is the communication system the Pi uses to talk to the sensors. It is **off by
default** and must be turned on once.

1. Open a Terminal on the Pi.
2. Run:
   ```bash
   sudo raspi-config
   ```
3. Use the arrow keys to choose **3 Interface Options** → **I5 I2C** → **Yes** (enable).
4. Select **Finish**. Reboot if it asks:
   ```bash
   sudo reboot
   ```

Install the I2C command-line tools (used for the check in the next step):
```bash
sudo apt-get update
sudo apt-get install -y i2c-tools python3-pip
```

---

## 4. The I2C check (very important)

This check confirms the Pi can actually "see" both sensors **before** you run any code.
It saves a lot of time, because most problems are wiring problems.

Run:
```bash
i2cdetect -y 1
```

The `1` means I2C bus 1 (the standard bus on the GPIO header).

**What a good result looks like** — you should see `69` and `77` (or `76`) in the grid:

```
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:                         -- -- -- -- -- -- -- --
...
60: -- -- -- -- -- -- -- -- -- 69 -- -- -- -- -- --
70: -- -- -- -- -- -- -- 77
```

- `69` = the SEN55 air-quality sensor
- `77` (or `76`) = the BMP388 altimeter

**How to read it / what to do:**

| What you see | What it means | What to do |
| --- | --- | --- |
| Both `69` and `77` (or `76`) appear | Both sensors detected — great | Continue to Step 5 |
| Only `69` appears | Altimeter not seen | Re-check BMP388 wiring. If it shows as `76`, see the note below |
| Only `77`/`76` appears | Air sensor not seen | Re-check SEN55 wiring and power |
| Nothing appears, all `--` | Bus/wiring/power problem | Check SDA↔pin3, SCL↔pin5, 3V3, GND; confirm I2C is enabled (Step 3) |
| `i2cdetect: command not found` | Tools not installed | Re-run the install command in Step 3 |

> **If your BMP388 shows up as `0x76` instead of `0x77`:** no action needed — the code
> auto-detects both addresses (it tries `0x77`, then `0x76`), so no launch-day edit is
> required either way.

---

## 5. Copy the code onto the Pi

Put the project's `code` folder onto the Pi (for example into your home folder so the
path is `~/rocket/code`). Any of these methods works:

- **USB drive:** copy the `code` folder onto a USB stick, then copy it onto the Pi.
- **SSH / SCP from your PC** (replace `pi` and the IP address with yours):
  ```bash
  scp -r "C:\Users\philip_admin\Documents\Personal\rocket project\code" pi@192.168.1.50:~/rocket
  ```
- **Git**, if the project is in a repository:
  ```bash
  git clone <your-repo-url> ~/rocket
  ```

After copying, move into the code folder on the Pi:
```bash
cd ~/rocket/code
```

You should see these files when you run `ls`:
```
launch_sequence.py  bmp388.py  sen55.py  led_patterns.py  requirements-hardware.txt  Data_Plotting_Code.py
```

---

## 6. Install the required libraries

These are the drivers the code needs to talk to the BMP388, the SEN55, and the LED.

From inside the `code` folder on the Pi:
```bash
pip3 install -r requirements-hardware.txt
```

This installs:
- `adafruit-circuitpython-bmp3xx` + `adafruit-blinka` — BMP388 altimeter driver
- `sensirion-i2c-driver` + `sensirion-i2c-sen5x` — SEN55 air-quality driver
- `gpiozero` + `lgpio` — to control the status LED

> If `pip3` reports an "externally managed environment" error on newer Raspberry Pi OS,
> add the flag:
> ```bash
> pip3 install -r requirements-hardware.txt --break-system-packages
> ```

---

## 7. Set the launch-day values

Open the flight code:
```bash
nano launch_sequence.py
```

Near the top, check/adjust the settings block:
- `SEA_LEVEL_PRESSURE` — set to the **local sea-level pressure (QNH) in hPa/mbar** for the
  day and place of launch (look it up from a weather source). This makes the altitude
  reading accurate.
- `LED_PIN` — must match the GPIO pin your LED is wired to (default `17`).
- The timing/threshold values (`COUNTDOWN_MS`, `LAUNCH_MARGIN_M`, etc.) — only change if
  your launch plan differs.

Save and exit nano with **Ctrl+O**, **Enter**, then **Ctrl+X**.

---

## 8. Run the flight logger

From inside the `code` folder:
```bash
python3 launch_sequence.py
```

**What you should see (the launch sequence):**
1. A **boot self-test** prints first (and is saved to `boot_<timestamp>.txt` — see below):
   ```
   ===== Rocket sensor boot self-test =====
   Run timestamp: 20260615_101500
   SD card: OK (boot file is writable)
   BMP388 altimeter: OK at 0x77  (test read: 134.2 m ASL, 997.5 hPa, 18.3 C)
   SEN55 pollution sensor: OK (comms established; fan + readings warm up before launch)
   Boot result: READY
   ```
   This is exactly what you want to check on the monitor on Monday — every line should say
   `OK` and the last line should say `READY`.
2. The **LED blinks slowly** while waiting on the pad.
3. After ~2 minutes: `Fan Started.` (the SEN55 fan powers up to warm up); the **LED goes solid** (armed).
4. After ~5 minutes: `Countdown complete, ground baseline: …m`.
5. On launch: `Liftoff` — the **LED blinks rapidly** and it begins logging.
6. After landing: `Landed`, then the **LED shows the two-blink "landed" pattern** (recovery).

To stop early during testing, press **Ctrl+C** (it closes the file cleanly).

### Output files (timestamped per run)

Every run stamps its files with **one shared timestamp** so a reboot can never overwrite a
previous run. For a run at 10:15:00 on 15 Jun 2026 you get:

- **`boot_20260615_101500.txt`** — the boot self-test result (sensors + SD card).
- **`flight_data_20260615_101500.csv`** — the per-row flight log. The `Altitude(m)` column is
  **height above the launch pad (AGL)** — the ground level captured at countdown is subtracted,
  so the apogee reads correctly even when launching from high ground.
- **`flight_summary_20260615_101500.txt`** — ground baseline (ASL) and the **apogee** (metres
  above the pad and in feet). Updated as the rocket climbs and again at landing, so the peak is
  saved even if power is lost during descent. Example:

```
Flight summary
Run timestamp: 20260615_101500
Ground baseline ASL (m): 134.20
Apogee ASL (m): 591.40
Apogee AGL / height above pad (m): 457.20
Apogee AGL (ft): 1500.0
Time to apogee since liftoff (ms): 10500
```

> Note: the Pi Zero has no real-time clock. If it has never seen the correct time (no
> internet), the timestamp may not be the true date, but it is still unique per run.

### LED signals at a glance

The single status LED tells you what stage the rocket is in. Learn these few patterns so
you can read it from a distance:

| LED behaviour | Meaning |
| --- | --- |
| **Fast blink** (first ~2 s) | Booting / starting up |
| **Slow blink** | On the pad, waiting (fan not started yet) |
| **Solid ON** | Armed and ready (fan started; counting down / waiting for liftoff) |
| **Rapid blink** | In flight — logging data |
| **Two quick blinks, then a pause** | Landed (recovery) |
| **Five fast blinks, then a pause** | Error — a sensor failed to start (check the console) |

The exact timings live in `code/led_patterns.py` if you ever want to adjust them.

### Data safety

During flight the code **forces data onto the SD card** (`flush` + `fsync`) every ~0.5 s
and again right before the file is closed (on landing, on Ctrl+C, or if it crashes). That
means a sudden power cut loses at most the last fraction of a second of data, not the whole
flight. Even so, prefer a **clean shutdown** when you can (`sudo poweroff`) rather than just
pulling power, to avoid any chance of SD-card corruption.

---

## 9. After the flight — make the graphs (on your PC)

The graphing step uses bigger libraries (pandas/matplotlib), so run it on a **PC/laptop**,
not the Pi:

1. Copy the run's `flight_data_<timestamp>.csv` off the Pi into the same folder as
   `Data_Plotting_Code.py`, and **rename it to `flight_data.csv`** (the plotting
   script reads that fixed name).
2. On the PC, install the plotting libraries once:
   ```bash
   pip install pandas numpy matplotlib
   ```
3. Run:
   ```bash
   python "Data_Plotting_Code.py"
   ```
4. You'll get **8 PNG graphs** (altitude, particulate matter, VOC/NOx, etc.) saved next to
   the script.

> Want to rehearse the whole thing without the rocket or hardware? The project's
> `testrig` folder simulates a full flight on a PC — see `testrig/README.md`.

---

## 10. Quick troubleshooting

| Problem | Likely cause | Fix |
| --- | --- | --- |
| `Setup Failed. … BMP388 not found` | Altimeter not detected on I2C (tried 0x77 and 0x76) | Re-run Step 4 `i2cdetect -y 1`; check wiring and power |
| `Setup Failed. … ` for the SEN55 | Air sensor not detected | Check SEN55 wiring and 3V3 power |
| `i2cdetect` shows nothing | I2C off or bad wiring | Re-do Step 3; recheck SDA/SCL/3V3/GND |
| `ModuleNotFoundError` when running | Libraries not installed | Re-run Step 6 (in the `code` folder) |
| `pip3: command not found` | pip not installed | `sudo apt-get install -y python3-pip` |
| LED never lights | Wrong pin or LED backwards | Check `LED_PIN`; flip the LED legs; confirm the resistor |
| No `flight_data.csv` created | It only logs **after** liftoff is detected | Confirm the altitude rises past the launch threshold |

---

### File reference

| File | Where it runs | Purpose |
| --- | --- | --- |
| `code/launch_sequence.py` | Raspberry Pi | Captures and logs flight data |
| `code/bmp388.py` | Raspberry Pi | BMP388 altimeter driver wrapper (auto-detects 0x77/0x76) |
| `code/sen55.py` | Raspberry Pi | SEN55 air-quality driver wrapper |
| `code/led_patterns.py` | Raspberry Pi | Status-LED signal patterns |
| `boot_<timestamp>.txt` (output) | created on the Pi | Boot self-test result (sensors + SD) |
| `flight_data_<timestamp>.csv` (output) | created on the Pi | Per-row flight log (altitude is AGL) |
| `flight_summary_<timestamp>.txt` (output) | created on the Pi | Ground baseline + apogee summary |
| `code/requirements-hardware.txt` | Raspberry Pi | List of libraries to install |
| `code/Data_Plotting_Code.py` | PC / laptop | Turns the CSV into 8 graphs |
| `testrig/` | PC / laptop | Simulates a flight to test the code |
