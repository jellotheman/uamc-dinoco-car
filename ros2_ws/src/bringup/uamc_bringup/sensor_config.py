"""Allowlisted acquisition settings, independent of actuation and health."""
import re
from pathlib import Path
from .real_config import _mapping, _number, _text, _file


def _frame(value):
    value = _text(value, "sensor.frame_id")
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_/]*", value):
        raise ValueError("sensor frame_id must be a relative ROS frame without whitespace")
    return value


def validate_sensors(data, base):
    for key, source in (("camera", "opencv"), ("lidar", "sllidar_c1")):
        selected = data["sources"][key] == source
        if selected != (key in data):
            raise ValueError(f"{key} block is required exactly when its managed source is selected")
    if "camera" in data:
        camera = _mapping(data["camera"], ("device", "width", "height", "fps", "fourcc", "frame_id",
                                         "max_frame_age", "startup_timeout", "frame_timeout"),
                          ("calibration_file",), where="camera")
        device = _text(camera["device"], "camera.device")
        if not re.fullmatch(r"/dev/v4l/by-(?:id|path)/[^/]+", device) or ".." in device.split("/"):
            raise ValueError("camera.device must use an explicit stable /dev/v4l/by-* path")
        _frame(camera["frame_id"])
        for key in ("width", "height"):
            if type(camera[key]) is not int or not 1 <= camera[key] <= 8192:
                raise ValueError(f"camera.{key} must be a positive integer <=8192")
        camera["fps"] = _number(camera["fps"], "camera.fps")
        if camera["fps"] > 240 or camera["fourcc"] != "MJPG":
            raise ValueError("camera supports MJPG at a requested rate <=240 FPS")
        for key, bound in (("max_frame_age", 1), ("startup_timeout", 30), ("frame_timeout", 5)):
            camera[key] = _number(camera[key], "camera." + key)
            if camera[key] > bound:
                raise ValueError(f"camera.{key} exceeds {bound} seconds")
        if "calibration_file" in camera:
            camera["calibration_file"] = _file(base, camera["calibration_file"], "camera.calibration_file")
            from uamc_io.camera_calibration import load_calibration
            load_calibration(camera["calibration_file"], camera["width"], camera["height"])
    if "lidar" in data:
        lidar = _mapping(data["lidar"], ("device", "baud", "frame_id", "inverted", "angle_compensate", "scan_mode"), where="lidar")
        device = _text(lidar["device"], "lidar.device")
        if not re.fullmatch(r"/dev/serial/by-(?:id|path)/[^/]+", device) or ".." in device.split("/"):
            raise ValueError("lidar.device must use an explicit stable /dev/serial/by-* path")
        _frame(lidar["frame_id"])
        if type(lidar["baud"]) is not int or lidar["baud"] != 460800:
            raise ValueError("C1 baud must be 460800")
        if any(type(lidar[key]) is not bool for key in ("inverted", "angle_compensate")):
            raise ValueError("LiDAR orientation/compensation flags must be booleans")
        if lidar["scan_mode"] != "Standard":
            raise ValueError("C1 integration currently supports Standard scan mode only")
        serial = data.get("serial")
        if isinstance(serial, dict) and isinstance(serial.get("device"), str):
            if Path(serial["device"]).resolve() == Path(device).resolve():
                raise ValueError("LiDAR and actuator cannot own the same serial device")
