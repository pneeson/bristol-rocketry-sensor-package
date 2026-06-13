# -*- coding: utf-8 -*-
"""
launch_sequence.py - Rocket sensor flight logger.

Runs on a Raspberry Pi Zero 2 W (Raspberry Pi OS, standard CPython 3). It logs
altitude / pressure / temperature from a Bosch BMP388 and air-quality data from a
Sensirion SEN55 to a CSV file during the flight, driven by a simple state machine:

    Pre-Launch -> Sensor Warmup -> Flight -> Recovery   (or -> Error on setup failure)

----------------------------------------------------------------------------------
HARDWARE
  * Raspberry Pi Zero 2 W
  * Bosch BMP388 barometric altimeter   (I2C, address 0x77 by default; some boards 0x76)
  * Sensirion SEN55 air-quality sensor  (I2C, address 0x69, fixed)
  * Status LED on a GPIO pin

WIRING (both sensors share the one I2C bus)
  * Sensor SDA -> GPIO2  (physical pin 3)
  * Sensor SCL -> GPIO3  (physical pin 5)
  * Sensor VCC -> 3V3, Sensor GND -> GND
  * LED -> GPIO17 (physical pin 11) through a current-limiting resistor to GND

ONE-TIME SETUP ON THE PI
  1. Enable I2C:        sudo raspi-config  ->  Interface Options  ->  I2C  ->  Enable
  2. Install drivers:   pip3 install -r requirements-hardware.txt
  3. Check wiring:      i2cdetect -y 1     (expect to see 0x77 and 0x69)

The low-level BMP388 / SEN55 drivers are wrapped by the local modules bmp388.py and
sen55.py, so this file stays simple. Those same module names are emulated by the
virtual test rig (../testrig), which means this exact logic can be tested on a PC
without any hardware.
"""

# ----- Imports
import os
import time

from bmp388 import BMP388_I2C
from sen55 import SEN55
from gpiozero import LED

from led_patterns import (
    led_signal, BOOT, WAITING, ARMED, FLIGHT, LANDED, ERROR, BOOT_BLINK_MS,
)


# ----- Configuration (review/adjust these for each launch) ------------------
LED_PIN = 17                      # BCM pin for the status LED
SEA_LEVEL_PRESSURE = 1013.25      # hPa (= mbar); set to the day's local QNH for accurate altitude
FEET_PER_METER = 3.280839895      # for reporting apogee in feet

# Every run is identified by a BOOT COUNTER stored on the SD card (the Pi Zero has no
# real-time clock, so a wall-clock timestamp can be wrong/repeat when it boots offline).
# All of a run's files share that id, e.g.:
#   boot_0001.txt, flight_data_0001.csv, flight_summary_0001.txt

FAN_WARMUP_MS = 2 * 60 * 1000     # start the SEN55 measurement (fan) 2 min before launch
COUNTDOWN_MS = 5 * 60 * 1000      # capture the ground baseline after a 5 min countdown
LAUNCH_MARGIN_M = 10.0            # climb above baseline that counts as "lifted off"
LANDING_MARGIN_M = 5.0            # height above baseline that counts as "landed"
MIN_FLIGHT_MS = 10 * 1000         # don't test for landing during the first 10 s of flight
SAMPLE_INTERVAL_S = 0.05          # main loop period (~20 Hz logging)
FSYNC_EVERY_ROWS = 10             # force data onto the SD card every N rows (~0.5 s)


# ----- Timing helpers -------------------------------------------------------
# MicroPython has time.ticks_ms(); on the Pi we use a monotonic clock instead, which
# is immune to system clock changes and never goes backwards.
def millis():
    """Milliseconds elapsed since the program started."""
    return time.monotonic_ns() // 1_000_000


def millis_diff(now, earlier):
    return now - earlier


def persist(f):
    """Flush Python's buffer AND force the OS to write it to the physical SD card.

    `flush()` alone only moves data into the operating system's cache; `os.fsync()`
    forces those bytes onto the card, which is what makes the log power-loss safe.
    A sync error must never stop logging, so it is caught and reported.
    """
    try:
        f.flush()
        os.fsync(f.fileno())
    except OSError as e:
        print("Persist (fsync) failed.", e)


