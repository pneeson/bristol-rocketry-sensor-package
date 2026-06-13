# -*- coding: utf-8 -*-
"""Tests for SD-card write durability (the persist()/fsync path in launch_sequence.py).

The flight code calls os.fsync at runtime, so we monkeypatch os.fsync to observe it.
"""

import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
TESTRIG = os.path.dirname(HERE)
if TESTRIG not in sys.path:
    sys.path.insert(0, TESTRIG)

import run_sim  # noqa: E402

EXPECTED_COLUMNS = [
    "Time(ms)", "Altitude(m)", "Pressure", "Temp",
    "PM1.0", "PM2.5", "PM10.0", "VOC_Index", "NOX_Index",
]


def test_fsync_is_called_during_flight(tmp_path, monkeypatch):
    calls = {"n": 0}
    real_fsync = os.fsync

    def counting_fsync(fd):
        calls["n"] += 1
        return real_fsync(fd)

    monkeypatch.setattr(os, "fsync", counting_fsync)

    res = run_sim.simulate("nominal", outdir=str(tmp_path), do_plot=False)
    assert res["csv_exists"]
    # Header persist + one per FSYNC_EVERY_ROWS rows + final close -> many calls.
    assert calls["n"] > 0


def test_fsync_failure_does_not_crash_flight(tmp_path, monkeypatch):
    def failing_fsync(fd):
        raise OSError("simulated SD sync failure")

    monkeypatch.setattr(os, "fsync", failing_fsync)

    res = run_sim.simulate("nominal", outdir=str(tmp_path), do_plot=False)
    # Even though every fsync fails, persist() swallows it and the flight completes.
    assert res["csv_exists"]
    assert res["rows"] > 0


def test_csv_integrity_after_fsync_path(tmp_path):
    res = run_sim.simulate("nominal", outdir=str(tmp_path), do_plot=False)
    df = pd.read_csv(res["csv_path"])
    assert list(df.columns) == EXPECTED_COLUMNS
    assert len(df) > 0
