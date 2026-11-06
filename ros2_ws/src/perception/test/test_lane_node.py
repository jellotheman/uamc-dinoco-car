"""The ROS adapter preserves source timing and fails closed around lane detection."""
from types import SimpleNamespace

import cv2
import numpy as np
import rclpy
from rclpy.parameter import Parameter
from cv_bridge import CvBridge
from geometry_msgs.msg import TransformStamped
from sensor_msgs.msg import CameraInfo

from uamc_perception.lane_node import LaneDetector
from test_lane_tracking import road_image


def test_lane_callback_publishes_metric_path_then_empty_path_on_lost_markings():
    rclpy.init()
    node = LaneDetector()
    try:
        image, k, rotation, translation = road_image(brightness=150)
        transform = TransformStamped()
        transform.transform.translation.x = float(translation[0])
        transform.transform.translation.y = float(translation[1])
        transform.transform.translation.z = float(translation[2])
        axis_angle = cv2.Rodrigues(rotation)[0].ravel()
        angle = np.linalg.norm(axis_angle)
        quaternion = np.r_[axis_angle * np.sin(angle / 2) / angle, np.cos(angle / 2)]
        q = transform.transform.rotation
        q.x, q.y, q.z, q.w = map(float, quaternion)
        node.tf_buffer = SimpleNamespace(lookup_transform=lambda *_: transform)
        outputs = []
        node.publisher = SimpleNamespace(publish=outputs.append)
        stamp = node.get_clock().now().to_msg()
        info = CameraInfo()
        info.header.frame_id = 'camera_optical_frame'
        info.width, info.height = image.shape[1], image.shape[0]
        info.distortion_model = 'plumb_bob'
        info.k = k.ravel().tolist()
        info.d = [0.0] * 5
        node.on_info(info)

        bridge = CvBridge()
        message = bridge.cv2_to_imgmsg(image, encoding='bgr8')
        message.header.frame_id = info.header.frame_id
        message.header.stamp = stamp
        node.on_image(message)
        assert len(outputs[-1].poses) == 20
        assert outputs[-1].header.frame_id == 'base_link'
        assert outputs[-1].header.stamp == stamp

        # New tuning parameters must reach the algorithm; invalid tuning cannot
        # silently reuse a good detection or bypass detector validation.
        node.set_parameters([Parameter('adaptive_block_size', value=2)])
        node.on_image(message)
        assert outputs[-1].poses == []
        node.set_parameters([Parameter('adaptive_block_size', value=199)])

        # A subsequent frame with no markings must not retain the last good path.
        message.data = bridge.cv2_to_imgmsg(np.zeros_like(image), encoding='bgr8').data
        node.on_image(message)
        assert outputs[-1].poses == []
        assert outputs[-1].header.frame_id == 'base_link'
        assert outputs[-1].header.stamp == stamp
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
