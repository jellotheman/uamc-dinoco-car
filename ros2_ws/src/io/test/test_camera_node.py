import pytest
import rclpy
from rclpy.parameter import Parameter
from uamc_io import camera_node

class FakeCapture:
    calls = []
    def __init__(self, *args):
        self.calls.append(args)
        self.negotiated = None
    def close(self):
        return True
    def poll(self, *args):
        return None

@pytest.fixture
def ros():
    rclpy.init()
    yield
    rclpy.shutdown()

def overrides(*extra):
    return ["--ros-args", "-p", "device:=/dev/v4l/by-id/test", "-p", "width:=640",
            "-p", "height:=480", "-p", "fps:=30.0", "-p", "frame_id:=camera"] + list(extra)

def test_node_parameters_read_only(monkeypatch):
    monkeypatch.setattr(camera_node, "CameraCapture", FakeCapture)
    rclpy.init(args=overrides())
    node = camera_node.CameraNode()
    try:
        assert node.get_name() == "real_camera"
        assert not node.set_parameters([Parameter("width", value=320)])[0].successful
        assert not node.set_parameters([Parameter("use_sim_time", value=True)])[0].successful
        node._tick()
    finally:
        node.destroy_node()
        rclpy.shutdown()

def test_invalid_calibration_does_not_open(monkeypatch):
    monkeypatch.setattr(camera_node, "CameraCapture", FakeCapture)
    FakeCapture.calls.clear()
    rclpy.init(args=overrides("-p", "calibration_file:=/missing/camera.yaml"))
    try:
        with pytest.raises(FileNotFoundError):
            camera_node.CameraNode()
        assert not FakeCapture.calls
    finally:
        rclpy.shutdown()

def test_sim_time_rejected(monkeypatch):
    monkeypatch.setattr(camera_node, "CameraCapture", FakeCapture)
    FakeCapture.calls.clear()
    rclpy.init(args=overrides("-p", "use_sim_time:=true"))
    try:
        with pytest.raises(ValueError, match="use_sim_time"):
            camera_node.CameraNode()
        assert not FakeCapture.calls
    finally:
        rclpy.shutdown()


@pytest.mark.parametrize("exc", [KeyboardInterrupt, camera_node.ExternalShutdownException])
def test_main_handles_normal_shutdown(monkeypatch, exc):
    events = []
    class Node:
        def destroy_node(self):
            events.append("destroy")
    monkeypatch.setattr(camera_node.rclpy, "init", lambda **kwargs: events.append("init"))
    monkeypatch.setattr(camera_node, "CameraNode", Node)
    def spin(node):
        raise exc()
    monkeypatch.setattr(camera_node.rclpy, "spin", spin)
    monkeypatch.setattr(camera_node.rclpy, "try_shutdown", lambda: events.append("shutdown"))
    camera_node.main()
    assert events == ["init", "destroy", "shutdown"]


def _calibration_file(tmp_path):
    import yaml
    value = {
        "image_width": 640, "image_height": 480, "distortion_model": "plumb_bob",
        "camera_matrix": {"rows": 3, "cols": 3, "data": [500, 0, 320, 0, 500, 240, 0, 0, 1]},
        "distortion_coefficients": {"rows": 1, "cols": 5, "data": [0, 0, 0, 0, 0]},
        "rectification_matrix": {"rows": 3, "cols": 3, "data": [1, 0, 0, 0, 1, 0, 0, 0, 1]},
        "projection_matrix": {"rows": 3, "cols": 4, "data": [500, 0, 320, 0, 0, 500, 240, 0, 0, 0, 1, 0]},
    }
    path = tmp_path / "calibration.yaml"
    path.write_text(yaml.safe_dump(value))
    return path


@pytest.mark.parametrize("calibrated", [False, True])
def test_dds_image_and_optional_matching_info(monkeypatch, tmp_path, calibrated):
    import time
    import numpy as np
    from builtin_interfaces.msg import Time
    from rclpy.executors import SingleThreadedExecutor
    from rclpy.qos import qos_profile_sensor_data
    from sensor_msgs.msg import CameraInfo, Image

    class OneFrame(FakeCapture):
        def __init__(self, *args):
            super().__init__(*args)
            self.next_frame = None

        def poll(self, *args):
            result, self.next_frame = self.next_frame, None
            return result

    monkeypatch.setattr(camera_node, "CameraCapture", OneFrame)
    extra = ("-p", "calibration_file:=" + str(_calibration_file(tmp_path))) if calibrated else ()
    image_topic = "/test/uamc_camera/image"
    info_topic = "/test/uamc_camera/info"
    rclpy.init(args=overrides(*extra, "-r", "/camera/image_raw:=" + image_topic,
                             "-r", "/camera/camera_info:=" + info_topic))
    node = None
    observer = None
    executor = SingleThreadedExecutor()
    try:
        node = camera_node.CameraNode()
        observer = rclpy.create_node("camera_test_observer")
        images, infos = [], []
        image_sub = observer.create_subscription(Image, image_topic, images.append, qos_profile_sensor_data)
        info_sub = observer.create_subscription(CameraInfo, info_topic, infos.append, qos_profile_sensor_data)
        executor.add_node(node)
        executor.add_node(observer)
        deadline = time.monotonic() + 3
        while (node.image_pub.get_subscription_count() < 1 or
               (calibrated and node.info_pub.get_subscription_count() < 1)) and time.monotonic() < deadline:
            executor.spin_once(timeout_sec=0.05)
        assert node.image_pub.get_subscription_count() >= 1
        if calibrated:
            assert node.info_pub.get_subscription_count() >= 1
        else:
            assert node.info_pub is None
            assert observer.count_publishers(info_topic) == 0

        frame = np.arange(480 * 640 * 3, dtype=np.uint8).reshape(480, 640, 3)
        stamp = Time(sec=123, nanosec=456)
        node.capture.next_frame = (frame, time.monotonic(), stamp)
        node._tick()
        deadline = time.monotonic() + 3
        while (not images or (calibrated and not infos)) and time.monotonic() < deadline:
            executor.spin_once(timeout_sec=0.05)
        assert len(images) == 1
        image = images[0]
        assert image.header.stamp == stamp
        assert image.header.frame_id == "camera"
        assert (image.width, image.height, image.encoding, image.step, image.is_bigendian) == (640, 480, "bgr8", 1920, 0)
        assert bytes(image.data) == frame.tobytes()
        if calibrated:
            assert len(infos) == 1
            info = infos[0]
            assert info.header == image.header
            assert (info.width, info.height, info.distortion_model) == (640, 480, "plumb_bob")
            assert list(info.k) == [500, 0, 320, 0, 500, 240, 0, 0, 1]
        else:
            assert not infos
        # Keep subscriptions alive throughout the test.
        assert image_sub is not None and info_sub is not None
    finally:
        executor.shutdown()
        if observer is not None:
            observer.destroy_node()
        if node is not None:
            node.destroy_node()
        rclpy.try_shutdown()


def test_capture_failure_propagates(monkeypatch):
    class FailedCapture(FakeCapture):
        def poll(self, *args):
            raise RuntimeError("simulated camera loss")
    monkeypatch.setattr(camera_node, "CameraCapture", FailedCapture)
    rclpy.init(args=overrides())
    node = None
    try:
        node = camera_node.CameraNode()
        with pytest.raises(RuntimeError, match="simulated camera loss"):
            node._tick()
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.try_shutdown()
