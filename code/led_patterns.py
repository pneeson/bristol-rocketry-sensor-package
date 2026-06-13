# -*- coding: utf-8 -*-
"""
led_patterns.py - the status-LED "signal language" for the flight logger.

A small, non-blocking pattern engine: a *pattern* is a tuple of millisecond durations
that alternate ON, OFF, ON, OFF... (always starting ON). Given the current time,
`led_signal()` returns 1 (LED on) or 0 (LED off). Because the value is derived purely
from the clock, it never blocks the main loop and is fully deterministic - so it can be
unit-tested and runs identically in the virtual test rig.

Examples:
    (1,)            -> solid ON (one ON segment; nothing turns it off)
    (400, 400)      -> 400 ms on, 400 ms off, repeating (slow blink)
    (120, 120, 120, 640) -> two quick blinks, then a pause (repeating)

This module is pure Python with no hardware imports, so both the flight code and the
tests can import it directly.
"""

# ----- The signal set (see package/SETUP_GUIDE.md for the human-readable table) -----
# Kept deliberately small so an observer can read the LED from a distance.

BOOT = (120, 120)                  # fast blink: starting up / initialising
WAITING = (400, 400)               # slow blink: on the pad, fan not started yet
ARMED = (1,)                       # solid ON: ready / armed (and during sensor warmup)
FLIGHT = (80, 80)                  # rapid blink: launch detected, logging in flight
LANDED = (120, 120, 120, 640)      # two quick blinks + pause: landed / recovery
ERROR = (100, 100, 100, 100, 100, 100, 100, 100, 100, 700)  # five fast blinks + pause

# How long the BOOT pattern is shown at the very start (milliseconds).
BOOT_BLINK_MS = 2000


def led_signal(pattern, now_ms):
    """Return 1 (on) or 0 (off) for `pattern` at time `now_ms` (milliseconds).

    `pattern` is a tuple of durations in ms, alternating ON, OFF, ON, OFF...,
    starting with ON. The pattern repeats every `sum(pattern)` ms.
    """
    cycle = sum(pattern)
    if cycle <= 0:
        return 0
    t = now_ms % cycle
    on = True
    acc = 0
    for segment in pattern:
        acc += segment
        if t < acc:
            return 1 if on else 0
        on = not on
    return 0
