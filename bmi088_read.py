#!/usr/bin/env python3
"""Command-line reader using the official Bosch-backed BMI088 Python library."""
import argparse
import math
import sys
import time

from bmi088 import BMI088, BMI088Error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", default="/dev/i2c-1", help="Linux I2C device")
    parser.add_argument("--samples", type=int, default=None, help="Stop after N samples")
    parser.add_argument("--interval", type=float, default=0.1, help="Seconds between reads (default: 0.1)")
    parser.add_argument("--probe", action="store_true", help="Check chip IDs without resetting/configuring sensors")
    args = parser.parse_args()
    if args.samples is not None and args.samples <= 0:
        parser.error("--samples must be positive")
    if not math.isfinite(args.interval) or args.interval <= 0:
        parser.error("--interval must be a finite positive number")
    try:
        with BMI088(args.device, probe_only=args.probe) as sensor:
            print("CHIP_ID: ACC=0x1e GYRO=0x0f")
            if args.probe:
                return 0
            print("ACC [g], GYRO [deg/s]. Unsynchronized readings. Ctrl+C to stop.")
            count = 0
            while args.samples is None or count < args.samples:
                sample = sensor.read()
                a, g = sample.acceleration_g, sample.angular_velocity_dps
                print(f"ACC {a[0]:+7.3f} {a[1]:+7.3f} {a[2]:+7.3f} | "
                      f"GYRO {g[0]:+8.2f} {g[1]:+8.2f} {g[2]:+8.2f}", flush=True)
                count += 1
                if args.samples is None or count < args.samples:
                    time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nStopped.")
    except BMI088Error as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
