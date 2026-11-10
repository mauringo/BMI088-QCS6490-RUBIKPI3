"""Subscribe to BMI088 sensor_msgs/Imu; no sensor or I2C permissions required."""
import math
import sys
from time import monotonic

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rcl_interfaces.msg import ParameterDescriptor
from sensor_msgs.msg import Imu


class BMI088Listener(Node):
    def __init__(self, **kwargs):
        super().__init__('bmi088_listener', **kwargs)
        try:
            readonly = ParameterDescriptor(read_only=True)
            topic = self.declare_parameter('topic', '/imu/data_raw', readonly).value
            self.log_interval = self.declare_parameter('log_interval_sec', 1.0, readonly).value
            if not math.isfinite(self.log_interval) or self.log_interval < 0:
                raise ValueError('log_interval_sec must be finite and nonnegative')
            self.last_log = -math.inf
            self.received = 0
            self.last_message = None
            self.subscription = self.create_subscription(
                Imu, topic, self.receive, qos_profile_sensor_data)
            self.get_logger().info(f'Listening on {topic}; acceleration=m/s^2, angular velocity=rad/s')
        except BaseException:
            self.destroy_node()
            raise

    def receive(self, msg):
        self.received += 1
        self.last_message = msg
        now = monotonic()
        if now - self.last_log >= self.log_interval:
            a, g = msg.linear_acceleration, msg.angular_velocity
            self.get_logger().info(
                f'frame={msg.header.frame_id} ACC [{a.x:+.3f}, {a.y:+.3f}, {a.z:+.3f}] m/s^2 '
                f'GYRO [{g.x:+.3f}, {g.y:+.3f}, {g.z:+.3f}] rad/s')
            self.last_log = now


def main(args=None):
    rclpy.init(args=args)
    node = None
    result = 0
    try:
        node = BMI088Listener()
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    except ValueError as error:
        print(f'BMI088 listener error: {error}', file=sys.stderr)
        result = 1
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return result
