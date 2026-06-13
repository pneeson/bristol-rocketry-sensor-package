# -*- coding: utf-8 -*-
"""Virtual test rig orchestrator.

Runs Tatiana's flight code on this PC against a simulated rocket flight, produces
``flight_data.csv``, and then runs her PC-side plotting script on that CSV.

Usage examples:
    python run_sim.py                         # nominal flight + plots
    python run_sim.py --scenario noisy
    python run_sim.py --scenario altimeter-init-fail --no-plot
    python run_sim.py --apogee-ft 1500 --seed 7
    python run_sim.py --list
"""

from __future__ import annotations

import argparse
import glob
import os
import runpy
import shutil
import sys
import time as _time

# Run matplotlib without a display so the plotting script works headless.
os.environ.setdefault("MPLBACKEND", "Agg")

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(HERE)
CODE_DIR = os.path.join(PROJECT_ROOT, "code")
PLOTTING_SCRIPT = os.path.join(CODE_DIR, "Data_Plotting_Code.py")
# The rig runs Tatiana's REAL flight code, with the hardware modules faked out.
FLIGHT_SCRIPT = os.path.join(CODE_DIR, "launch_sequence.py")

if HERE not in sys.path:
    sys.path.insert(0, HERE)

from sim import context  # noqa: E402
from sim.clock import SimulationStop, VirtualClock  # noqa: E402
from sim.flight_model import FlightModel, FlightParams  # noqa: E402
from sim.scenarios import SCENARIOS  # noqa: E402


def _install_stubs() -> None:
    """Point the flight code's hardware imports (bmp388/sen55/gpiozero) at the fakes."""
    import stubs.bmp388 as bmp388
    import stubs.gpiozero as gpiozero
    import stubs.sen55 as sen55

    sys.modules["bmp388"] = bmp388
    sys.modules["sen55"] = sen55
    sys.modules["gpiozero"] = gpiozero

    # Let the flight code import its real (pure-Python) helper modules, e.g. led_patterns.
    # The faked hardware modules above still win because they are already in sys.modules.
    if CODE_DIR not in sys.path:
        sys.path.insert(0, CODE_DIR)


def simulate(
    scenario: str = "nominal",
    *,
    outdir: str | None = None,
    do_plot: bool = True,
    dt_ms: int = 50,
    seed: int = 0,
    apogee_ft: float = 1500.0,
    launch_alt_m: float = 0.0,
) -> dict:
    """Run one full simulation. Returns a small result dict."""
    if scenario not in SCENARIOS:
        raise ValueError(
            f"Unknown scenario '{scenario}'. Choose from: {', '.join(SCENARIOS)}"
        )
    if outdir is None:
        outdir = os.path.join(HERE, "output")
    os.makedirs(outdir, exist_ok=True)

    params = FlightParams.from_feet(
        apogee_ft=apogee_ft, launch_site_alt_m=launch_alt_m
    )
    flight = FlightModel(params)
    # Stop the flight code's infinite loop a bit after the rocket has landed.
    clock = VirtualClock(dt_ms=dt_ms, max_ms=flight.t_land_ms + 15_000)
    sim = context.Simulation(flight, clock, SCENARIOS[scenario], seed=seed)
    context.set_active(sim)
    _install_stubs()

    print(f"[rig] scenario={scenario}  target apogee={apogee_ft:.0f} ft  seed={seed}")
    print(f"[rig] running flight code ({os.path.basename(FLIGHT_SCRIPT)}) ...")

    # Drive the flight code's clock from the virtual clock and skip real sleeps, so the
    # whole mission runs in a moment. Restored afterwards so plotting libs are unaffected.
    orig_monotonic_ns = _time.monotonic_ns
    orig_sleep = _time.sleep
    _time.monotonic_ns = lambda: sim.clock.tick() * 1_000_000
    _time.sleep = lambda *a, **k: None

    prev_cwd = os.getcwd()
    os.chdir(outdir)
    try:
        runpy.run_path(FLIGHT_SCRIPT, run_name="__main__")
    except SimulationStop as stop:
        print(f"[rig] {stop}")
    finally:
        os.chdir(prev_cwd)
        _time.monotonic_ns = orig_monotonic_ns
        _time.sleep = orig_sleep

    # Output files are timestamped per run (e.g. flight_data_20260615_101500.csv); pick the
    # newest of each kind that this run produced.
    csv_path = _newest(outdir, "flight_data_*.csv")
    summary_path = _newest(outdir, "flight_summary_*.txt")
    boot_path = _newest(outdir, "boot_*.txt")

    csv_exists = csv_path is not None
    rows = 0
    if csv_exists:
        with open(csv_path, "r", encoding="utf-8") as fh:
            rows = max(0, sum(1 for _ in fh) - 1)  # minus header
    print(f"[rig] flight finished. CSV written: {csv_exists} ({rows} data rows)")

    plotted = False
    if do_plot and csv_exists and rows > 0:
        # The plotting script expects the fixed name 'flight_data.csv'; give it a copy.
        shutil.copyfile(csv_path, os.path.join(outdir, "flight_data.csv"))
        plotted = _run_plotting(outdir)

    return {
        "scenario": scenario,
        "csv_path": csv_path,
        "csv_exists": csv_exists,
        "rows": rows,
        "summary_path": summary_path,
        "boot_path": boot_path,
        "outdir": outdir,
        "plotted": plotted,
        "clock_ticks": clock.ticks,
    }


def _newest(outdir: str, pattern: str) -> str | None:
    """Return the most recently modified file matching pattern in outdir, or None."""
    matches = glob.glob(os.path.join(outdir, pattern))
    return max(matches, key=os.path.getmtime) if matches else None


def _run_plotting(outdir: str) -> bool:
    """Run Tatiana's plotting script against the produced CSV (in ``outdir``)."""
    import matplotlib

    matplotlib.use("Agg")
    print(f"[rig] running plotting code ({os.path.basename(PLOTTING_SCRIPT)}) ...")
    prev_cwd = os.getcwd()
    os.chdir(outdir)
    try:
        runpy.run_path(PLOTTING_SCRIPT, run_name="__main__")
    finally:
        os.chdir(prev_cwd)
    pngs = [f for f in os.listdir(outdir) if f.lower().endswith(".png")]
    print(f"[rig] plotting finished. {len(pngs)} PNG(s) in {outdir}")
    return len(pngs) > 0


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Rocket sensor virtual test rig.")
    p.add_argument("--scenario", default="nominal", help="scenario name (see --list)")
    p.add_argument("--outdir", default=None, help="output folder for CSV + PNGs")
    p.add_argument("--no-plot", action="store_true", help="skip the plotting step")
    p.add_argument("--dt", type=int, default=50, help="simulated ms per loop iteration")
    p.add_argument("--seed", type=int, default=0, help="RNG seed (reproducible noise)")
    p.add_argument("--apogee-ft", type=float, default=1500.0, help="target apogee (ft)")
    p.add_argument("--launch-alt", type=float, default=0.0, help="launch site alt (m ASL)")
    p.add_argument("--list", action="store_true", help="list scenarios and exit")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.list:
        print("Available scenarios:")
        for name, sc in SCENARIOS.items():
            print(f"  {name:<20} {sc.description}")
        return 0

    result = simulate(
        args.scenario,
        outdir=args.outdir,
        do_plot=not args.no_plot,
        dt_ms=args.dt,
        seed=args.seed,
        apogee_ft=args.apogee_ft,
        launch_alt_m=args.launch_alt,
    )
    print(f"[rig] done -> {result['outdir']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
