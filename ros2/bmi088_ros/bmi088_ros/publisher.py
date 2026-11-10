"""Publish sequential BMI088 measurements as sensor_msgs/Imu."""
import math
import sys

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rcl_interfaces.msg import ParameterDescriptor
from sensor_msgs.msg import Imu
from bmi088 import BMI088, BMI088Error
from .messages import imu_message


class BMI088Publisher(Node):
    def __init__(self, *, sensor_factory=BMI088, **kwargs):
        super().__init__('bmi088_publisher', **kwargs)
        self.sensor = None
        try:
            readonly = ParameterDescriptor(read_only=True)
            device = self.declare_parameter('device', '/dev/i2c-1', readonly).value
            topic = self.declare_parameter('topic', '/imu/data_raw', readonly).value
            self.frame_id = self.declare_parameter('frame_id', 'imu_link', readonly).value
            rate = self.declare_parameter('publish_rate_hz', 10.0, readonly).value
            if not math.isfinite(rate) or not 0 < rate <= 100:
                raise ValueError('publish_rate_hz must be finite and in (0, 100]')
            if not self.frame_id or self.frame_id.startswith('/'):
                raise ValueError('frame_id must be nonempty and must not start with /')
            self.publisher = self.create_publisher(Imu, topic, qos_profile_sensor_data)
            self.sensor = sensor_factory(device)
            self.timer = self.create_timer(1.0 / rate, self.publish_sample)
            self.get_logger().info(f'Publishing {topic} from {device} at {rate:g} Hz; frame={self.frame_id}')
        except BaseException:
            self.destroy_node()
            raise

    def publish_sample(self):
        # Errors propagate: main closes the device and exits rather than publishing stale data.
        sample = self.sensor.read()
        msg = imu_message(sample, self.get_clock().now().to_msg(), self.frame_id)
        self.publisher.publish(msg)

    def destroy_node(self):
        if self.sensor is not None:
            self.sensor.close()
            self.sensor = None
        return super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = None
    result = 0
    try:
        node = BMI088Publisher()
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    except (BMI088Error, ValueError) as error:
        print(f'BMI088 publisher error: {error}', file=sys.stderr)
        result = 1
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return result
