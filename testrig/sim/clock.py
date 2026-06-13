"""Deterministic virtual clock used to drive the flight code without waiting in real time.

The flight code reads ``time.monotonic_ns()`` once per main-loop iteration. The rig maps
that call onto :meth:`VirtualClock.tick`, which advances simulated time by a fixed step.
This makes the whole 5-minute countdown + flight run in a fraction of a second and,
crucially, makes every run perfectly reproducible (great for tests).
"""


class SimulationStop(BaseException):
    """Raised to break the flight code's ``while True`` loop when the mission window ends.

    It deliberately subclasses :class:`BaseException` (not :class:`Exception`) so that it
    propagates straight through the flight code's ``except Exception`` failsafes instead
    of being swallowed by them.
    """


class VirtualClock:
    def __init__(self, dt_ms: int = 20, max_ms: int | None = None):
        self.dt_ms = int(dt_ms)
        self.max_ms = max_ms
        self._now_ms = 0
        self.ticks = 0

    def tick(self) -> int:
        """Advance one loop step and return the new time in milliseconds."""
        self._now_ms += self.dt_ms
        self.ticks += 1
        if self.max_ms is not None and self._now_ms > self.max_ms:
            raise SimulationStop(
                f"Mission window of {self.max_ms} ms elapsed "
                f"({self.ticks} loop iterations)."
            )
        return self._now_ms

    def now(self) -> int:
        """Current simulated time in milliseconds (without advancing)."""
        return self._now_ms
