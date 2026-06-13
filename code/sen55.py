# -*- coding: utf-8 -*-
"""
sen55.py - thin wrapper around Sensirion's official SEN5x I2C driver for the Pi.

Why a wrapper? Sensirion's driver returns measurement objects whose values are
wrapped (e.g. ``values.mass_concentration_1p0.physical``,
``values.voc_index.scaled``). This wrapper flattens them to plain floats and exposes
a small ``SEN55`` class, so the flight code can simply read
``data.mass_concentration_1p0`` etc. The virtual test rig emulates this same class.

Install the underlying libraries on the Pi:
    pip3 install sensirion-i2c-driver sensirion-i2c-sen5x

The SEN55 has a fixed I2C address of 0x69 and lives on the Linux bus /dev/i2c-1.
After ``start_measurement()`` the sensor needs a short warm-up before values are
valid (the flight code starts it well before launch).
"""

from sensirion_i2c_driver import I2cConnection, LinuxI2cTransceiver
from sensirion_i2c_sen5x import Sen5xI2cDevice


class Measurement:
    """A flat, plain-float view of one SEN5x measurement."""

    def __init__(self, values):
        self.mass_concentration_1p0 = values.mass_concentration_1p0.physical
        self.mass_concentration_2p5 = values.mass_concentration_2p5.physical
        self.mass_concentration_4p0 = values.mass_concentration_4p0.physical
        self.mass_concentration_10p0 = values.mass_concentration_10p0.physical
        self.ambient_humidity = values.ambient_humidity.percent_rh
        self.ambient_temperature = values.ambient_temperature.degrees_celsius
        self.voc_index = values.voc_index.scaled
        self.nox_index = values.nox_index.scaled


class SEN55:
    def __init__(self, i2c_device="/dev/i2c-1"):
        self._transceiver = LinuxI2cTransceiver(i2c_device)
        self._device = Sen5xI2cDevice(I2cConnection(self._transceiver))

    def start_measurement(self):
        """Start measuring (turns the fan on)."""
        self._device.start_measurement()

    def stop_measurement(self):
        self._device.stop_measurement()

    def data_ready(self):
        """True once a fresh measurement is available since the last read."""
        return self._device.read_data_ready()

    def read_measured_values(self):
        return Measurement(self._device.read_measured_values())

    def close(self):
        self._transceiver.close()
