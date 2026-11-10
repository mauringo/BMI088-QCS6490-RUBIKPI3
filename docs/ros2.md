# ROS 2: BMI088 publisher and listener

The optional `bmi088_ros` package targets **ROS 2 Jazzy on Ubuntu 24.04**.
It uses the same Bosch-backed driver as the standalone C/Python readers.
All commands below are run from the repository root unless stated otherwise.

## Install ROS 2 Jazzy on Ubuntu 24.04 ARM64

This setup is for the **Qualcomm QCS6490-based RUBIK Pi 3 running Ubuntu
Server 24.04 (Noble), ARM64**. ROS 2 is now installed on the development board;
the steps below also cover a fresh installation. Check your platform first:

```bash
. /etc/os-release
printf 'Ubuntu: %s (%s)\n' "$VERSION_ID" "$VERSION_CODENAME"
dpkg --print-architecture
```

Expected: `24.04`, `noble`, and `arm64`. These instructions follow the
[official ROS 2 Jazzy Ubuntu package guide](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html).
Installation and one-time group configuration require an administrator;
building and running the nodes do not.

### 1. Prepare Ubuntu

```bash
sudo apt update
sudo apt install -y locales software-properties-common curl
sudo add-apt-repository -y universe
sudo locale-gen en_US.UTF-8
export LANG=en_US.UTF-8
```

Use a UTF-8 locale in subsequent sessions as well; an existing UTF-8 locale is
fine. Check it with `locale`.

### 2. Configure the official ROS apt repository

The `ros2-apt-source` package provides the repository configuration and signing
keys. This block downloads the current release for Ubuntu Noble:

```bash
ROS_APT_SOURCE_VERSION=$(
  curl -fsSL https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest |
  python3 -c 'import json, sys; print(json.load(sys.stdin)["tag_name"])'
)

curl -fL \
  "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.noble_all.deb" \
  -o /tmp/ros2-apt-source.deb

sudo dpkg -i /tmp/ros2-apt-source.deb
sudo apt update
```

