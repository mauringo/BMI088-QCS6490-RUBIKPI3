# BMI088 on Qualcomm QCS6490 / RUBIK Pi 3 — Linux and Python

Read a Bosch BMI088 over I2C on the Qualcomm QCS6490-based RUBIK Pi 3, running Ubuntu Server.
Both the C executable and the Python library use the **official Bosch
[BMI08x SensorAPI](https://github.com/boschsensortec/BMI08x_SensorAPI)** through
the same Linux backend. Python does not reimplement sensor registers or parse
a subprocess's console output.

## Quick start: Python without root

The project is already built on this board and `ubuntu` has been added to the
`i2c` group. Stop any existing reader with **Ctrl+C**, then run:

```bash
cd ~/BMI088
sg i2c -c 'python3 bmi088_read.py'
```

No `sudo` is needed. Stop with **Ctrl+C**.

After reconnecting over SSH, your new session should already have the group:

```bash
id
cd ~/BMI088
python3 bmi088_read.py
```

Alternatively, run `newgrp i2c` once in an existing shell. It starts a subshell
with the new group; use `exit` to leave it. `sg` applies that group to just the
specified command.

## Components

| Component | Requirement |
| --- | --- |
| Host board | **RUBIK Pi 3 or a Qualcomm QCS6490-based board** running Linux with an accessible I2C bus. |
| IMU module | [**Seeed Studio Grove – 6-Axis Accelerometer & Gyroscope (BMI088)**](https://www.seeedstudio.com/Grove-6-Axis-Accelerometer-Gyroscope-BMI088.html), SKU **101020584**, with I2C support, configured for accelerometer address `0x18` and gyroscope address `0x68`. |
| Wiring | Leads or a suitable connector cable for **3.3 V, GND, SDA, and SCL**. |
| Power supply | A power supply suitable for the host board. |
| Optional prototyping hardware | Breadboard and jumper wires, as shown in the setup photograph. |

**Verified setup:** RUBIK Pi 3 with Ubuntu Server. Other Qualcomm QCS6490-based
boards need their own header pinout, I2C bus selection, and device permissions;
the RUBIK Pi 3 pin numbers below must not be assumed to apply to them.

## Wiring

Disconnect board power before wiring. These are **physical header positions**,
not GPIO numbers. SDA is the data line (sometimes mistyped as “SCA”).

| BMI088 module | RUBIK Pi physical pin | Function |
| --- | ---: | --- |
| 3V / 3V3 | 1 | 3.3 V supply |
| GND | 6 | Ground |
| SDA | 3 | I2C1 data |
| SCL | 5 | I2C1 clock |

Looking at the board in the supplied photograph, from the left end of the header:

```text
                      Toward the board edge
              [2: 5 V]   [4: 5 V]   [6: GND]
              [1: 3.3 V] [3: SDA]   [5: SCL]
                      Toward the fan
```

**Pin 1 is 3.3 V, not ground. Do not connect the module's 3V input to pin 2 or 4.**
The module must be configured for I2C. This project's addresses are fixed to the
ones verified on this board: accelerometer `0x18`, gyroscope `0x68`.

![User-supplied wiring reference](../wiring-reference.png)

`wiring-reference.png` is the English version of the supplied wiring reference,
saved at the project root. Its labels were translated with the built-in image
generation tool using this instruction: translate only the annotations to
English while preserving the photograph, pin positions, colors, and wiring
mappings. The table and diagram above describe the same connections.

Reference: [RUBIK Pi Ubuntu 40-pin connector documentation](https://www.thundercomm.com/rubik-pi-3/en/docs/rubik-pi-3-user-manual/1.0.0-u/peripherals-and-interfaces/12.40-pin-ls-connector/).

## Dependencies and installation

No pip packages, virtual environment, NumPy, `smbus`, or `smbus2` are required by
the current Python library. It uses Python's standard-library `ctypes`, loading
`libbmi088.so` from the directory containing `bmi088.py`.

The following package versions were found installed on this board:

| Package | Installed version | Purpose |
| --- | --- | --- |
| `build-essential` | `12.10ubuntu1` | C build toolchain meta-package |
| `gcc` | `4:13.2.0-7ubuntu1` | Compile the adapter and Bosch sources |
| `make` | `4.3-4.1build2` | Build executable and shared library |
| `libc6-dev` | `2.39-0ubuntu8.9` | C/POSIX development headers |
| `linux-libc-dev` | `6.8.0-149.149` | Linux I2C ioctl headers |
| `python3` | `3.12.3-0ubuntu2.1` | Python runtime (project requires Python 3.10+) |
| `i2c-tools` | `4.3-4build2` | Optional bus diagnostics |
| `git` | `1:2.43.0-1ubuntu7.4` | Obtain/update upstream sources |
| `python3-smbus` | `4.3-4build2` | Installed during the earlier Python prototype; **not used now** |

These are an inventory, not exact version requirements. This change did not
install new system or pip packages. On a fresh Ubuntu installation, an
administrator can install prerequisites once:

```bash
sudo apt update
sudo apt install build-essential python3 i2c-tools git
sudo modprobe i2c-dev
```

The Bosch source tree is pinned as a Git submodule in `vendor/BMI08x_SensorAPI`, unchanged, at
commit `c1ed227e7bb7da1fa600bbd4e5c82d0da1eb416a`. Its BSD-3-Clause license is in
[`vendor/BMI08x_SensorAPI/LICENSE`](../vendor/BMI08x_SensorAPI/LICENSE).
No Bosch COINES board/library is required: this project provides native Linux
I2C callbacks instead.

## Device permissions: one-time setup

On this board `/dev/i2c-1` already has owner `root`, group `i2c`, mode `0660`.
The user `ubuntu` was added to that group during setup. This grants access to
I2C devices belonging to that group, not just the BMI088 addresses.

For a fresh installation, an administrator must configure access once:

```bash
sudo groupadd -f i2c
sudo usermod -aG i2c ubuntu
ls -l /dev/i2c-1
```

Then reconnect over SSH or use `newgrp i2c`. Normal building and reading require
neither root nor sudo. If device ownership is not already configured, install
this persistent udev rule as an administrator:

```bash
printf '%s\n' 'SUBSYSTEM=="i2c-dev", KERNEL=="i2c-1", GROUP="i2c", MODE="0660"' | sudo tee /etc/udev/rules.d/99-bmi088-i2c.rules
sudo udevadm control --reload-rules
sudo udevadm trigger --subsystem-match=i2c-dev
```

This rule was **not needed or installed** on the current board. Do not use
world-writable permissions or a setuid executable to bypass device access.

## Build

```bash
cd ~/BMI088
make
```

Outputs:

- `bmi088`: native C command-line reader.
- `libbmi088.so`: native library used by Python.

The checked build is native ARM64. Rebuild on any other architecture; do not
reuse this board's binaries on x86. Use `make clean && make` for a fresh build.
Python locates the shared library relative to its module, independent of the
current working directory. Keep `bmi088.py` and `libbmi088.so` together.

## Python commands

```bash
# Normal continuous reading
sg i2c -c 'python3 bmi088_read.py'

# Check both chip IDs without resetting or configuring sensors
sg i2c -c 'python3 bmi088_read.py --probe'

# Collect 100 samples, approximately 10 seconds
sg i2c -c 'python3 bmi088_read.py --samples 100'

# Choose a device and display interval
sg i2c -c 'python3 bmi088_read.py --device /dev/i2c-1 --interval 0.2'

python3 bmi088_read.py --help
```

The old direct-register `bmi088_read.py` has been replaced by this Bosch-backed
CLI; its filename remains the same for convenience.

Example output:

```text
CHIP_ID: ACC=0x1e GYRO=0x0f
ACC [g], GYRO [deg/s]. Unsynchronized readings. Ctrl+C to stop.
ACC  +0.133  -0.081  +0.988 | GYRO    +0.20    +0.31    +0.87
```

Each triple is X, Y, Z in sensor coordinates. A stationary sensor should measure
an acceleration magnitude near 1 g, including gravity. Gyroscope readings should
be near zero, with noise and bias. Tilting changes the acceleration components;
rotation changes angular velocity. The program does not calculate orientation,
remove gravity, calibrate bias, or apply a board-to-world axis transformation.

## Python library API

From a script in this project directory:

```python
import time
from bmi088 import BMI088, BMI088Error

try:
    with BMI088('/dev/i2c-1') as sensor:
        for _ in range(100):
            sample = sensor.read()
            print(sample.timestamp)             # Host monotonic seconds
            print(sample.acceleration_g)        # XYZ in g
            print(sample.acceleration_m_s2)      # XYZ in m/s^2
            print(sample.angular_velocity_dps)  # XYZ in degrees/second
            time.sleep(0.1)
except BMI088Error as error:
    print(f'Sensor error: {error}')
```

`BMI088(device='/dev/i2c-1', probe_only=False)` opens and locks the bus, checks
IDs, resets both sensors, loads the Bosch configuration, and configures sampling.
`probe_only=True` only checks IDs; `read()` is disabled in that mode.

`read()` returns an immutable `Sample`. Its timestamp is captured after the
sequential reads using host monotonic time, not a sensor timestamp or UTC time.

`close()` releases the descriptor and lock, is idempotent, and leaves the sensors
powered/configured. Use `with` or explicitly call `close()` in a `finally` block;
do not depend on garbage collection. Reads after close raise `BMI088Error`.
Methods on one Python instance are serialized with a lock. Do not share an
instance across `fork()`.

## ROS 2 integration

The optional ROS 2 Jazzy package adds a `sensor_msgs/msg/Imu` publisher and a
listener. Follow the [complete ROS 2 guide](ros2.md) for fresh installation on
Ubuntu 24.04 ARM64, colcon build instructions, non-root startup, topic units,
parameters, reset messages, and the `sg`/`LD_LIBRARY_PATH` troubleshooting fix.
The standalone driver commands in this guide do not require ROS.

## C command-line reader

```bash
sg i2c -c './bmi088'
sg i2c -c './bmi088 --probe'
sg i2c -c './bmi088 --samples 10'
```

The C and Python clients share the same implementation and exclusive advisory
bus lock. Only one may run at a time. Other tools such as `i2cget` can ignore
that lock; avoid concurrent access from those tools.

## Initialization, reset handling, and sampling limits

The backend follows the Bosch `polling_streaming_pc` initialization approach,
selecting `BMI088_VARIANT`. It resets both sensors before every configuration
upload, then calls Bosch APIs to load configuration and set power and ranges:

- Accelerometer: +/-3 g, 100 Hz ODR, normal bandwidth mode.
- Gyroscope: +/-500 degrees/s, 100 Hz ODR, 32 Hz filter bandwidth.
- Readout: approximately 10 Hz by default; sequential and **not synchronized**.

Linux reads use `I2C_RDWR` combined transactions (register address followed by
repeated-start read). Sensor acquisition runs faster than console polling, so
this is a live monitor, not lossless acquisition. There is no FIFO draining or
hardware data-ready interrupt handling. Equal consecutive values alone do not
prove a fault, and the library does not guarantee a new sample on every read.

An earlier implementation reloaded the configuration without an explicit reset;
the accelerometer was observed frozen on a subsequent run. Resetting before
configuration restored updates across repeated starts on this board.

During testing, reset writes sometimes returned `ENXIO` or `EREMOTEIO` even
though the reset took effect. The adapter accepts this **only for the exact reset
command**, after a delay and successful checks of CHIP_ID and reset defaults:
ACC power/configuration or GYRO range/bandwidth/power. All other failures remain
errors. A message such as `NACK received; reset confirmed by register readback`
is informational. It does not mean arbitrary communication errors are ignored.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| Permission denied | Check `id`, device ownership, and use `sg i2c -c 'python3 bmi088_read.py'` or reconnect over SSH. |
| Cannot load libbmi088.so | Run `make` on the target machine and keep it beside `bmi088.py`. |
| Cannot lock the bus | Stop the other C/Python reader with Ctrl+C. |
| No such file for /dev/i2c-1 | Check `i2cdetect -l`, kernel I2C support, and whether i2c-dev is loaded. |
| No such device or address | Read the reported operation/address/register; stop the reader, check power/wiring, and rerun the probe. |
| ACC appears frozen | Stop every reader and restart the current binary/script; initialization now resets both sensors. Tilt the sensor and check values. If still frozen, record the startup messages and output. |
| Wrong chip ID | Expected IDs are ACC 0x1e and GYRO 0x0f; verify module and addresses. |

With all readers stopped, the previously verified diagnostic commands are:

```bash
sg i2c -c 'i2cdetect -y -r 1'
sg i2c -c 'i2cget -y 1 0x18 0x00 b'
sg i2c -c 'i2cget -y 1 0x68 0x00 b'
```

## Project layout

```text
README.md                 Setup, wiring, APIs, dependencies, troubleshooting
wiring-reference.png      English wiring illustration
Makefile                  Native executable and shared-library build
bmi088.py                 Reusable Python library (ctypes)
bmi088_read.py            Python CLI
src/bmi088_linux.c         Linux I2C adapter and shared Bosch initialization
src/bmi088_linux.h         C interface
src/main.c                C CLI
vendor/BMI08x_SensorAPI/   Unmodified official Bosch sources and license
tests/hardware_smoke.py   Opt-in live hardware regression test
```

## Validation

Built on the actual ARM64 board with `-Wall -Wextra -Wpedantic` without warnings.
The Python hardware test passed **without root**, covering two successive
initializations, 25 samples on each (25 distinct ACC readings on each run),
exclusive access, repeated close, read-after-close rejection, and probe-only
read rejection. Both Python and C CLIs were exercised on the sensor.
These checks establish live communication and changing samples; they are not
calibration or accuracy certification.

To repeat (this resets the attached sensor; stop other readers first):

```bash
sg i2c -c 'python3 tests/hardware_smoke.py'
```
