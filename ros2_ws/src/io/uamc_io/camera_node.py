"""ROS publisher for an explicitly configured local V4L2 camera."""
import math
import re
import rclpy
from rcl_interfaces.msg import ParameterDescriptor, SetParametersResult
from rclpy.node import Node
from rclpy.executors import ExternalShutdownException
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CameraInfo, Image

from .camera_calibration import load_calibration
from .camera_capture import CameraCapture

class CameraNode(Node):
    def __init__(self):
        super().__init__("real_camera")
        self.capture = None
        try:
            descriptor = ParameterDescriptor(read_only=True)
            defaults = {"device": "", "width": 0, "height": 0, "fps": 0.0,
                        "fourcc": "MJPG", "frame_id": "", "calibration_file": "",
                        "max_frame_age": 0.3, "startup_timeout": 5.0, "frame_timeout": 1.0}
            for name, value in defaults.items():
                self.declare_parameter(name, value, descriptor)
            p = {name: self.get_parameter(name).value for name in defaults}
            if self.get_parameter("use_sim_time").value:
                raise ValueError("real camera requires use_sim_time=false")
            if not re.fullmatch(r"/dev/v4l/by-(?:id|path)/[^/]+", p["device"]):
                raise ValueError("device must be an explicit /dev/v4l/by-id/ or by-path/ path")
            if p["width"] <= 0 or p["height"] <= 0 or not p["frame_id"].strip():
                raise ValueError("positive width, height and nonempty frame_id are required")
            if len(p["fourcc"]) != 4 or not p["fourcc"].isascii() or not p["fourcc"].isprintable():
                raise ValueError("fourcc must contain four printable ASCII characters")
            for key in ("fps", "max_frame_age", "startup_timeout", "frame_timeout"):
                if not math.isfinite(p[key]) or p[key] <= 0:
                    raise ValueError(f"{key} must be finite and positive")
            self.p = p
            self.calibration = (load_calibration(p["calibration_file"], p["width"], p["height"])
                                if p["calibration_file"] else None)
            self.image_pub = self.create_publisher(Image, "/camera/image_raw", qos_profile_sensor_data)
            self.info_pub = (self.create_publisher(CameraInfo, "/camera/camera_info", qos_profile_sensor_data)
                             if self.calibration else None)
            self.add_on_set_parameters_callback(self._validate_parameter_update)
            self.capture = CameraCapture(p["device"], p["width"], p["height"], p["fps"],
                                         p["fourcc"], lambda: self.get_clock().now().to_msg())
            self.logged = False
            self.timer = self.create_timer(min(0.02, 1.0 / p["fps"]), self._tick)
        except Exception:
            if self.capture is not None:
                self.capture.close()
            self.destroy_node()
            raise

    def _validate_parameter_update(self, params):
        if any(p.name == "use_sim_time" and p.value is not False for p in params):
            return SetParametersResult(successful=False, reason="real camera requires wall time")
        return SetParametersResult(successful=True)

    def _tick(self):
        result = self.capture.poll(self.p["startup_timeout"], self.p["frame_timeout"], self.p["max_frame_age"])
        if not self.logged and self.capture.negotiated is not None:
            w, h, fps, fourcc = self.capture.negotiated
            fmt = "".join(chr((int(fourcc) >> (8*i)) & 255) for i in range(4))
            self.get_logger().info(f"Negotiated {w:g}x{h:g} {fmt}, nominal FPS {fps:g}; requested {self.p['fps']:g} FPS")
            self.logged = True
        if result is None:
            return
        frame, _, stamp = result
        msg = Image()
        msg.header.stamp = stamp
        msg.header.frame_id = self.p["frame_id"]
        msg.width, msg.height = self.p["width"], self.p["height"]
        msg.encoding, msg.is_bigendian, msg.step = "bgr8", 0, self.p["width"] * 3
        msg.data = frame.tobytes()
        self.image_pub.publish(msg)
        if self.calibration:
            c = self.calibration
            info = CameraInfo()
            info.header = msg.header
            info.width, info.height = c.width, c.height
            info.distortion_model = c.model
            info.k, info.d, info.r, info.p = list(c.k), list(c.d), list(c.r), list(c.p)
            self.info_pub.publish(info)

    def destroy_node(self):
        if self.capture is not None:
            if not self.capture.close():
                self.get_logger().error("Camera worker remains blocked; device release may await process exit")
            self.capture = None
        return super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = CameraNode()
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.try_shutdown()
