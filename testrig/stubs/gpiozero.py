"""Fake of the ``gpiozero`` library - just enough ``LED`` for the flight code.

The status LED has no observable effect in the simulator; this only needs to satisfy
the API so the logic under test can run.
"""

from __future__ import annotations


class LED:
    def __init__(self, pin=None, *args, **kwargs):
        self.pin = pin
        self._value = 0

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, v):
        self._value = int(v)

    def on(self):
        self._value = 1

    def off(self):
        self._value = 0

    def toggle(self):
        self._value = 0 if self._value else 1

    def blink(self, *args, **kwargs):
        pass

    def close(self):
        pass

    def __repr__(self):
        return f"LED(stub, pin={self.pin}, value={self._value})"
