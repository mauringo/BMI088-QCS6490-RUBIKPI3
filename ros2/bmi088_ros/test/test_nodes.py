"""ROS 2 integration tests using real DDS messages and a fake sensor."""
import math
import time
import pytest
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.parameter import Parameter
from builtin_interfaces.msg import Time
from bmi088 import Sample, BMI088Error
from bmi088_ros.messages import imu_message
from bmi088_ros.publisher import BMI088Publisher
from bmi088_ros.listener import BMI088Listener


class FakeSensor:
    closed = False
    def __init__(self, device):
        self.device = device
    def read(self):
        return Sample(123.0, (1.0, -0.5, 0.0), (180.0, -90.0, 0.0))
    def close(self):
        self.closed = True


def test_message_units_and_metadata():
    stamp = Time(sec=42, nanosec=7)
    msg = imu_message(FakeSensor('').read(), stamp, 'test_imu')
    assert msg.header.stamp == stamp
    assert msg.header.frame_id == 'test_imu'
    assert msg.linear_acceleration.x == pytest.approx(9.80665)
    assert msg.linear_acceleration.y == pytest.approx(-4.903325)
    assert msg.angular_velocity.x == pytest.approx(math.pi)
    assert msg.angular_velocity.y == pytest.approx(-math.pi/2)
    assert msg.orientation_covariance[0] == -1
    assert list(msg.linear_acceleration_covariance) == [0.0]*9
    assert list(msg.angular_velocity_covariance) == [0.0]*9


@pytest.fixture
def ros_context():
    rclpy.init()
    yield
    rclpy.shutdown()


def test_publisher_listener_delivery_and_cleanup(ros_context):
    publisher = BMI088Publisher(sensor_factory=FakeSensor)
    sensor = publisher.sensor
    listener = BMI088Listener()
    executor = SingleThreadedExecutor()
    executor.add_node(publisher)
    executor.add_node(listener)
    try:
        deadline = time.monotonic() + 10
        while listener.received == 0 and time.monotonic() < deadline:
            executor.spin_once(timeout_sec=0.1)
        assert listener.received > 0
        assert listener.last_message.header.frame_id == 'imu_link'
        assert listener.last_message.angular_velocity.x == pytest.approx(math.pi)
        assert listener.last_message.header.stamp.sec > 0
    finally:
        executor.shutdown()
        publisher.destroy_node()
        listener.destroy_node()
    assert sensor.closed


def test_invalid_rate_does_not_open_device(ros_context):
    def forbidden(_device):
        pytest.fail('Device opened before parameter validation')
    with pytest.raises(ValueError, match='publish_rate_hz'):
        BMI088Publisher(sensor_factory=forbidden, parameter_overrides=[
            Parameter('publish_rate_hz', value=0.0)])


def test_read_error_propagates_and_cleanup(ros_context):
    class FailingSensor(FakeSensor):
        def read(self):
            raise BMI088Error('I2C test failure')
    publisher = BMI088Publisher(sensor_factory=FailingSensor)
    sensor = publisher.sensor
    try:
        with pytest.raises(BMI088Error, match='I2C test failure'):
            publisher.publish_sample()
    finally:
        publisher.destroy_node()
    assert sensor.closed
