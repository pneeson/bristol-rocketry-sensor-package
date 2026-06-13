# -*- coding: utf-8 -*-
"""Deterministic tests for the LED pattern engine (code/led_patterns.py)."""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(HERE))
CODE_DIR = os.path.join(PROJECT_ROOT, "code")
if CODE_DIR not in sys.path:
    sys.path.insert(0, CODE_DIR)

import led_patterns as lp  # noqa: E402


def test_solid_is_always_on():
    for t in (0, 1, 7, 123, 100_000):
        assert lp.led_signal(lp.ARMED, t) == 1


def test_blink_toggles_at_boundaries():
    # WAITING = (400, 400): on for [0,400), off for [400,800), then repeats.
    assert lp.led_signal(lp.WAITING, 0) == 1
    assert lp.led_signal(lp.WAITING, 399) == 1
    assert lp.led_signal(lp.WAITING, 400) == 0
    assert lp.led_signal(lp.WAITING, 799) == 0


def test_pattern_wraps_across_its_cycle():
    cycle = sum(lp.WAITING)  # 800 ms
    for t in (0, 50, 400, 750):
        assert lp.led_signal(lp.WAITING, t) == lp.led_signal(lp.WAITING, t + cycle)
        assert lp.led_signal(lp.WAITING, t) == lp.led_signal(lp.WAITING, t + 5 * cycle)


def _count_on_pulses(pattern):
    """Count rising edges (off/start -> on) over exactly one cycle, sampled at 1 ms."""
    cycle = sum(pattern)
    pulses = 0
    prev = 0
    for t in range(cycle):
        v = lp.led_signal(pattern, t)
        if v == 1 and prev == 0:
            pulses += 1
        prev = v
    return pulses


def test_error_burst_has_five_blinks():
    assert _count_on_pulses(lp.ERROR) == 5


def test_landed_has_two_blinks():
    assert _count_on_pulses(lp.LANDED) == 2


def test_patterns_are_nonempty_and_start_on():
    for pattern in (lp.BOOT, lp.WAITING, lp.ARMED, lp.FLIGHT, lp.LANDED, lp.ERROR):
        assert len(pattern) >= 1
        assert sum(pattern) > 0
        assert lp.led_signal(pattern, 0) == 1  # every pattern starts ON
