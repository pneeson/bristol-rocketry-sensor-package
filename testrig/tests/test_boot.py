# -*- coding: utf-8 -*-
"""Tests for the boot self-test (boot.txt) and the shared per-run timestamp (issue 5)."""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TESTRIG = os.path.dirname(HERE)
if TESTRIG not in sys.path:
    sys.path.insert(0, TESTRIG)

import run_sim  # noqa: E402


def _read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def test_boot_file_reports_all_ok(tmp_path, capsys):
    res = run_sim.simulate("nominal", outdir=str(tmp_path), do_plot=False)
    assert res["boot_path"] is not None
    text = _read(res["boot_path"])
    assert "SD card: OK" in text
    assert "BMP388 altimeter: OK" in text
    assert "SEN55 pollution sensor: OK" in text
    assert "Boot result: READY" in text
    # It also prints to the console (for the monitor on the Pi).
    out = capsys.readouterr().out
    assert "Boot result: READY" in out


def test_boot_file_reports_sensor_failure(tmp_path):
    res = run_sim.simulate("altimeter-init-fail", outdir=str(tmp_path), do_plot=False)
    text = _read(res["boot_path"])
    assert "BMP388 altimeter: FAILED" in text
    assert "Boot result: ERROR" in text


def _run_id_from(path):
    # boot_<id>.txt / flight_data_<id>.csv / flight_summary_<id>.txt
    name = os.path.basename(path)
    return re.sub(r"^(boot|flight_data|flight_summary)_|\.(txt|csv)$", "", name)


def test_all_files_share_one_run_id(tmp_path):
    res = run_sim.simulate("nominal", outdir=str(tmp_path), do_plot=False)
    boot_id = _run_id_from(res["boot_path"])
    csv_id = _run_id_from(res["csv_path"])
    summary_id = _run_id_from(res["summary_path"])
    assert boot_id == csv_id == summary_id

    # The same value also appears inside the boot and summary file contents.
    assert f"Run ID: {boot_id}" in _read(res["boot_path"])
    assert f"Run ID: {summary_id}" in _read(res["summary_path"])


def test_boot_counter_increments(tmp_path):
    # Two runs in the same folder ("SD card") must get consecutive, unique ids.
    r1 = run_sim.simulate("nominal", outdir=str(tmp_path), do_plot=False)
    r2 = run_sim.simulate("nominal", outdir=str(tmp_path), do_plot=False)
    assert _run_id_from(r1["boot_path"]) == "0001"
    assert _run_id_from(r2["boot_path"]) == "0002"
    with open(os.path.join(str(tmp_path), "boot_count.txt")) as f:
        assert f.read().strip() == "2"
