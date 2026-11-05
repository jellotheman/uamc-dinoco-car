"""Independent joystick input path for the shared safety gate."""
import math
import time

from ackermann_msgs.msg import AckermannDriveStamped
import rclpy
from rclpy.node import Node
from rclpy.clock import Clock, ClockType
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Joy
from std_msgs.msg import Bool

from .logic import ManualState, valid_source_stamp


class ManualJoy(Node):
    def __init__(self):
        super().__init__('manual_joy')
        self.declare_parameter('throttle_axis', 1)
        self.declare_parameter('steering_axis', 0)
        self.declare_parameter('deadman_button', 4)
        self.declare_parameter('max_speed', 0.3)
        self.declare_parameter('max_steer', 0.4)
        self.declare_parameter('neutral_tolerance', 0.08)
        self.declare_parameter('timeout', 0.3)
        self.declare_parameter('allow_reverse', False)
        self.declare_parameter('max_source_age', 0.3)
        self.declare_parameter('future_tolerance', 0.05)
        self.max_source_age = self.get_parameter('max_source_age').value
        self.future_tolerance = self.get_parameter('future_tolerance').value
        if (not math.isfinite(self.max_source_age) or self.max_source_age <= 0
                or not math.isfinite(self.future_tolerance)
                or self.future_tolerance < 0):
            raise ValueError('Invalid joystick timestamp limits')
        self.throttle_axis = self.get_parameter('throttle_axis').value
        self.steering_axis = self.get_parameter('steering_axis').value
        self.deadman_button = self.get_parameter('deadman_button').value
        if min(self.throttle_axis, self.steering_axis, self.deadman_button) < 0:
            raise ValueError('Joystick indices must be nonnegative')
        self.state = ManualState(
            self.get_parameter('max_speed').value,
            self.get_parameter('max_steer').value,
            self.get_parameter('neutral_tolerance').value,
            self.get_parameter('allow_reverse').value,
            self.get_parameter('timeout').value,
        )
        self.enable_pub = self.create_publisher(Bool, '/manual/enable', 10)
        self.drive_pub = self.create_publisher(AckermannDriveStamped, '/drive/manual', 10)
        self.create_subscription(Joy, '/joy', self.on_joy, qos_profile_sensor_data)
        self.steady_clock = Clock(clock_type=ClockType.STEADY_TIME)
        self.create_timer(0.05, self.on_timer, clock=self.steady_clock)

    def publish(self, enabled, speed=0.0, steering=0.0, source_stamp=None):
        enable = Bool()
        enable.data = enabled
        self.enable_pub.publish(enable)
        drive = AckermannDriveStamped()
        drive.header.stamp = (source_stamp if source_stamp is not None
                              else self.get_clock().now().to_msg())
        drive.header.frame_id = 'base_link'
        drive.drive.speed = speed
        drive.drive.steering_angle = steering
        self.drive_pub.publish(drive)

    def on_joy(self, msg):
        try:
            if not valid_source_stamp(msg.header.stamp, self.get_clock().now().nanoseconds,
                                      self.max_source_age, self.future_tolerance):
                raise ValueError('stale, future, or invalid joystick timestamp')
            throttle = msg.axes[self.throttle_axis]
            steer = msg.axes[self.steering_axis]
            button = msg.buttons[self.deadman_button]
            if button not in (0, 1):
                raise ValueError('invalid deadman')
            result = self.state.update(throttle, steer, bool(button), time.monotonic())
        except (IndexError, ValueError, TypeError):
            self.state.reset()
            self.publish(False)
            return
        self.publish(*result, source_stamp=msg.header.stamp)

    def on_timer(self):
        if not self.state.fresh(time.monotonic()):
            self.publish(False)


def main(args=None):
    rclpy.init(args=args)
    node = ManualJoy()
    try:
        rclpy.spin(node)
    finally:
        node.publish(False)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