If the download fails, stop and resolve the error before installing the package.
The repository setup is only needed once. Source:
[official ROS repository instructions](https://github.com/ros2/ros2_documentation/blob/jazzy/source/Installation/_Apt-Repositories.rst).

### 3. Install ROS Base and build/test dependencies

```bash
sudo apt install -y \
  ros-jazzy-ros-base \
  ros-jazzy-ament-cmake-python \
  ros-jazzy-ament-cmake-pytest \
  ros-jazzy-sensor-msgs \
  ros-jazzy-rcl-interfaces \
  python3-colcon-common-extensions \
  python3-pytest \
  build-essential cmake
```

| Dependency | Purpose |
| --- | --- |
| `ros-jazzy-ros-base` | ROS middleware, Python client library and command-line tools; no desktop GUI required |
| `ros-jazzy-ament-cmake-python` | Install the Python nodes alongside the C backend |
| `ros-jazzy-sensor-msgs` | Standard `sensor_msgs/msg/Imu` messages |
| `ros-jazzy-rcl-interfaces` | Parameter descriptors used by both nodes |
| `python3-colcon-common-extensions` | Build, test and install the ROS package |
| `ros-jazzy-ament-cmake-pytest`, `python3-pytest` | ROS integration tests |
| `build-essential`, `cmake` | Compile the native Bosch backend |

No pip packages are needed. Use Ubuntu's system Python with these ROS packages.
Check the installation:

```bash
source /opt/ros/jazzy/setup.bash
printenv ROS_DISTRO
python3 -c 'import rclpy; from sensor_msgs.msg import Imu; print("ROS Python imports OK")'
ros2 --help
```

`ROS_DISTRO` should be `jazzy`.

### 4. Grant non-root I2C access

The current board already has `ubuntu` in the `i2c` group. For a fresh setup:

```bash
sudo groupadd -f i2c
sudo usermod -aG i2c "$USER"
ls -l /dev/i2c-1
```

Reconnect over SSH to apply membership, then check `id`. The device should
belong to group `i2c` with mode `0660`. See the
[device permission setup](guide.md#device-permissions-one-time-setup) if a
persistent udev rule is needed. Do not make the device world-writable.

Opening the device resets both sensors. Stop the standalone C/Python reader
before starting the ROS publisher. Multiple listeners are fine.

## Build

```bash
cd ~/BMI088  # Or your actual clone directory
source /opt/ros/jazzy/setup.bash
git submodule update --init --recursive
colcon build --base-paths ros2 --packages-select bmi088_ros
source install/setup.bash
```

No separate `make` is needed: CMake builds the shared Bosch backend and installs
it beside the existing `bmi088.py` module in the ROS overlay. Keep the ROS package
inside this repository; it references the shared sources two directories above.
The build also installs the project and Bosch license notices.

## Run without root

If your current shell already has the `i2c` group:

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 run bmi088_ros publisher
```

If the group was added after you logged in, source ROS **inside** the new
shell, after `sg` applies the group. The system may remove `LD_LIBRARY_PATH`
when starting `sg`; sourcing ROS only before `sg` is not sufficient.

```bash
sg i2c -c 'bash -c "
  source /opt/ros/jazzy/setup.bash
  source /home/ubuntu/BMI088/install/setup.bash
  exec ros2 run bmi088_ros publisher
"'
```

Adjust the overlay path if your checkout is elsewhere. Alternatively, reconnect
via SSH or run `newgrp i2c`, then source both setup files and run `ros2 run`
directly. An import error for `librcl_action.so` with the file present can be
caused by the environment being cleared during the group switch.

In another terminal:

```bash
cd ~/BMI088
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 run bmi088_ros listener
```

Press Ctrl+C to stop either node. The publisher closes its sensor handle and
releases its lock; the sensor remains powered/configured, as in the Python API.
Communication failures stop the publisher with an error instead of silently
republishing old data. The listener never opens the I2C device.

## Expected startup and live data

The following startup was confirmed on the physical board with the ordinary,
non-root command `ros2 run bmi088_ros publisher`:

```text
Reset ACC: NACK received; reset confirmed by register readback.
Reset GYRO: NACK received; reset confirmed by register readback.
[INFO] [...] [bmi088_publisher]: Publishing /imu/data_raw from /dev/i2c-1 at 10 Hz; frame=imu_link
```

The reset lines may appear for one or both sensors. They are informational:
the backend checked the chip IDs and reset-register values before proceeding.
They are not unconditionally ignored I2C errors.

The publisher logs startup, not each sample. Use the listener in a second
terminal to view values. Its output format is:

```text
[INFO] [...] [bmi088_listener]: frame=imu_link ACC [+0.000, +0.000, +9.807] m/s^2 GYRO [+0.000, +0.000, +0.000] rad/s
```

Those numbers are illustrative. At rest, acceleration magnitude should be near
9.81 m/s², with components determined by mounting orientation; angular velocity
should be near zero with some bias/noise. Tilt and rotate the module to check
that readings change. Listener logging is once per second by default, even
though the publisher requests 10 messages per second.

## Parameters

Parameters are configured at startup and read-only afterward.

| Node | Parameter | Default | Meaning |
| --- | --- | --- | --- |
| Publisher | `device` | `/dev/i2c-1` | Linux I2C device |
| Publisher/listener | `topic` | `/imu/data_raw` | `sensor_msgs/msg/Imu` topic |
| Publisher | `frame_id` | `imu_link` | Sensor coordinate frame; nonempty, no leading slash |
| Publisher | `publish_rate_hz` | `10.0` | Requested poll rate, finite and greater than 0, at most 100 Hz |
| Listener | `log_interval_sec` | `1.0` | Console log interval; 0 logs every received message |

Example:

```bash
# In a shell with i2c membership and both ROS setup files sourced:
ros2 run bmi088_ros publisher --ros-args \
  -p device:=/dev/i2c-1 -p publish_rate_hz:=50.0 \
  -p frame_id:=imu_link -p topic:=/robot/imu/data_raw

ros2 run bmi088_ros listener --ros-args -p topic:=/robot/imu/data_raw
```

ROS topic remapping is also supported. The configured sensor ODR stays 100 Hz;
changing the publish rate changes polling, not hardware configuration. Linux
scheduling and I2C latency affect the achieved rate. Reads are sequential and
unsynchronized; this is not FIFO-based, lossless acquisition.

## Message semantics

The publisher follows the official
[`sensor_msgs/Imu` definition](https://github.com/ros2/common_interfaces/blob/jazzy/sensor_msgs/msg/Imu.msg):

- `linear_acceleration`: sensor XYZ acceleration including gravity, in m/s².
- `angular_velocity`: sensor XYZ angular velocity, converted from degrees/s to rad/s.
- `header.stamp`: ROS clock time immediately after reading both sensors, not the
  driver's monotonic timestamp and not a hardware sampling timestamp.
- `header.frame_id`: `imu_link` by default; no axis remapping or TF is generated.
- `orientation_covariance[0] = -1`: orientation is unavailable. The identity
  quaternion is only a placeholder and must not be used as an attitude estimate.
- Acceleration and angular-velocity covariance matrices are all zero: unknown,
  not zero sensor noise. Configure downstream filters accordingly.

Define a transform from the physical sensor axes to your robot's `base_link`
using your actual mounting orientation. Merely changing `frame_id` does not
rotate the measurements. Keep `use_sim_time` false for normal physical sensing;
if enabled, a working `/clock` publisher is required.

Both nodes use ROS sensor-data QoS (best effort, volatile, keep last 5).
A reliable subscriber may not match this publisher. The listener receives every
delivered message but throttles console output using host monotonic time.

## Inspect or record

```bash
ros2 topic info /imu/data_raw --verbose
ros2 topic echo /imu/data_raw --qos-reliability best_effort
ros2 bag record /imu/data_raw
```

For a listener on a different machine, install/build the same package there,
use a matching `ROS_DOMAIN_ID`, and configure ROS discovery/network access.
The remote listener needs no `i2c` membership. A standard Imu subscriber can
also consume the topic without this repository.

## Troubleshooting

| Symptom | Cause/check | Action |
| --- | --- | --- |
| `ros2: command not found` | ROS underlay not sourced or not installed | Source `/opt/ros/jazzy/setup.bash`; if absent, complete installation above. |
| `Package bmi088_ros not found` | Project overlay not built/sourced | Build with colcon and source `install/setup.bash` in that terminal. |
| `ImportError: librcl_action.so` | ROS library path missing, including after `sg` | Source both setup files **after** switching groups, using the corrected command above. |
| Permission denied on `/dev/i2c-1` | Current process lacks group membership | Reconnect after adding `i2c`, or use the documented `sg` command. |
| Cannot lock the bus | Another project reader owns the lock | Stop the standalone reader or other publisher. Listeners do not hold this lock. |
| Publisher startup succeeds but listener stays silent | Topic, discovery or QoS mismatch | Match topic and `ROS_DOMAIN_ID`; inspect `ros2 topic info /imu/data_raw --verbose`; use best-effort subscriber QoS. |
| `NACK received; reset confirmed` at startup | Reset took effect despite a transport NACK | No action needed if startup continues; only reset commands receive this verified handling. |
| Other I2C error | Sensor did not complete the requested transaction | Check the reported address/register, power, and wiring; stop readers before standalone diagnostics. |

For the shared-library error, the file can exist while the dynamic loader still
cannot find it. These checks were useful on this board:

```bash
ls -l /opt/ros/jazzy/lib/librcl_action.so
printenv LD_LIBRARY_PATH
source /opt/ros/jazzy/setup.bash
source install/setup.bash
python3 -c 'import rclpy; print("rclpy import OK")'
```

Do not reinstall ROS merely because the error occurs after `sg`; first restore
the environment inside the group-switched shell. The plain standalone
`sg i2c -c 'python3 bmi088_read.py'` command does not need the ROS environment,
so its behavior differs from running `ros2` through `sg`.

## Tests and validation limits

```bash
source /opt/ros/jazzy/setup.bash
colcon build --base-paths ros2 --packages-select bmi088_ros
source install/setup.bash
colcon test --packages-select bmi088_ros --event-handlers console_direct+
colcon test-result --verbose
```

Tests use actual ROS messages and DDS communication with an injected fake sensor;
they never open the physical I2C device. They cover unit conversion, timestamps,
orientation/covariance conventions, publisher-to-listener delivery, parameter
validation, read errors, and cleanup. GitHub Actions runs these checks in a ROS
2 Jazzy container. The installed backend is also checked from outside the source
checkout to catch missing shared libraries.

Validation completed:

- Native C and Python driver tests on the physical RUBIK Pi 3/BMI088 setup.
- GitHub Actions: Python 3.10/3.12 software tests and ROS 2 Jazzy build,
  simulated-sensor DDS delivery, conversions, cleanup, and installed-library loading.
- A five-second non-root ROS publisher startup on the physical board, sourcing
  ROS inside the group-switched shell.
- User-confirmed direct non-root `ros2 run bmi088_ros publisher` startup at
  10 Hz on `/imu/data_raw` after installation and environment setup.

Startup success confirms initialization and creation of the publisher. It does
not alone prove live message delivery or calibrated accuracy. The listener
commands above provide the next end-to-end hardware check; simulated DDS tests
are recorded separately from real sensor measurements.
