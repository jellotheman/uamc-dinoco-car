"""Test-only transport and an explicitly disabled hardware interface.

No pinout, firmware protocol, cutoff status or wheel feedback is assumed.
"""
import time

from ackermann_msgs.msg import AckermannDriveStamped
import rclpy
from rclpy.node import Node
from rclpy.clock import Clock, ClockType
from uamc_interfaces.msg import VehicleStatus

from .logic import FakeTransport


class VehicleIO(Node):
    def __init__(self):
        super().__init__('vehicle_io')
        self.declare_parameter('transport', 'disabled')
        self.declare_parameter('max_speed', 0.3)
        self.declare_parameter('max_steer', 0.4)
        self.declare_parameter('command_timeout', 0.3)
        self.transport = self.get_parameter('transport').value
        if self.transport not in ('disabled', 'fake', 'real'):
            raise ValueError('transport must be disabled, fake, or real')
        self.fake = FakeTransport(
            self.get_parameter('max_speed').value,
            self.get_parameter('max_steer').value,
            self.get_parameter('command_timeout').value,
        )
        self.status_pub = self.create_publisher(VehicleStatus, '/vehicle/status', 10)
        self.fake_pub = self.create_publisher(
            AckermannDriveStamped, '/io/fake_applied_command', 10)
        self.create_subscription(AckermannDriveStamped, '/drive/command', self.on_command, 10)
        self.steady_clock = Clock(clock_type=ClockType.STEADY_TIME)
        self.create_timer(0.05, self.on_timer, clock=self.steady_clock)

    def on_command(self, msg):
        if self.transport == 'fake':
            self.fake.accept(msg.drive.speed, msg.drive.steering_angle, time.monotonic())

    def on_timer(self):
        status = VehicleStatus()
        status.header.stamp = self.get_clock().now().to_msg()
        status.header.frame_id = 'base_link'
        status.ready = self.transport == 'fake'
        status.estop = False
        status.fault = self.transport != 'fake'
        status.reason = ('Test-only fake transport; no hardware is controlled'
                         if status.ready else
                         'Hardware transport disabled or unverified; no actuation available')
        self.status_pub.publish(status)
        if self.transport == 'fake':
            speed, steer = self.fake.read(time.monotonic())
            output = AckermannDriveStamped()
            output.header = status.header
            output.drive.speed = speed
            output.drive.steering_angle = steer
            self.fake_pub.publish(output)


def main(args=None):
    rclpy.init(args=args)
    node = VehicleIO()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
