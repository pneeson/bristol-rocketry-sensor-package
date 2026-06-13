"""Fake ``bmp388`` driver exposing the same API the flight code uses.

The flight code does:
    from bmp388 import BMP388_I2C
    altimeter = BMP388_I2C(i2c)
    altimeter.sea_level_pressure = ...
    altimeter.altitude / altimeter.pressure / altimeter.temperature

Values come from the active flight simulation rather than real I2C traffic.
"""

from __future__ import annotations

from sim import context


class BMP388_I2C:
    def __init__(self, i2c=None, address=None):
        sim = context.active()
        if sim.scenario.altimeter_init_fail:
            raise OSError("BMP388 not found on I2C bus (simulated init failure)")
        self._i2c = i2c
        self._sim = sim
        # Mirror the real wrapper's auto-detect result (0x77 by default).
        self.address = address if address is not None else 0x77
        # Matches the real driver attribute the flight code sets.
        self.sea_level_pressure = 1013.25

    @property
    def altitude(self) -> float:
        return self._sim.read_altitude()

    @property
    def pressure(self) -> float:
        return self._sim.read_pressure()

    @property
    def temperature(self) -> float:
        return self._sim.read_temperature()