BOOT_COUNT_FILE = "boot_count.txt"   # persistent run counter kept on the SD card


def next_boot_number():
    """Read, increment and persist a boot counter on the SD card.

    The Pi Zero has no real-time clock, so a wall-clock timestamp can be wrong (or repeat)
    when it boots with no network. A counter stored on the card instead gives every run a
    unique, monotonically increasing id that survives power cycles.
    """
    count = 0
    try:
        with open(BOOT_COUNT_FILE, "r") as f:
            count = int(f.read().strip() or "0")
    except (OSError, ValueError):
        count = 0
    count += 1
    try:
        with open(BOOT_COUNT_FILE, "w") as f:
            f.write(str(count))
            f.flush()
            os.fsync(f.fileno())
    except OSError as e:
        print("Could not update boot counter (SD problem?).", e)
    return count


def unique_run_id(boot_number):
    """Zero-padded run id from the boot number, guarded against name clashes in case the
    counter could not be saved on a previous run."""
    run_id = "{:04d}".format(boot_number)
    extra = 0
    while any(
        os.path.exists("{}_{}.{}".format(prefix, run_id, ext))
        for prefix, ext in (("boot", "txt"), ("flight_data", "csv"), ("flight_summary", "txt"))
    ):
        extra += 1
        run_id = "{:04d}_{}".format(boot_number, extra)
    return run_id


# A boot counter (not a clock) identifies each run, so ids are unique even without an RTC.
BOOT_NUMBER = next_boot_number()
RUN_ID = unique_run_id(BOOT_NUMBER)
CLOCK_TIME = time.strftime("%Y-%m-%d %H:%M:%S")   # best effort only; may be wrong without an RTC
BOOT_FILE = f"boot_{RUN_ID}.txt"
DATA_FILE = f"flight_data_{RUN_ID}.csv"
SUMMARY_FILE = f"flight_summary_{RUN_ID}.txt"


def write_summary(baseline_asl, apogee_asl_value, apogee_ms):
    """Write a small human-readable summary file with the ground baseline and apogee.

    Rewritten whenever a new maximum altitude is reached, so the apogee is safely on the
    card as the rocket falls (and survives a power loss during descent).
    """
    apogee_agl = apogee_asl_value - baseline_asl
    try:
        with open(SUMMARY_FILE, "w") as s:
            s.write("Flight summary\n")
            s.write(f"Run ID: {RUN_ID}\n")
            s.write(f"Boot number: {BOOT_NUMBER}\n")
            s.write(f"Clock time (best effort, no RTC): {CLOCK_TIME}\n")
            s.write(f"Ground baseline ASL (m): {baseline_asl:.2f}\n")
            s.write(f"Apogee ASL (m): {apogee_asl_value:.2f}\n")
            s.write(f"Apogee AGL / height above pad (m): {apogee_agl:.2f}\n")
            s.write(f"Apogee AGL (ft): {apogee_agl * FEET_PER_METER:.1f}\n")
            s.write(f"Time to apogee since liftoff (ms): {apogee_ms}\n")
            s.flush()
            os.fsync(s.fileno())
    except OSError as e:
        print("Summary write failed.", e)


# ---- Launch-state definitions (named constants for readability)
State_Error = -1
State_Pre_Launch = 0
State_Sensor_Warmup = 1
State_Flight = 2
State_Recovery = 3

# how the system is in the beginning
current_state = State_Pre_Launch
fan_has_started = False
ground_baseline = 0.0            # ground altitude above sea level (ASL), captured at countdown
flight_file = None
apogee_asl = 0.0                 # highest altitude (ASL) seen so far
apogee_time_ms = 0              # time since liftoff at which the apogee was reached
last_summary_apogee = 0.0      # last apogee value written to the summary file


# ----- Setting up hardware
led = LED(LED_PIN)


# ----- Boot self-test ------------------------------------------------------
# Checks the SD card and each sensor at power-on. Results are printed to the console
# (handy with a monitor on the Pi) AND saved to the boot file on the SD card, so the
# health of the package can be confirmed either way before launch.
boot_file = None
try:
    boot_file = open(BOOT_FILE, "w")
except OSError as e:
    print("Could not open boot file - SD card problem?", e)


