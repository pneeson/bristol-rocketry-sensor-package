"""Test scenarios, including fault injection, for the rig.

Each scenario tweaks sensor behaviour so we can prove the flight code's failsafes
actually work. Probabilities are "per sensor read".
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Scenario:
    name: str = "nominal"
    description: str = ""
    # Setup failures (constructor raises -> flight code goes to State_Error).
    altimeter_init_fail: bool = False
    sen55_init_fail: bool = False
    # Intermittent read failures (probability per read).
    altimeter_dropout: float = 0.0
    sen55_dropout: float = 0.0
    # Probability a read returns NaN/garbage instead of a value.
    nan_prob: float = 0.0
    # Gaussian sensor noise (std-dev).
    alt_noise: float = 0.3
    pressure_noise: float = 0.05
    temp_noise: float = 0.15
    pollution_noise: float = 0.4


SCENARIOS: dict[str, Scenario] = {
    "nominal": Scenario(
        name="nominal",
        description="Everything works; clean nominal flight to 1500 ft.",
    ),
    "altimeter-init-fail": Scenario(
        name="altimeter-init-fail",
        description="BMP388 missing at startup -> flight code should enter State_Error.",
        altimeter_init_fail=True,
    ),
    "sen55-init-fail": Scenario(
        name="sen55-init-fail",
        description="SEN55 missing at startup -> flight code should enter State_Error.",
        sen55_init_fail=True,
    ),
    "altimeter-dropout": Scenario(
        name="altimeter-dropout",
        description="BMP388 intermittently times out; flight should still complete.",
        altimeter_dropout=0.05,
    ),
    "sen55-dropout": Scenario(
        name="sen55-dropout",
        description="SEN55 intermittently times out; flight should still complete.",
        sen55_dropout=0.10,
    ),
    "noisy": Scenario(
        name="noisy",
        description="High sensor noise to stress thresholds and plots.",
        alt_noise=2.0,
        pressure_noise=0.5,
        temp_noise=1.0,
        pollution_noise=3.0,
    ),
    "nan-data": Scenario(
        name="nan-data",
        description="Occasional NaN readings; the plotting script's dropna() must cope.",
        nan_prob=0.03,
    ),
}
