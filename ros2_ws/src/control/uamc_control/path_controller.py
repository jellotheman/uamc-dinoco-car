import math
import time

import rclpy
from rclpy.clock import Clock, ClockType
from rclpy.node import Node
from nav_msgs.msg import Path
from ackermann_msgs.msg import AckermannDriveStamped
from .control_math import steering_for_path


class PathController(Node):
    def __init__(self):
        super().__init__('path_controller')
        for key, val in [('speed', 0.30), ('lookahead', 0.55), ('wheelbase', 0.232),
                         ('max_steering', 0.45), ('lane_timeout', 0.35)]:
            self.declare_parameter(key, val)
        self.path = None
        self.received = 0.0
        self.pub = self.create_publisher(AckermannDriveStamped, '/drive/requested', 10)
        self.create_subscription(Path, '/planning/path', self.on_path, 10)
        self.create_timer(0.05, self.tick, clock=Clock(clock_type=ClockType.STEADY_TIME))

    def on_path(self, msg):
        self.path, self.received = msg, time.monotonic()

    def tick(self):
        msg = AckermannDriveStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'base_link'
        if self.path is not None and self.path.header.frame_id == 'base_link' and time.monotonic() - self.received < self.get_parameter('lane_timeout').value:
            points = [(p.pose.position.x, p.pose.position.y) for p in self.path.poses]
            angle = steering_for_path(points, self.get_parameter('lookahead').value,
                                      self.get_parameter('wheelbase').value, self.get_parameter('max_steering').value)
            if angle is not None:
                msg.drive.steering_angle = angle
                msg.drive.speed = self.get_parameter('speed').value / (1.0 + 2.0 * abs(math.tan(angle)))
        self.pub.publish(msg)


def main():
    rclpy.init()
    node = PathController()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
