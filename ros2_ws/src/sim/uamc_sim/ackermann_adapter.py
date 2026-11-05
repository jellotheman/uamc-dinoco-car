"""Convert the final Ackermann command to Gazebo's combined Twist interface."""
import math
import time

from ackermann_msgs.msg import AckermannDriveStamped
from geometry_msgs.msg import Twist
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.clock import Clock, ClockType
from rclpy.node import Node


class AckermannAdapter(Node):
    def __init__(self):
        super().__init__('sim_ackermann_adapter')
        self.declare_parameter('wheelbase', 0.232)
        self.declare_parameter('timeout', 0.25)
        self.declare_parameter('max_speed', 0.30)
        self.declare_parameter('max_steering', 0.5)
        self.publisher = self.create_publisher(Twist, '/sim/cmd_vel', 10)
        self.create_subscription(AckermannDriveStamped, '/drive/command', self.command, 10)
        self.last_received = None
        self.value = Twist()
        self.timer = self.create_timer(0.05, self.tick, clock=Clock(clock_type=ClockType.STEADY_TIME))

    def command(self, msg):
        speed, angle = msg.drive.speed, msg.drive.steering_angle
        if not math.isfinite(speed) or not math.isfinite(angle):
            self.last_received = None
            self.value = Twist()
            return
        limit = float(self.get_parameter('max_speed').value)
        steer_limit = float(self.get_parameter('max_steering').value)
        speed = max(-limit, min(limit, speed))
        angle = max(-steer_limit, min(steer_limit, angle))
        self.value = Twist()
        self.value.linear.x = speed
        self.value.angular.z = speed * math.tan(angle) / float(self.get_parameter('wheelbase').value)
        self.last_received = time.monotonic()

    def tick(self):
        fresh = self.last_received is not None and time.monotonic() - self.last_received <= float(self.get_parameter('timeout').value)
        self.publisher.publish(self.value if fresh else Twist())


def main(args=None):
    rclpy.init(args=args)
    node = AckermannAdapter()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        if rclpy.ok():
            node.publisher.publish(Twist())
        node.destroy_node()
        rclpy.try_shutdown()
