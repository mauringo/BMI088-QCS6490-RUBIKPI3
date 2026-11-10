# ROS 2: BMI088 publisher and listener

The optional `bmi088_ros` package targets **ROS 2 Jazzy on Ubuntu 24.04**.
It uses the same Bosch-backed driver as the standalone C/Python readers.
All commands below are run from the repository root unless stated otherwise.

## Prerequisites

ROS 2 was not installed on the development board when this integration was
created. First install ROS 2 Jazzy using the
[official Ubuntu installation instructions](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html).
Once the ROS apt repository is configured, install these packages once:

```bash
sudo apt update
sudo apt install ros-jazzy-ros-base ros-jazzy-ament-cmake-python \
  ros-jazzy-sensor-msgs ros-jazzy-rcl-interfaces \
  ros-jazzy-ament-cmake-pytest python3-colcon-common-extensions \
  python3-pytest build-essential cmake
```

The publisher needs membership in `i2c` and access to `/dev/i2c-1`; see the
[device permission setup](guide.md#device-permissions-one-time-setup).
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

If the group was added after you logged in, run this after sourcing the same
setup files. `sg` preserves the ROS environment while applying the group:

```bash
sg i2c -c 'ros2 run bmi088_ros publisher'
```

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
sg i2c -c 'ros2 run bmi088_ros publisher --ros-args \
  -p device:=/dev/i2c-1 -p publish_rate_hz:=50.0 \
  -p frame_id:=imu_link -p topic:=/robot/imu/data_raw'

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

The standalone hardware driver was previously tested on this board. Live ROS
publisher/listener operation on the board still requires installing ROS 2 and
running the nodes; software/DDS tests do not replace that hardware check.
