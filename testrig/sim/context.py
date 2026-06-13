"""Holds the active simulation and turns the clean flight model into noisy, fault-prone
sensor reads that the fake driver modules (``bmp388``/``sen55``) consume.

There is one "active" :class:`Simulation` at a time. The fake drivers look it up via
:func:`active` at read time, so each run can swap in a fresh simulation.
"""

from __future__ import annotations

import random

from .clock import VirtualClock
from .flight_model import FlightModel
from .scenarios import Scenario

_active: "Simulation | None" = None


def active() -> "Simulation":
    if _active is None:
        raise RuntimeError(
            "No active simulation. The fake sensors must be driven via run_sim."
        )
    return _active


def set_active(sim: "Simulation | None") -> None:
    global _active
    _active = sim


class Simulation:
    def __init__(
        self,
        flight: FlightModel,
        clock: VirtualClock,
        scenario: Scenario,
        seed: int = 0,
    ):
        self.flight = flight
        self.clock = clock
        self.scenario = scenario
        self.rng = random.Random(seed)
        self.sen55_started = False

    # -- fault helpers -------------------------------------------------------
    def _hit(self, prob: float) -> bool:
        return prob > 0.0 and self.rng.random() < prob

    def _maybe_dropout(self, which: str) -> None:
        s = self.scenario
        prob = s.altimeter_dropout if which == "altimeter" else s.sen55_dropout
        if self._hit(prob):
            raise OSError(f"{which} I2C read timed out (simulated dropout)")

    # -- altimeter (BMP388) reads -------------------------------------------
    def read_altitude(self) -> float:
        self._maybe_dropout("altimeter")
        v = self.flight.altitude_asl(self.clock.now()) + self.rng.gauss(
            0, self.scenario.alt_noise
        )
        return float("nan") if self._hit(self.scenario.nan_prob) else v

    def read_pressure(self) -> float:
        self._maybe_dropout("altimeter")
        return self.flight.pressure_hpa(self.clock.now()) + self.rng.gauss(
            0, self.scenario.pressure_noise
        )

    def read_temperature(self) -> float:
        self._maybe_dropout("altimeter")
        return self.flight.temperature_c(self.clock.now()) + self.rng.gauss(
            0, self.scenario.temp_noise
        )

    # -- pollution (SEN55) reads --------------------------------------------
    def read_pollution(self) -> dict:
        self._maybe_dropout("sen55")
        d = self.flight.pollution(self.clock.now())
        n = self.scenario.pollution_noise

        def jitter(x: float) -> float:
            return max(0.0, x + self.rng.gauss(0, n))

        vals = {k: jitter(v) for k, v in d.items()}
        if self._hit(self.scenario.nan_prob):
            vals["pm25"] = float("nan")
        return vals
