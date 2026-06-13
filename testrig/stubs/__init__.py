"""Drop-in fake hardware modules.

These are injected into ``sys.modules`` as ``bmp388``, ``sen55`` and ``gpiozero`` so
the flight code imports them instead of the real (hardware-only) libraries and runs
unchanged on a PC.
"""
