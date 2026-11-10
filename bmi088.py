"""BMI088 Linux driver backed by the official Bosch BMI08x SensorAPI.

Build libbmi088.so with `make` before use. No third-party Python dependencies.
Use a context manager to release the bus lock deterministically.
"""
from __future__ import annotations

import ctypes
import os
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from time import monotonic


class BMI088Error(RuntimeError):
    """Bus access, initialization, or sensor communication failed."""


@dataclass(frozen=True)
class Sample:
    """Sequential, unsynchronized XYZ readings; timestamp is host monotonic time."""

    timestamp: float
    acceleration_g: tuple[float, float, float]
    angular_velocity_dps: tuple[float, float, float]

    @property
    def acceleration_m_s2(self) -> tuple[float, float, float]:
        """Acceleration including gravity, converted using standard gravity."""
        return tuple(value * 9.80665 for value in self.acceleration_g)


def _load_library():
    path = Path(__file__).resolve().with_name("libbmi088.so")
    try:
        lib = ctypes.CDLL(str(path))
    except OSError as exc:
        raise BMI088Error(f"Cannot load {path}. Run 'make' on this machine: {exc}") from exc
    lib.bmi088_open.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.POINTER(ctypes.c_char)]
    lib.bmi088_open.restype = ctypes.c_void_p
    lib.bmi088_read.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_double)]
    lib.bmi088_read.restype = ctypes.c_int
    lib.bmi088_error.argtypes = [ctypes.c_void_p]
    lib.bmi088_error.restype = ctypes.c_char_p
    lib.bmi088_close.argtypes = [ctypes.c_void_p]
    lib.bmi088_close.restype = None
    return lib


class BMI088:
    """Open and initialize ACC 0x18 and GYRO 0x68 on a Linux I2C device.

    Opening resets both sensors and loads Bosch's configuration. Ranges are
    +/-3 g and +/-500 deg/s with 100 Hz output rates. An advisory lock excludes
    other instances of this project's C/Python readers. Other I2C tools may
    ignore that lock. Do not use this object across fork().
    """

    def __init__(self, device: str = "/dev/i2c-1", *, probe_only: bool = False):
        self._lock = RLock()
        self._handle = None
        self._lib = _load_library()
        self._probe_only = probe_only
        error = ctypes.create_string_buffer(256)
        self._handle = self._lib.bmi088_open(os.fsencode(device), probe_only, error)
        if not self._handle:
            raise BMI088Error(error.value.decode(errors="replace"))

    def read(self) -> Sample:
        """Read one sample; raises BMI088Error on failure or a closed handle."""
        with self._lock:
            if not self._handle:
                raise BMI088Error("The sensor is closed")
            if self._probe_only:
                raise BMI088Error("Probe-only handles cannot read samples")
            values = (ctypes.c_double * 6)()
            if self._lib.bmi088_read(self._handle, values):
                raise BMI088Error(self._lib.bmi088_error(self._handle).decode(errors="replace"))
            return Sample(monotonic(), tuple(values[:3]), tuple(values[3:]))

    def close(self) -> None:
        """Release the device and lock. Safe to call more than once.

        Sensors remain configured and powered; closing does not reset them.
        """
        with self._lock:
            if self._handle:
                self._lib.bmi088_close(self._handle)
                self._handle = None

    def __enter__(self) -> BMI088:
        return self

    def __exit__(self, *_exc) -> None:
        self.close()
