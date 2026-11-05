"""Verify source timestamps cannot be converted into fresh manual commands."""
import pytest
import rclpy
from rclpy.time import Time
from sensor_msgs.msg import Joy

from uamc_io.manual_joy import ManualJoy


class Capture:
    def __init__(self):
        self.messages = []

    def publish(self, msg):
        self.messages.append(msg)


@pytest.fixture
def node():
    rclpy.init()
    instance = ManualJoy()
    instance.enable_pub = Capture()
    instance.drive_pub = Capture()
    yield instance
    instance.destroy_node()
    rclpy.shutdown()


def joy(node, offset_seconds, pressed, throttle=0.0, steer=0.0):
    msg = Joy()
    ns = node.get_clock().now().nanoseconds + int(offset_seconds * 1_000_000_000)
    msg.header.stamp = Time(nanoseconds=ns).to_msg()
    msg.axes = [steer, throttle]
    msg.buttons = [0, 0, 0, 0, int(pressed)]
    return msg


def test_stale_input_disables_and_requires_new_release_press(node):
    node.on_joy(joy(node, 0, False))
    node.on_joy(joy(node, 0, True))
    node.on_joy(joy(node, 0, True, throttle=1))
    assert node.enable_pub.messages[-1].data
    assert node.drive_pub.messages[-1].drive.speed > 0

    node.on_joy(joy(node, -1, True, throttle=1))
    assert not node.enable_pub.messages[-1].data
    assert node.drive_pub.messages[-1].drive.speed == 0
    assert node.drive_pub.messages[-1].drive.steering_angle == 0
    node.on_joy(joy(node, 0, True))
    assert not node.enable_pub.messages[-1].data
    node.on_joy(joy(node, 0, False))
    node.on_joy(joy(node, 0, True))
    assert node.enable_pub.messages[-1].data


def test_future_and_zero_stamp_rejected_and_valid_stamp_preserved(node):
    node.on_joy(joy(node, 0, False))
    node.on_joy(joy(node, 1, True))
    assert not node.enable_pub.messages[-1].data
    node.on_joy(joy(node, 0, True))
    assert not node.enable_pub.messages[-1].data
    node.on_joy(joy(node, 0, False))
    valid = joy(node, -0.02, True)
    node.on_joy(valid)
    assert node.enable_pub.messages[-1].data
    assert node.drive_pub.messages[-1].header.stamp == valid.header.stamp

    unstamped = Joy()
    unstamped.axes = [0.0, 0.0]
    unstamped.buttons = [0, 0, 0, 0, 1]
    node.on_joy(unstamped)
    assert not node.enable_pub.messages[-1].data
    assert node.drive_pub.messages[-1].drive.speed == 0
