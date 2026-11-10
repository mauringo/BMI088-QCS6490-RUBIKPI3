"""Software tests: never open a physical I2C device."""
import math
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

from bmi088 import BMI088, BMI088Error

ROOT = Path(__file__).resolve().parents[1]


class PythonApiTests(unittest.TestCase):
    def fake_library(self):
        lib = Mock()
        lib.bmi088_open.return_value = 123
        lib.bmi088_read.return_value = 0
        return lib

    def test_context_closes_on_exception_and_close_is_idempotent(self):
        lib = self.fake_library()
        with patch('bmi088._load_library', return_value=lib):
            with self.assertRaisesRegex(ValueError, 'application error'):
                with BMI088() as sensor:
                    raise ValueError('application error')
            sensor.close()
            lib.bmi088_close.assert_called_once_with(123)
            with self.assertRaisesRegex(BMI088Error, 'closed'):
                sensor.read()

    def test_read_preserves_axis_order_and_units(self):
        lib = self.fake_library()
        def read(_handle, values):
            values[:] = [1, -2, 3, -4, 5, -6]
            return 0
        lib.bmi088_read.side_effect = read
        with patch('bmi088._load_library', return_value=lib):
            with BMI088() as sensor:
                sample = sensor.read()
        self.assertEqual(sample.acceleration_g, (1, -2, 3))
        self.assertEqual(sample.angular_velocity_dps, (-4, 5, -6))
        self.assertAlmostEqual(sample.acceleration_m_s2[1], -19.6133)
        self.assertTrue(math.isfinite(sample.timestamp))

    def test_transport_error_is_exposed(self):
        lib = self.fake_library()
        lib.bmi088_read.return_value = -1
        lib.bmi088_error.return_value = b'I2C READ addr=0x18 reg=0x12: failure'
        with patch('bmi088._load_library', return_value=lib):
            with BMI088() as sensor:
                with self.assertRaisesRegex(BMI088Error, 'addr=0x18 reg=0x12'):
                    sensor.read()

    def test_probe_rejects_reads(self):
        lib = self.fake_library()
        with patch('bmi088._load_library', return_value=lib):
            with BMI088(probe_only=True) as sensor:
                with self.assertRaisesRegex(BMI088Error, 'Probe-only'):
                    sensor.read()
        lib.bmi088_read.assert_not_called()

    def test_open_failure_does_not_close_invalid_handle(self):
        lib = self.fake_library()
        def fail(_path, _probe, error):
            error.value = b'Permission denied'
            return None
        lib.bmi088_open.side_effect = fail
        with patch('bmi088._load_library', return_value=lib):
            with self.assertRaisesRegex(BMI088Error, 'Permission denied'):
                BMI088()
        lib.bmi088_close.assert_not_called()


class NativeBoundaryTests(unittest.TestCase):
    def test_missing_device_returns_error_to_python(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(BMI088Error, 'No such file'):
                BMI088(str(Path(directory) / 'missing-device'))

    def test_regular_file_rejected_and_lock_released(self):
        with tempfile.NamedTemporaryFile() as device:
            for _ in range(2):
                with self.assertRaisesRegex(BMI088Error, 'I2C_RDWR'):
                    BMI088(device.name)

    def test_c_cli_missing_device(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [str(ROOT / 'bmi088'), '--device', str(Path(directory) / 'missing')],
                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 1)
        self.assertIn('No such file', result.stderr)

    def test_c_cli_rejects_invalid_count(self):
        result = subprocess.run([str(ROOT / 'bmi088'), '--samples', '-1'],
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 2)


if __name__ == '__main__':
    unittest.main()
