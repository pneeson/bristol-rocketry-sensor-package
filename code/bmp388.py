# -*- coding: utf-8 -*-
"""
bmp388.py - thin wrapper around Adafruit's BMP3xx driver for the Raspberry Pi.

Why a wrapper? It gives the flight code a small, stable API
(``BMP388_I2C`` with ``.altitude`` / ``.pressure`` / ``.temperature`` and a settable
``.sea_level_pressure``) and keeps the Adafruit/Blinka setup details in one place.
The virtual test rig emulates this same class, so the flight code is identical whether
it runs on the Pi or in the simulator.

Install the underlying libraries on the Pi:
    pip3 install adafruit-circuitpython-bmp3xx adafruit-blinka

Datasheet addresses: 0x77 (default) or 0x76 (SDO tied to GND).
"""

import board
import adafruit_bmp3xx

# The BMP388 answers on one of these two I2C addresses depending on the board wiring
# (0x77 by default, or 0x76 when SDO is tied to GND). We try them in order so no code
# edit is needed on launch day regardless of which board is fitted.
DEFAULT_ADDRESSES = (0x77, 0x76)


class BMP388_I2C:
    def __init__(self, i2c=None, address=None):
        # board.I2C() opens the Pi's default I2C bus (SDA=GPIO2, SCL=GPIO3).
        if i2c is None:
            i2c = board.I2C()

        # If an explicit address is given, use only that; otherwise auto-detect.
        candidates = (address,) if address is not None else DEFAULT_ADDRESSES

        self._sensor = None
        last_error = None
        for addr in candidates:
            try:
                self._sensor = adafruit_bmp3xx.BMP3XX_I2C(i2c, address=addr)
                self.address = addr
                break
            except (ValueError, OSError, RuntimeError) as e:
                last_error = e   # not found at this address, try the next one
        if self._sensor is None:
            raise OSError(
                "BMP388 not found at any of {} ({})".format(
                    [hex(a) for a in candidates], last_error
                )
            )

        # Sensible defaults for altitude logging: oversample to reduce noise.
        self._sensor.pressure_oversampling = 8
        self._sensor.temperature_oversampling = 2

    @property
    def sea_level_pressure(self):
        return self._sensor.sea_level_pressure

    @sea_level_pressure.setter
    def sea_level_pressure(self, value):
        # Local sea-level pressure (hPa); altitude is derived from this.
        self._sensor.sea_level_pressure = value

    @property
    def altitude(self):
        """Altitude above sea level, in metres."""
        return self._sensor.altitude

    @property
    def pressure(self):
        """Barometric pressure, in hPa."""
        return self._sensor.pressure

    @property
    def temperature(self):
        """Temperature, in degrees Celsius."""
        return self._sensor.temperature
