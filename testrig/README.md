# Rocket Sensor Virtual Test Rig

A pure-Python rig that runs Tatiana's flight code on a PC against a **simulated rocket
flight**, so the code can be exercised and proven correct without the Raspberry Pi,
the BMP388 altimeter, or the SEN55 air-quality sensor.

It runs the flight code, produces `flight_data.csv`, then runs the PC-side plotting
script on that CSV — the whole pipeline, end to end, in a few seconds.

---

## Quick start

```bash
# from this testrig/ folder
python -m pip install -r requirements.txt

# run a nominal flight (writes CSV + 8 PNG plots to ./output)
python run_sim.py

# list all scenarios
python run_sim.py --list

# run a fault-injection scenario
python run_sim.py --scenario noisy
python run_sim.py --scenario altimeter-init-fail --no-plot

# run the automated checks
python -m pytest -v
```

Outputs land in `testrig/output/` by default.

---

## How it works

The rig runs the **real** `../code/launch_sequence.py` unmodified. That file imports
`bmp388`, `sen55` and `gpiozero`; the rig provides **drop-in fakes** for those three so
no hardware (or Pi-only library) is needed, and patches the clock so the mission runs
instantly:

```
../code/launch_sequence.py   (the actual flight code that loads onto the Pi)
        |
        v  imports
   bmp388 / sen55 / gpiozero  <-- fakes in  stubs/
        |
        v  read values from
   the active Simulation       <-- sim/context.py
        |
        v  driven by
   a physics flight model      <-- sim/flight_model.py
   on a virtual clock          <-- sim/clock.py
```

- **Virtual clock** (`sim/clock.py`): the flight code's `time.monotonic_ns()` is mapped
  onto the virtual clock and `time.sleep()` is skipped, so the 5-minute countdown +
  flight runs in a fraction of a second, and every run is **deterministic** (seeded).
- **Flight model** (`sim/flight_model.py`): a real kinematic profile — powered boost,
  ballistic coast to apogee (default **1500 ft**), then parachute descent — plus a
  barometric pressure model, a temperature lapse, and altitude-correlated air quality.
- **Scenarios** (`sim/scenarios.py`): nominal plus fault injection (sensor missing at
  startup, intermittent dropouts, high noise, NaN readings).

### Folder layout

```
testrig/
  run_sim.py            # orchestrator + CLI (runs ../code/launch_sequence.py)
  requirements.txt
  sim/                  # the simulation core
    clock.py  flight_model.py  scenarios.py  context.py
  stubs/                # fake bmp388 / sen55 / gpiozero
  tests/                # pytest suite
  output/               # generated CSV + PNGs
```

---

## Scenarios

| Scenario              | What it tests                                                       |
|-----------------------|--------------------------------------------------------------------|
| `nominal`             | Clean flight to 1500 ft; full CSV + 8 plots.                       |
| `altimeter-init-fail` | BMP388 missing at boot → flight code should enter the error state. |
| `sen55-init-fail`     | SEN55 missing at boot → error state.                              |
| `altimeter-dropout`   | Intermittent altimeter timeouts; flight should still complete.     |
| `sen55-dropout`       | Intermittent SEN55 timeouts; flight should still complete.         |
| `noisy`               | High sensor noise, to stress thresholds and plots.                |
| `nan-data`            | Occasional NaN readings; the plotting `dropna()` must cope.        |

---

## Running on the real Raspberry Pi Zero 2W

`../code/launch_sequence.py` is now standard CPython for the Pi. On the device:

```bash
# enable I2C once:  sudo raspi-config -> Interface Options -> I2C -> Enable
cd code
pip3 install -r requirements-hardware.txt
i2cdetect -y 1          # confirm 0x77 (BMP388) and 0x69 (SEN55) appear
python3 launch_sequence.py
```

The Pi-only details live in the wrapper modules `code/bmp388.py` (Adafruit BMP3xx) and
`code/sen55.py` (Sensirion SEN5x). The rig fakes those exact modules, so the same flight
logic is what gets tested here and what runs on the rocket.

Before a launch, review the constants at the top of `launch_sequence.py`: `LED_PIN`,
`SEA_LEVEL_PRESSURE` (set to the day's local QNH), and the timing/threshold values.

---

## Findings the rig surfaced (now addressed)

1. **The original draft had blank placeholders that were syntax errors** (empty pins,
   empty `sea_level_pressure`, empty filename) — it couldn't run at all. These are now
   real values/constants at the top of `launch_sequence.py`.

2. **`Pollution_Data()` returned 3 values on the `None` path but the caller unpacks 5** —
   a latent crash. Fixed: it now returns 5 zeros on both failure paths.

3. **Altitude is logged above *sea level*, but the apogee/1500 ft analysis assumes height
   above the *launch pad*.** Still logged as ASL (left as a deliberate choice). On a real
   launch site above sea level, subtract the captured `ground_baseline` to get true AGL.
   The rig uses a sea-level launch site so the 1500 ft numbers line up.
