"""Fail-closed vehicle transport and independently monitored real serial link."""
import math
import time

from ackermann_msgs.msg import AckermannDriveStamped
import rclpy
from rclpy.node import Node
from rclpy.executors import ExternalShutdownException
from rclpy.clock import Clock, ClockType
from uamc_interfaces.msg import VehicleStatus

from .logic import FakeTransport, valid_source_stamp
from .calibration import load_calibration, map_command, validate_caps
from .hardware_health import HardwareHealth
from .serial_transport import SerialTransport


class VehicleIO(Node):
    def __init__(self):
        super().__init__('vehicle_io')
        defaults = {'transport': 'disabled', 'max_speed': 0.3, 'max_steer': 0.4,
                    'command_timeout': 0.3, 'serial_device': '', 'serial_baud': 115200,
                    'calibration_file': '', 'handshake_timeout': 5.0, 'write_timeout': 0.1,
                    'health_timeout': 0.3, 'max_source_age': 0.3, 'future_tolerance': 0.05}
        for key, value in defaults.items():
            self.declare_parameter(key, value)
        p = {key: self.get_parameter(key).value for key in defaults}
        self.transport = p['transport']
        if self.transport not in ('disabled', 'fake', 'real'):
            raise ValueError('transport must be disabled, fake, or real')
        self.fake = FakeTransport(p['max_speed'], p['max_steer'], p['command_timeout'])
        self.link = None
        self.health = None
        self.calibration = None
        self.last_command = None
        self.last_stamp = 0
        self.last_ros_time = 0
        self.invalidated = True
        self.qualified = False
        self.command_fault = False
        self.below_envelope = False
        self.p = p
        if self.transport == 'real':
            for key in ('handshake_timeout', 'write_timeout', 'command_timeout', 'health_timeout', 'max_source_age', 'max_speed', 'max_steer'):
                if isinstance(p[key], bool) or not isinstance(p[key], (int, float)) or not math.isfinite(p[key]) or p[key] <= 0:
                    raise ValueError('invalid ' + key)
            for key, maximum in (('handshake_timeout', 30), ('write_timeout', 0.5), ('command_timeout', 5), ('health_timeout', 5), ('max_source_age', 5), ('future_tolerance', 1)):
                if p[key] > maximum:
                    raise ValueError(key + ' exceeds bounded maximum')
            if not isinstance(p['future_tolerance'], (int, float)) or isinstance(p['future_tolerance'], bool) or not math.isfinite(p['future_tolerance']) or p['future_tolerance'] < 0:
                raise ValueError('invalid future_tolerance')
            if not isinstance(p['serial_device'], str) or not p['serial_device'].strip() or type(p['serial_baud']) is not int or p['serial_baud'] != 115200:
                raise ValueError('explicit serial device and baud 115200 required')
            self.calibration = load_calibration(p['calibration_file'])
            validate_caps(self.calibration, p['max_speed'], p['max_steer'])
            self.health = HardwareHealth(p['health_timeout'], p['max_source_age'], p['future_tolerance'])
            self.link = SerialTransport(p['serial_device'], p['serial_baud'], p['handshake_timeout'], p['write_timeout'], map_command(self.calibration, 0, 0))
            self.create_subscription(VehicleStatus, '/hardware/status', self.on_health, 10)
        self.status_pub = self.create_publisher(VehicleStatus, '/vehicle/status', 10)
        self.fake_pub = self.create_publisher(AckermannDriveStamped, '/io/fake_applied_command', 10)
        self.create_subscription(AckermannDriveStamped, '/drive/command', self.on_command, 10)
        self.steady_clock = Clock(clock_type=ClockType.STEADY_TIME)
        self.create_timer(0.05, self.on_timer, clock=self.steady_clock)

    def invalidate(self):
        if not self.invalidated:
            self.command_fault = True
        self.qualified = False
        self.below_envelope = False
        self.last_command = None
        if self.link is not None and not self.invalidated:
            self.link.invalidate()
        self.invalidated = True

    def on_health(self, msg):
        now = time.monotonic()
        self.health.accept(msg, self.get_clock().now().nanoseconds, now)
        if not self._health_state(now)[0]:
            self.invalidate()

    def _health_state(self, steady):
        if not self.link.ready:
            return False, False, True, self.link.error or 'Serial link unavailable'
        if self.health.received is None or self.health.received <= self.link.connected_at:
            return False, False, True, 'Fresh independent hardware status required after connection'
        return self.health.state(self.get_clock().now().nanoseconds, steady)

    def on_command(self, msg):
        steady = time.monotonic()
        if self.transport == 'fake':
            self.fake.accept(msg.drive.speed, msg.drive.steering_angle, steady)
            return
        if self.transport != 'real':
            return
        now_ns = self.get_clock().now().nanoseconds
        stamp = msg.header.stamp.sec * 1000000000 + msg.header.stamp.nanosec
        if (msg.header.frame_id != 'base_link' or now_ns < self.last_ros_time or stamp <= self.last_stamp or
                not valid_source_stamp(msg.header.stamp, now_ns, self.p['max_source_age'], self.p['future_tolerance']) or
                not self._health_state(steady)[0]):
            self.last_ros_time = now_ns
            self.invalidate()
            return
        self.last_ros_time, self.last_stamp = now_ns, stamp
        try:
            speed, steer = msg.drive.speed, msg.drive.steering_angle
            if not math.isfinite(speed) or not math.isfinite(steer) or speed < 0 or speed > self.p['max_speed'] or abs(steer) > self.p['max_steer']:
                raise ValueError('command outside operating caps')
            if self.qualified and (speed != 0 or steer != 0) and not self.link.neutral_confirmed():
                return
            if not self.qualified and (speed != 0 or steer != 0):
                self.invalidate()
                return
            pair = map_command(self.calibration, speed, steer)
        except ValueError:
            self.invalidate()
            return
        # Queue expires at the earliest source, receipt or health deadline.
        source_remaining = (stamp + self.p['max_source_age'] * 1e9 - now_ns) / 1e9
        health_remaining = min(self.p['health_timeout'] - (steady - self.health.received),
                               (self.health.last_stamp + self.p['max_source_age'] * 1e9 - now_ns) / 1e9)
        deadline = steady + min(self.p['command_timeout'], source_remaining, health_remaining)
        if deadline <= steady or not self.link.submit(pair, deadline):
            self.invalidate()
            return
        self.below_envelope = 0 < speed < self.calibration['throttle']['samples'][1][0]
        self.last_command = (msg.header.stamp, steady)
        self.invalidated = False
        if speed == 0 and steer == 0:
            self.qualified = True
            self.command_fault = False

    def on_timer(self):
        status = VehicleStatus()
        now = self.get_clock().now()
        steady = time.monotonic()
        status.header.stamp = now.to_msg()
        status.header.frame_id = 'base_link'
        if self.transport == 'real':
            status.ready, status.estop, status.fault, status.reason = self._health_state(steady)
            if (now.nanoseconds < self.last_ros_time or not status.ready or
                    (self.last_command is not None and
                     (steady - self.last_command[1] > self.p['command_timeout'] or
                      not valid_source_stamp(self.last_command[0], now.nanoseconds, self.p['max_source_age'], self.p['future_tolerance'])))):
                self.invalidate()
            self.last_ros_time = now.nanoseconds
            if status.ready and self.below_envelope:
                status.reason += '; speed below measured moving envelope, neutral throttle applied'
            if status.ready and self.command_fault:
                status.ready = False
                status.fault = True
                status.reason = 'Command invalidated; fresh neutral command required; ' + status.reason
        else:
            status.ready = self.transport == 'fake'
            status.estop = False
            status.fault = not status.ready
            status.reason = ('Test-only fake transport; no hardware is controlled' if status.ready else
                             'Hardware transport disabled; no actuation available')
        self.status_pub.publish(status)
        if self.transport == 'fake':
            speed, steer = self.fake.read(steady)
            output = AckermannDriveStamped()
            output.header = status.header
            output.drive.speed = speed
            output.drive.steering_angle = steer
            self.fake_pub.publish(output)

    def destroy_node(self):
        if self.link is not None:
            self.link.close()
        return super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = VehicleIO()
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    except RuntimeError as exc:
        if rclpy.ok() or not str(exc).startswith("Unable to convert call argument '0' to Python object"):
            raise
    finally:
        try:
            if node is not None:
                node.destroy_node()
        finally:
            rclpy.try_shutdown()


if __name__ == '__main__':
    main()