def boot_log(line):
    """Print a boot-test line to the console and (if possible) the boot file."""
    print(line)
    if boot_file is not None:
        try:
            boot_file.write(line + "\n")
        except OSError:
            pass


boot_log("===== Rocket sensor boot self-test =====")
boot_log(f"Run ID: {RUN_ID}")
boot_log(f"Boot number: {BOOT_NUMBER}")
boot_log(f"Clock time (best effort, no RTC): {CLOCK_TIME}")
boot_log(
    "SD card: "
    + ("OK (boot file is writable)" if boot_file is not None
       else "FAILED (could not open boot file)")
)

# Altimeter (BMP388): set it up and take one test reading to confirm it returns data.
try:
    altimeter = BMP388_I2C()
    altimeter.sea_level_pressure = SEA_LEVEL_PRESSURE   # units are mbar = hPa
    test_alt, test_pressure, test_temp = (
        altimeter.altitude, altimeter.pressure, altimeter.temperature
    )
    boot_log(
        "BMP388 altimeter: OK at {}  (test read: {:.1f} m ASL, {:.1f} hPa, {:.1f} C)".format(
            hex(getattr(altimeter, "address", 0)), test_alt, test_pressure, test_temp
        )
    )
except Exception as e:
    boot_log(f"BMP388 altimeter: FAILED - {e}")
    altimeter = None
    current_state = State_Error

# Pollution sensor (SEN55): confirm I2C comms (its fan + readings warm up before launch).
try:
    pollution_sensor = SEN55()
    boot_log("SEN55 pollution sensor: OK (comms established; fan + readings warm up before launch)")
except Exception as e:
    boot_log(f"SEN55 pollution sensor: FAILED - {e}")
    pollution_sensor = None
    current_state = State_Error

if current_state == State_Error:
    boot_log("Boot result: ERROR - see the failure(s) above")
else:
    boot_log("Boot result: READY")

if boot_file is not None:
    persist(boot_file)     # make sure the boot log reaches the SD card
    boot_file.close()
    boot_file = None


# ----- Reading the Data
def Altimeter_Data():
    if altimeter is None:
        return 0.0, 0.0, 0.0
    try:
        # NOTE: altitude here is height ABOVE SEA LEVEL. For height above the launch
        # pad (what the apogee analysis wants), subtract ground_baseline.
        return altimeter.altitude, altimeter.pressure, altimeter.temperature
    except Exception as e:
        print("Altimeter Failed.", e)
        return 0.0, 0.0, 0.0


def Pollution_Data():
    # Always return 5 values so the caller's 5-way unpacking can never crash.
    if pollution_sensor is None:
        return 0.0, 0.0, 0.0, 0.0, 0.0
    try:
        data = pollution_sensor.read_measured_values()
        return (data.mass_concentration_1p0, data.mass_concentration_2p5,
                data.mass_concentration_10p0, data.voc_index, data.nox_index)
    except Exception as e:
        print("Pollution Sensor Failed.", e)
        return 0.0, 0.0, 0.0, 0.0, 0.0


# ----- Main Loop
SDwrite_counter = 0  # counts rows so we periodically flush to the SD card
start_time = millis()

