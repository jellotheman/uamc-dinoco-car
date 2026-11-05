import math
import time
import rclpy
from rclpy.node import Node
from rclpy.executors import ExternalShutdownException
from rclpy.clock import Clock, ClockType
from rclpy.qos import qos_profile_sensor_data
from rclpy.time import Time
from ackermann_msgs.msg import AckermannDriveStamped
from sensor_msgs.msg import LaserScan
from tf2_ros import Buffer, TransformException, TransformListener
from uamc_interfaces.msg import Obstacle

from .geometry import transform_parts
from .obstacle import swept_obstacle


class ObstacleDetector(Node):
    def __init__(self):
        super().__init__('obstacle_detector')
        # Conservative 0.40 x 0.26 m envelope around rear-axle base_link;
        # contains the supplied 0.345 x 0.205 m car and steered tires.
        for name, value in [('base_frame', 'base_link'), ('wheelbase', 0.232),
                            ('front', 0.30), ('rear', 0.10), ('half_width', 0.13),
                            ('lookahead', 1.0), ('scan_timeout', 0.5), ('command_timeout', 0.5)]:
            self.declare_parameter(name, value)
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.curvature = None
        self.command_time = None
        self.scan_time = None
        self.scan_header = None
        self.publisher = self.create_publisher(Obstacle, '/perception/obstacle', 10)
        self.create_subscription(LaserScan, '/scan', self.on_scan, qos_profile_sensor_data)
        self.create_subscription(AckermannDriveStamped, '/drive/command', self.on_command, 10)
        self.steady_clock = Clock(clock_type=ClockType.STEADY_TIME)
        self.create_timer(0.1, self.watchdog, clock=self.steady_clock)

    def p(self, name):
        return self.get_parameter(name).value

    def on_command(self, msg):
        steering = msg.drive.steering_angle
        wheelbase = self.p('wheelbase')
        if math.isfinite(steering) and abs(steering) < 1.4 and wheelbase > 0:
            self.curvature = math.tan(steering)/wheelbase
            self.command_time = time.monotonic()
        else:
            self.curvature = None
            self.command_time = None

    def publish_invalid(self, reason):
        msg = Obstacle()
        if self.scan_header is not None:
            msg.header = self.scan_header
        else:
            msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.p('base_frame')
        msg.valid = False
        msg.detected = False
        msg.clearance_m = 0.0
        msg.reason = reason
        self.publisher.publish(msg)

    def watchdog(self):
        now = time.monotonic()
        if self.scan_time is None or now-self.scan_time > self.p('scan_timeout'):
            self.publish_invalid('scan stale or missing')
        elif self.command_time is None or now-self.command_time > self.p('command_timeout'):
            self.publish_invalid('drive command stale or missing')

    def on_scan(self, scan):
        self.scan_time = time.monotonic()
        self.scan_header = scan.header
        try:
            age = (self.get_clock().now() - Time.from_msg(scan.header.stamp)).nanoseconds / 1e9
            if age > self.p('scan_timeout') or age < -0.1:
                raise ValueError('scan timestamp stale or future')
            if not scan.header.frame_id:
                raise ValueError('missing scan frame')
            if (self.command_time is None or
                    time.monotonic()-self.command_time > self.p('command_timeout')):
                raise ValueError('drive command stale or missing')
            tf = self.tf_buffer.lookup_transform(self.p('base_frame'), scan.header.frame_id,
                                                 Time.from_msg(scan.header.stamp))
            rotation, translation = transform_parts(tf.transform)
            detected, clearance = swept_obstacle(
                scan.ranges, scan.angle_min, scan.angle_increment, scan.range_min, scan.range_max,
                rotation, translation, self.curvature, front=self.p('front'), rear=self.p('rear'),
                half_width=self.p('half_width'), lookahead=self.p('lookahead'))
            output = Obstacle()
            output.header = scan.header
            output.header.frame_id = self.p('base_frame')
            output.valid = True
            output.detected = detected
            output.clearance_m = clearance if detected else self.p('lookahead')
            output.reason = 'obstacle in swept corridor' if detected else 'clear to configured lookahead'
            self.publisher.publish(output)
        except (ValueError, TransformException, TypeError, RuntimeError) as exc:
            self.publish_invalid(str(exc))


def main(args=None):
    rclpy.init(args=args)
    node = ObstacleDetector()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
