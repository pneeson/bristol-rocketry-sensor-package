# Code Testing — Virtual Test Rig

This project can be tested **end to end on a PC, with no Raspberry Pi and no sensors**. The
`testrig/` folder runs the *real* flight code (`code/launch_sequence.py`) against a simulated
rocket flight, produces the same output files a real flight would, and then runs the plotting
script on them. There is also an automated test suite.

Use this to check the code is solid before every hardware test or launch.

---

## 1. Install the test tools (once, on a PC)

```bash
cd testrig
pip install -r requirements.txt
```

This installs `pandas`, `numpy`, `matplotlib` and `pytest`.

---

## 2. Run a simulated flight

```bash
cd testrig
python run_sim.py
```

What happens:
1. The fake `bmp388`, `sen55` and `gpiozero` modules stand in for the hardware.
2. A physics model flies a rocket (boot → pad wait → boost → coast → apogee at ~1500 ft →
   parachute → landing), with the clock sped up so it finishes in seconds.
3. The **real** `launch_sequence.py` runs against it and writes `boot_*.txt`,
   `flight_data_*.csv` and `flight_summary_*.txt` into `testrig/output/`.
4. The plotting script (`code/Data_Plotting_Code.py`) runs and saves **8 PNG graphs** there too.

Open `testrig/output/` to see the CSV, the summary, and the graphs.

### Useful options

```bash
python run_sim.py --list                 # list all scenarios
python run_sim.py --scenario noisy       # run a specific scenario
python run_sim.py --no-plot              # skip the graph step
python run_sim.py --apogee-ft 1500       # change the target apogee
python run_sim.py --launch-alt 200       # launch site 200 m above sea level
python run_sim.py --seed 7               # change the random noise seed
```

### Scenarios (fault injection)

| Scenario | What it checks |
| --- | --- |
| `nominal` | A clean flight to 1500 ft. |
| `altimeter-init-fail` | BMP388 missing at boot → error state, no flight log. |
| `sen55-init-fail` | SEN55 missing at boot → error state. |
| `altimeter-dropout` | Intermittent altimeter timeouts; flight still completes. |
| `sen55-dropout` | Intermittent air-sensor timeouts; flight still completes. |
| `noisy` | High sensor noise. |
| `nan-data` | Occasional bad/NaN readings; plotting must cope. |

---

## 3. Run the automated tests

```bash
cd testrig
python -m pytest -q
```

The suite checks the things that matter for a real flight:
- **End-to-end:** the flight code runs, writes a valid CSV, and the plotting script makes all 8 graphs.
- **State machine:** pre-launch → warm-up → flight → recovery happen in the right order.
- **Failsafes:** a missing or intermittently failing sensor never crashes the logger.
- **SD durability:** data is `fsync`ed, and an SD sync error doesn't stop logging.
- **Altitude + apogee:** altitude is logged above the pad (AGL); the summary apogee is correct even from a high launch site.
- **Boot self-test + counter:** `boot.txt` reports sensor/SD health, and the boot counter gives each run a unique, increasing id.
- **LED patterns:** the blink patterns are correct and distinguishable.

---

## How it works (in brief)

- `testrig/stubs/` — fake `bmp388`, `sen55`, `gpiozero` so the flight code imports and runs on a PC.
- `testrig/sim/` — the flight physics model, a deterministic virtual clock, and the scenarios.
- `testrig/run_sim.py` — wires it together, runs the real flight code, then the plotting script.

For more detail see [testrig/README.md](testrig/README.md).
