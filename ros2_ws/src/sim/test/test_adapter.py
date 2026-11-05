import math
import rclpy
from ackermann_msgs.msg import AckermannDriveStamped
from uamc_sim.ackermann_adapter import AckermannAdapter


def test_conversion_and_invalid_command():
    rclpy.init()
    node = AckermannAdapter()
    try:
        cmd = AckermannDriveStamped()
        cmd.drive.speed = 0.2
        cmd.drive.steering_angle = 0.25
        node.command(cmd)
        assert abs(node.value.angular.z - 0.2 * math.tan(0.25) / 0.232) < 1e-6
        cmd.drive.speed = float('nan')
        node.command(cmd)
        assert node.last_received is None
        assert node.value.linear.x == 0.0
    finally:
        node.destroy_node()
        rclpy.shutdown()