try:                                     # failsafes to protect the data file if anything goes wrong
    while True:                          # establish current and hence elapsed times
        current_time = millis()
        elapsed_time = millis_diff(current_time, start_time)

        if current_state == State_Error:
            led.value = led_signal(ERROR, current_time)
            # five fast blinks + pause = something went wrong

        elif current_state == State_Pre_Launch:
            if not fan_has_started:
                if elapsed_time < BOOT_BLINK_MS:
                    led.value = led_signal(BOOT, current_time)      # fast blink = booting
                else:
                    led.value = led_signal(WAITING, current_time)   # slow blink = waiting on pad
            else:
                led.value = led_signal(ARMED, current_time)          # solid = armed / ready

            # the fan needs to be started a few minutes before launch, so:
            if elapsed_time >= FAN_WARMUP_MS and not fan_has_started:
                if pollution_sensor:
                    pollution_sensor.start_measurement()   # powers the fan; needs warm-up time
                    print("Fan Started.")
                fan_has_started = True

            # at the end of the 'countdown'
            if elapsed_time >= COUNTDOWN_MS:
                altitude, pressure, temperature = Altimeter_Data()
                ground_baseline = altitude
                apogee_asl = ground_baseline       # nothing higher than the pad yet
                last_summary_apogee = ground_baseline
                write_summary(ground_baseline, apogee_asl, apogee_time_ms)  # record the baseline ASL
                print(f"Countdown complete, ground baseline: {ground_baseline}m")
                current_state = State_Sensor_Warmup

        elif current_state == State_Sensor_Warmup:    # waiting on the pad, watching for liftoff
            led.value = led_signal(ARMED, current_time)   # solid = armed, ready to fly
            altitude, pressure, temperature = Altimeter_Data()

            if altitude > (ground_baseline + LAUNCH_MARGIN_M):   # climbed past the threshold
                print("Liftoff")
                flight_file = open(DATA_FILE, "w")   # open the log file and start writing to it
                flight_file.write("Time(ms),Altitude(m),Pressure,Temp,PM1.0,PM2.5,PM10.0,VOC_Index,NOX_Index\n")  # must match the plotting script
                persist(flight_file)   # make sure the file + header reach the card immediately
                flight_start_time = millis()
                current_state = State_Flight

        elif current_state == State_Flight:
            led.value = led_signal(FLIGHT, current_time)   # rapid blink = in flight, logging
            flight_time = millis_diff(current_time, flight_start_time)  # time since liftoff, for the CSV

            # read the data
            altitude, pressure, temperature = Altimeter_Data()
            pm1, pm25, pm10, voc, nox = Pollution_Data()

            # Log height ABOVE THE LAUNCH PAD (AGL). The sensor reports altitude above sea
            # level, so subtract the ground baseline. (Detection below still uses the raw
            # ASL `altitude` vs the baseline, which is equivalent.)
            altitude_agl = altitude - ground_baseline

            # format one CSV row and write it
            flight_data_string = f"{flight_time},{altitude_agl},{pressure},{temperature},{pm1},{pm25},{pm10},{voc},{nox}\n"
            flight_file.write(flight_data_string)

            # track the apogee and keep the summary file up to date as we climb/fall
            if altitude > apogee_asl:
                apogee_asl = altitude
                apogee_time_ms = flight_time
                if apogee_asl - last_summary_apogee >= 1.0:   # avoid rewriting on tiny changes
                    write_summary(ground_baseline, apogee_asl, apogee_time_ms)
                    last_summary_apogee = apogee_asl

            # force data onto the SD card periodically so little is lost if power is cut.
            # NOTE: the Pi logs to its own boot microSD (the OS filesystem), not a separate
            # SD breakout, so the Adafruit "SD card detect pin" guidance does not apply here.
            # For even stronger protection, a read-only / overlay root filesystem is the
            # optional next step (so a power cut cannot corrupt the OS partition).
            SDwrite_counter += 1
            if SDwrite_counter >= FSYNC_EVERY_ROWS:
                persist(flight_file)   # flush + fsync to the card
                SDwrite_counter = 0

            if flight_time > MIN_FLIGHT_MS and altitude < (ground_baseline + LANDING_MARGIN_M):
                print("Landed")
                current_state = State_Recovery

        elif current_state == State_Recovery:
            if flight_file is not None:
                persist(flight_file)   # final force-to-card before closing
                flight_file.close()
                flight_file = None
                # final apogee figure (in case the last new max was below the write threshold)
                write_summary(ground_baseline, apogee_asl, apogee_time_ms)

            led.value = led_signal(LANDED, current_time)   # two quick blinks + pause = landed

        time.sleep(SAMPLE_INTERVAL_S)

except KeyboardInterrupt:               # allow a clean Ctrl-C stop during testing
    print("Stopped by user.")
    if flight_file is not None:
        persist(flight_file)            # force-to-card before closing
        flight_file.close()

except Exception as fatal_error:
    print("Main loop crashed", fatal_error)

    if flight_file is not None:
        try:
            persist(flight_file)        # force-to-card before the emergency close
            flight_file.close()
            print("Emergency file save successful.")
        except Exception:
            print("Emergency file save unsuccessful...")


# the print statements are for debugging
# remember to set SEA_LEVEL_PRESSURE to the day's QNH and confirm LED_PIN / wiring
