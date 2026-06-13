# -*- coding: utf-8 -*-
"""Tests for AGL altitude logging (issue 4) and the flight_summary.txt file."""

import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
TESTRIG = os.path.dirname(HERE)
if TESTRIG not in sys.path:
    sys.path.insert(0, TESTRIG)

import run_sim  # noqa: E402

FEET_PER_METER = 3.280839895


def _read_summary(path):
    assert path is not None and os.path.exists(path), "flight summary was not written"
    values = {}
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            if ":" in line:
                key, _, val = line.partition(":")
                values[key.strip()] = val.strip()
    return values


def test_summary_file_has_baseline_and_apogee(tmp_path):
    res = run_sim.simulate("nominal", outdir=str(tmp_path), do_plot=False)
    s = _read_summary(res["summary_path"])
    assert "Ground baseline ASL (m)" in s
    assert "Apogee AGL / height above pad (m)" in s
    apogee_ft = float(s["Apogee AGL (ft)"])
    assert 1450 < apogee_ft < 1550


def test_csv_altitude_is_agl(tmp_path):
    res = run_sim.simulate("nominal", outdir=str(tmp_path), do_plot=False)
    df = pd.read_csv(res["csv_path"])
    # AGL: starts near the launch margin, peaks ~457 m, returns close to the ground.
    assert df["Altitude(m)"].min() < 12.0
    apogee_m = df["Altitude(m)"].max()
    assert 440 < apogee_m < 470  # ~457 m == 1500 ft above the pad


def test_csv_apogee_matches_summary(tmp_path):
    res = run_sim.simulate("nominal", outdir=str(tmp_path), do_plot=False)
    df = pd.read_csv(res["csv_path"])
    s = _read_summary(res["summary_path"])
    csv_apogee_m = df["Altitude(m)"].max()
    summary_apogee_m = float(s["Apogee AGL / height above pad (m)"])
    # The summary apogee should be at least the highest logged AGL row (it is the running max).
    assert summary_apogee_m >= csv_apogee_m - 1.0


def test_summary_survives_launch_site_above_sea_level(tmp_path):
    # With a launch site at 200 m ASL, AGL apogee must still be ~1500 ft (issue 4 fix).
    res = run_sim.simulate("nominal", outdir=str(tmp_path), do_plot=False, launch_alt_m=200.0)
    s = _read_summary(res["summary_path"])
    baseline = float(s["Ground baseline ASL (m)"])
    apogee_ft = float(s["Apogee AGL (ft)"])
    assert baseline > 150.0          # baseline reflects the elevated launch site
    assert 1450 < apogee_ft < 1550   # but height above pad is still ~1500 ft
