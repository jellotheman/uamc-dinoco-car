import cv2
import math
import time
from cv_bridge import CvBridgeError
import rclpy
from rclpy.node import Node
from rclpy.executors import ExternalShutdownException
from rclpy.qos import qos_profile_sensor_data
from rclpy.time import Time
from cv_bridge import CvBridge
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Path
from sensor_msgs.msg import CameraInfo, Image
from tf2_ros import Buffer, TransformException, TransformListener

from .geometry import transform_parts
from .lane import detect_lane
from .lane_debug import render_lane_debug


class LaneDetector(Node):
    def __init__(self):
        super().__init__('lane_detector')
        for name, value in [('base_frame', 'base_link'), ('near', 0.25), ('far', 1.5),
                            ('half_width', 0.75), ('min_width', 0.35), ('max_width', 0.95),
                            ('adaptive_block_size', 199), ('adaptive_c', -10.0),
                            ('window_height', 0.12), ('window_margin', 0.12),
                            ('min_rows', 12), ('image_timeout', 0.5),
                            ('ground_z', 0.0), ('debug_enabled', False), ('debug_rate_hz', 5.0)]:
            self.declare_parameter(name, value)
        self.info = None
        self.bridge = CvBridge()
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.publisher = self.create_publisher(Path, '/perception/lane', 10)
        self.debug_publisher = self.create_publisher(Image, '/perception/lane/debug_image', qos_profile_sensor_data)
        self.last_debug = 0.0
        self.create_subscription(CameraInfo, '/camera/camera_info', self.on_info, qos_profile_sensor_data)
        self.create_subscription(Image, '/camera/image_raw', self.on_image, qos_profile_sensor_data)

    def p(self, name):
        return self.get_parameter(name).value

    def on_info(self, msg):
        self.info = msg

    def on_image(self, msg):
        path = Path()
        path.header.stamp = msg.header.stamp
        path.header.frame_id = self.p('base_frame')
        debug = None
        try:
            rate = self.p('debug_rate_hz')
            if (self.p('debug_enabled') and math.isfinite(rate) and rate > 0 and
                    self.debug_publisher.get_subscription_count() > 0 and
                    time.monotonic() - self.last_debug >= 1.0/rate):
                debug = {}
                self.last_debug = time.monotonic()
        except Exception:
            pass
        valid = False
        try:
            age = (self.get_clock().now() - Time.from_msg(msg.header.stamp)).nanoseconds / 1e9
            if age > self.p('image_timeout') or age < -0.1:
                raise ValueError('image timestamp stale or future')
            info = self.info
            if info is None or not msg.header.frame_id or info.header.frame_id != msg.header.frame_id:
                raise ValueError('missing or mismatched camera calibration frame')
            if info.width != msg.width or info.height != msg.height:
                raise ValueError('camera calibration image dimensions differ')
            if info.distortion_model not in ('plumb_bob', 'rational_polynomial'):
                raise ValueError('unsupported distortion model')
            transform = self.tf_buffer.lookup_transform(path.header.frame_id, msg.header.frame_id,
                                                        Time.from_msg(msg.header.stamp))
            rotation, translation = transform_parts(transform.transform)
            image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            points = detect_lane(image, info.k, info.d, rotation, translation,
                                 near=self.p('near'), far=self.p('far'),
                                 half_width=self.p('half_width'), min_width=self.p('min_width'),
                                 max_width=self.p('max_width'),
                                 adaptive_block_size=self.p('adaptive_block_size'),
                                 adaptive_c=self.p('adaptive_c'),
                                 window_height=self.p('window_height'),
                                 window_margin=self.p('window_margin'),
                                 min_rows=self.p('min_rows'), ground_z=self.p('ground_z'), debug=debug)
            valid = True
            for x, y in points:
                pose = PoseStamped()
                pose.header = path.header
                pose.pose.position.x = float(x)
                pose.pose.position.y = float(y)
                pose.pose.orientation.w = 1.0
                path.poses.append(pose)
        except (ValueError, TransformException, TypeError, RuntimeError, CvBridgeError, cv2.error) as exc:
            self.get_logger().warning(f'lane invalid: {exc}', throttle_duration_sec=2.0)
        self.publisher.publish(path)
        if debug is not None:
            try:
                image = self.bridge.cv2_to_imgmsg(render_lane_debug(debug, valid), encoding='bgr8')
                image.header = msg.header
                self.debug_publisher.publish(image)
            except Exception as exc:
                self.get_logger().warning(f'lane debug failed: {exc}', throttle_duration_sec=2.0)


def main(args=None):
    rclpy.init(args=args)
    node = LaneDetector()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    except RuntimeError:
        if rclpy.ok():
            raise
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
