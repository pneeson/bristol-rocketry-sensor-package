"""Fake ``sen55`` driver exposing the same API the flight code uses.

The flight code does:
    from sen55 import SEN55
    pollution_sensor = SEN55(i2c)
    pollution_sensor.start_measurement()
    data = pollution_sensor.read_measured_values()
    data.mass_concentration_1p0 / _2p5 / _10p0 / data.voc_index / data.nox_index
"""

from __future__ import annotations

from sim import context


class MeasuredValues:
    """Mirrors the attribute names the flight code reads off a SEN5x measurement."""

    def __init__(self, d: dict):
        self.mass_concentration_1p0 = d["pm1"]
        self.mass_concentration_2p5 = d["pm25"]
        self.mass_concentration_4p0 = d.get("pm4", d["pm25"])
        self.mass_concentration_10p0 = d["pm10"]
        self.voc_index = d["voc"]
        self.nox_index = d["nox"]


class SEN55:
    def __init__(self, i2c_device="/dev/i2c-1", *args, **kwargs):
        sim = context.active()
        if sim.scenario.sen55_init_fail:
            raise OSError("SEN55 not found on I2C bus (simulated init failure)")
        self._i2c_device = i2c_device
        self._sim = sim

    def data_ready(self):
        return True

    def start_measurement(self):
        self._sim.sen55_started = True

    def stop_measurement(self):
        self._sim.sen55_started = False

    def read_measured_values(self) -> MeasuredValues:
        return MeasuredValues(self._sim.read_pollution())
