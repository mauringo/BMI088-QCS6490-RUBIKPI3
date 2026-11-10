"""Opt-in hardware test: resets the attached BMI088; run with i2c access."""
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bmi088 import BMI088, BMI088Error

for cycle in range(2):
    with BMI088() as sensor:
        try:
            with BMI088():
                raise AssertionError("Concurrent access was allowed")
        except BMI088Error as exc:
            assert "lock" in str(exc), exc
        samples = []
        for _ in range(25):
            samples.append(sensor.read())
            time.sleep(0.1)
        distinct = len({s.acceleration_g for s in samples})
        assert distinct > 1, "Accelerometer readings did not change"
        assert all(b.timestamp > a.timestamp for a, b in zip(samples, samples[1:]))
        print(f"Cycle {cycle+1}: {len(samples)} samples, {distinct} distinct ACC readings")
    sensor.close()
    try:
        sensor.read()
        raise AssertionError("Read after close was allowed")
    except BMI088Error:
        pass
with BMI088(probe_only=True) as sensor:
    try:
        sensor.read()
        raise AssertionError("Probe-only reads were allowed")
    except BMI088Error:
        pass
print("Hardware smoke test passed")
