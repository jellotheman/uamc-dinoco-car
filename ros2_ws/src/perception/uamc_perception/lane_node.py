import cv2
from cv_bridge import CvBridgeError
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.time import Time
from cv_bridge import CvBridge
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Path
from sensor_msgs.msg import CameraInfo, Image
from tf2_ros import Buffer, TransformException, TransformListener

from .geometry import transform_parts
from .lane import detect_lane


class LaneDetector(Node):
    def __init__(self):
        super().__init__('lane_detector')
        for name, value in [('base_frame', 'base_link'), ('near', 0.25), ('far', 1.5),
                            ('half_width', 0.75), ('min_width', 0.35), ('max_width', 0.95),
                            ('threshold', 190), ('min_rows', 12), ('image_timeout', 0.5)]:
            self.declare_parameter(name, value)
        self.info = None
        self.bridge = CvBridge()
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.publisher = self.create_publisher(Path, '/perception/lane', 10)
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
                                 max_width=self.p('max_width'), threshold=self.p('threshold'),
                                 min_rows=self.p('min_rows'))
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


def main(args=None):
    rclpy.init(args=args)
    node = LaneDetector()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
