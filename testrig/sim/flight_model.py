"""Physics-based model of a model-rocket flight.

The model is a pure function of mission time (in ms): given a time it returns the
"true" altitude / pressure / temperature / air-quality values. Sensor noise and
fault injection are added later in :mod:`sim.context`, so this file stays clean and
easy to reason about.

Timeline (all relative to power-on, matching the flight code's logic):
  * t < ~2 min      : on the pad, fan off
  * t = ~2 min      : fan started (handled by the flight code)
  * t = 5 min       : countdown complete -> ground baseline captured
  * t = t_launch    : liftoff (default 5 s after the countdown)
  * boost -> coast  : climbs to apogee (default 1500 ft AGL)
  * parachute       : descends at a constant rate back to the ground
"""

from __future__ import annotations

import math
from dataclasses import dataclass

G = 9.80665  # m/s^2

FEET_PER_METER = 3.280839895


@dataclass
class FlightParams:
    apogee_agl_m: float = 457.2          # 1500 ft above ground level
    launch_site_alt_m: float = 0.0       # ground elevation above sea level
    sea_level_hpa: float = 1013.25       # for the barometric pressure model
    ground_temp_c: float = 15.0
    lapse_rate_c_per_m: float = 0.0065   # standard atmosphere temperature lapse
    t_launch_ms: int = 305_000           # liftoff: 5 s after the 5-minute countdown
    burn_time_s: float = 1.6             # motor burn duration
    descent_rate_mps: float = 5.0        # parachute descent speed
    # Air-quality baselines (ground level), loosely realistic urban values.
    pm1_base: float = 5.0                # ug/m^3
    pm25_base: float = 8.0              # ug/m^3
    pm10_base: float = 12.0             # ug/m^3
    voc_base: float = 100.0            # Sensirion VOC index (nominal 100)
    nox_base: float = 1.0              # Sensirion NOx index (nominal 1)

    @classmethod
    def from_feet(cls, apogee_ft: float = 1500.0, **kwargs) -> "FlightParams":
        return cls(apogee_agl_m=apogee_ft / FEET_PER_METER, **kwargs)


class FlightModel:
    def __init__(self, params: FlightParams):
        self.p = params
        self._solve_ascent()

    def _solve_ascent(self) -> None:
        """Pick a thrust acceleration that reaches the requested apogee.

        Powered phase (constant net accel a) for burn_time, then a ballistic coast
        decelerating at g until vertical velocity hits zero (apogee). Solving:
            apogee = 0.5*a*tb^2 + (a*tb)^2 / (2g)
        for a, given the burn time tb and target apogee.
        """
        p = self.p
        tb = p.burn_time_s
        A = (tb * tb) / (2 * G)
        B = 0.5 * tb * tb
        C = -p.apogee_agl_m
        disc = B * B - 4 * A * C
        self.a_net = (-B + math.sqrt(disc)) / (2 * A)
        self.v_burnout = self.a_net * tb
        self.h_burnout = 0.5 * self.a_net * tb * tb
        self.t_coast_s = self.v_burnout / G
        self.t_apogee_rel_s = tb + self.t_coast_s
        self.descent_time_s = p.apogee_agl_m / p.descent_rate_mps
        self.t_land_rel_s = self.t_apogee_rel_s + self.descent_time_s

    # -- core geometry -------------------------------------------------------
    def altitude_agl(self, t_ms: int) -> float:
        """Height above the launch pad, in metres."""
        p = self.p
        if t_ms < p.t_launch_ms:
            return 0.0
        rel = (t_ms - p.t_launch_ms) / 1000.0
        if rel <= self.t_apogee_rel_s:
            if rel <= p.burn_time_s:
                h = 0.5 * self.a_net * rel * rel
            else:
                tc = rel - p.burn_time_s
                h = self.h_burnout + self.v_burnout * tc - 0.5 * G * tc * tc
            return max(0.0, h)
        td = rel - self.t_apogee_rel_s
        return max(0.0, p.apogee_agl_m - p.descent_rate_mps * td)

    def altitude_asl(self, t_ms: int) -> float:
        """Altitude above sea level (what an Adafruit BMP3xx ``.altitude`` returns)."""
        return self.p.launch_site_alt_m + self.altitude_agl(t_ms)

    def temperature_c(self, t_ms: int) -> float:
        return self.p.ground_temp_c - self.p.lapse_rate_c_per_m * self.altitude_agl(t_ms)

    def pressure_hpa(self, t_ms: int) -> float:
        asl = self.altitude_asl(t_ms)
        return self.p.sea_level_hpa * (1.0 - 2.25577e-5 * asl) ** 5.25588

    def pollution(self, t_ms: int) -> dict:
        """Air quality vs altitude: cleaner (less PM) higher up, slight VOC/NOx drift."""
        p = self.p
        agl = self.altitude_agl(t_ms)
        frac = 0.0 if p.apogee_agl_m == 0 else min(1.0, agl / p.apogee_agl_m)
        cleaner = 1.0 - 0.4 * frac
        return {
            "pm1": p.pm1_base * cleaner,
            "pm25": p.pm25_base * cleaner,
            "pm10": p.pm10_base * cleaner,
            "voc": p.voc_base + 15.0 * frac,
            "nox": p.nox_base + 3.0 * frac,
        }

    # -- convenience ---------------------------------------------------------
    @property
    def t_land_ms(self) -> int:
        return self.p.t_launch_ms + int(self.t_land_rel_s * 1000)

    @property
    def apogee_ft(self) -> float:
        return self.p.apogee_agl_m * FEET_PER_METER
