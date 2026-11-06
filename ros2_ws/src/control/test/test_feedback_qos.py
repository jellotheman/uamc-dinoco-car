"""Wheel feedback must match both common DDS publisher reliability profiles."""
import time

import pytest
import rclpy
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy

from uamc_control.safety_gate import SafetyGate


@pytest.mark.parametrize("reliability", [ReliabilityPolicy.BEST_EFFORT, ReliabilityPolicy.RELIABLE])
def test_gate_receives_wheel_from_sensor_publishers(reliability):
    rclpy.init()
    gate = SafetyGate()
    source = Node("wheel_qos_fixture")
    publisher = source.create_publisher(
        Odometry, "/odometry/wheel", QoSProfile(depth=10, reliability=reliability))
    try:
        msg = Odometry()
        msg.header.stamp = source.get_clock().now().to_msg()
        msg.twist.twist.linear.x = 0.123
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and "wheel" not in gate.data:
            publisher.publish(msg)
            rclpy.spin_once(gate, timeout_sec=0.05)
        assert "wheel" in gate.data
        assert gate.data["wheel"].twist.twist.linear.x == pytest.approx(0.123)
    finally:
        source.destroy_node()
        gate.destroy_node()
        rclpy.shutdown()
