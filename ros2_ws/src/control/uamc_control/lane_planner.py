"""The first local planner forwards the validated lane centerline unchanged."""
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Path


class LanePlanner(Node):
    def __init__(self):
        super().__init__('lane_planner')
        self.pub = self.create_publisher(Path, '/planning/path', 10)
        self.create_subscription(Path, '/perception/lane', self.pub.publish, 10)


def main():
    rclpy.init()
    node = LanePlanner()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
