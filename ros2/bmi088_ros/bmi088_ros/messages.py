"""Convert driver samples to the sensor_msgs/Imu convention."""
from math import radians
from sensor_msgs.msg import Imu


def imu_message(sample, stamp, frame_id):
    """No orientation estimate; zero measurement covariance means unknown."""
    msg = Imu()
    msg.header.stamp = stamp
    msg.header.frame_id = frame_id
    msg.orientation.w = 1.0
    msg.orientation_covariance[0] = -1.0
    a = sample.acceleration_m_s2
    g = tuple(radians(value) for value in sample.angular_velocity_dps)
    msg.linear_acceleration.x, msg.linear_acceleration.y, msg.linear_acceleration.z = a
    msg.angular_velocity.x, msg.angular_velocity.y, msg.angular_velocity.z = g
    return msg
