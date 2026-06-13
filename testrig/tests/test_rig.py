# -*- coding: utf-8 -*-
"""Automated checks for the flight code, run against the virtual test rig.

Run from the testrig folder with:   python -m pytest -v
"""

import os
import sys

import pandas as pd
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
TESTRIG = os.path.dirname(HERE)
if TESTRIG not in sys.path:
    sys.path.insert(0, TESTRIG)

import run_sim  # noqa: E402

# Exact columns Tatiana's plotting script depends on (order matters for the CSV header).
EXPECTED_COLUMNS = [
    "Time(ms)", "Altitude(m)", "Pressure", "Temp",
    "PM1.0", "PM2.5", "PM10.0", "VOC_Index", "NOX_Index",
]

EXPECTED_PNGS = [
    "Altitude_vs_Time.png",
    "PM_vs_time.png",
    "vox_nox_vs_time.png",
    "vox_vs_time.png",
    "nox_vs_time.png",
    "PM_vs_altitude.png",
    "vox_vs_altitude.png",
    "nox_vs_altitude.png",
]


# --- End-to-end -----------------------------------------------------------
def test_nominal_runs_and_plots(tmp_path):
    res = run_sim.simulate("nominal", outdir=str(tmp_path), do_plot=True)
    assert res["csv_exists"]
    assert res["rows"] > 100
    for png in EXPECTED_PNGS:
        assert (tmp_path / png).exists(), f"missing plot {png}"


def test_csv_schema_matches_plotting(tmp_path):
    res = run_sim.simulate("nominal", outdir=str(tmp_path), do_plot=False)
    df = pd.read_csv(res["csv_path"])
    assert list(df.columns) == EXPECTED_COLUMNS


def test_apogee_hits_target(tmp_path):
    res = run_sim.simulate("nominal", outdir=str(tmp_path), do_plot=False, apogee_ft=1500)
    df = pd.read_csv(res["csv_path"])
    apogee_ft = df["Altitude(m)"].max() * 3.280839895
    assert 1450 < apogee_ft < 1550


# --- State machine --------------------------------------------------------
def test_state_machine_order(tmp_path, capsys):
    run_sim.simulate("nominal", outdir=str(tmp_path), do_plot=False)
    out = capsys.readouterr().out
    i_fan = out.find("Fan Started")
    i_countdown = out.find("Countdown complete")
    i_liftoff = out.find("Liftoff")
    i_landed = out.find("Landed")
    assert -1 < i_fan < i_countdown < i_liftoff < i_landed


# --- Failsafes ------------------------------------------------------------
def test_altimeter_init_failure_no_launch(tmp_path, capsys):
    res = run_sim.simulate("altimeter-init-fail", outdir=str(tmp_path), do_plot=False)
    out = capsys.readouterr().out
    assert "BMP388 altimeter: FAILED" in out
    assert "Boot result: ERROR" in out
    assert not res["csv_exists"], "should not launch / log when the altimeter fails setup"


def test_sen55_init_failure_no_launch(tmp_path, capsys):
    res = run_sim.simulate("sen55-init-fail", outdir=str(tmp_path), do_plot=False)
    out = capsys.readouterr().out
    assert "SEN55 pollution sensor: FAILED" in out
    assert "Boot result: ERROR" in out
    assert not res["csv_exists"]


def test_altimeter_dropout_still_completes(tmp_path, capsys):
    res = run_sim.simulate("altimeter-dropout", outdir=str(tmp_path), do_plot=False)
    out = capsys.readouterr().out
    assert res["csv_exists"]
    assert "Landed" in out  # resilient to intermittent dropouts


def test_sen55_dropout_still_completes(tmp_path, capsys):
    res = run_sim.simulate("sen55-dropout", outdir=str(tmp_path), do_plot=False)
    out = capsys.readouterr().out
    assert res["csv_exists"]
    assert "Landed" in out


def test_nan_data_plotting_survives(tmp_path):
    res = run_sim.simulate("nan-data", outdir=str(tmp_path), do_plot=True)
    df_raw = pd.read_csv(res["csv_path"])
    assert df_raw.isna().any().any(), "nan-data scenario should inject some NaNs"
    assert (tmp_path / "Altitude_vs_Time.png").exists()


# --- Realism & determinism ------------------------------------------------
def test_flight_profile_is_realistic(tmp_path):
    res = run_sim.simulate("nominal", outdir=str(tmp_path), do_plot=False)
    df = pd.read_csv(res["csv_path"]).dropna()
    alt = df["Altitude(m)"].to_numpy()
    apogee_idx = alt.argmax()
    # climbs to apogee, then comes back down
    assert apogee_idx > 0
    assert alt[apogee_idx] > alt[0]
    assert alt[-1] < alt[apogee_idx]
    assert alt.min() < 10.0  # returns near the ground
    # pressure should fall as altitude rises (sanity on the barometric model)
    assert df["Pressure"].iloc[apogee_idx] < df["Pressure"].iloc[0]


def test_runs_are_reproducible(tmp_path):
    a = run_sim.simulate("noisy", outdir=str(tmp_path / "a"), do_plot=False, seed=42)
    b = run_sim.simulate("noisy", outdir=str(tmp_path / "b"), do_plot=False, seed=42)
    da = pd.read_csv(a["csv_path"])
    db = pd.read_csv(b["csv_path"])
    assert da["Altitude(m)"].max() == db["Altitude(m)"].max()
    assert len(da) == len(db)
