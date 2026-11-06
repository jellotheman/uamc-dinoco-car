"""Explicit sensor ownership is independent of real actuation authority."""
import copy
import importlib.util
from pathlib import Path
import pytest
import yaml
from launch import LaunchContext
from ament_index_python.packages import PackageNotFoundError
from uamc_bringup.real_config import load_profile, validate_tuning
from uamc_bringup import sensor_launch


def fixture():
    return {"schema_version": 1, "identification": dict.fromkeys(
        ("hardware", "firmware", "measurement_record"), "synthetic fixture"),
        "sources": dict.fromkeys(("camera", "lidar", "imu", "wheel", "health"), "external")}


def camera():
    return {"device": "/dev/v4l/by-id/test", "width": 1280, "height": 720,
            "fps": 30.0, "fourcc": "MJPG", "frame_id": "camera_optical_frame",
            "max_frame_age": 0.3, "startup_timeout": 5.0, "frame_timeout": 1.0}


def lidar():
    return {"device": "/dev/serial/by-id/test", "baud": 460800, "frame_id": "laser",
            "inverted": False, "angle_compensate": True, "scan_mode": "Standard"}


def write(tmp_path, value):
    path = tmp_path / "profile.yaml"
    path.write_text(yaml.safe_dump(value))
    return str(path)


def test_sources_are_opt_in_and_exact(tmp_path):
    data = fixture()
    assert load_profile(write(tmp_path, data))["sources"]["camera"] == "external"
    assert sensor_launch.sensor_nodes({}) == []
    for sensor, choice, config in (("camera", "opencv", camera()), ("lidar", "sllidar_c1", lidar())):
        value = copy.deepcopy(data)
        value["sources"][sensor] = choice
        with pytest.raises(ValueError):
            load_profile(write(tmp_path, value))
        value[sensor] = config
        loaded = load_profile(write(tmp_path, value))
        assert loaded[sensor] == config
        with pytest.raises(ValueError):
            load_profile(write(tmp_path, value), "serial")
        value["sources"][sensor] = "external"
        with pytest.raises(ValueError):
            load_profile(write(tmp_path, value))


@pytest.mark.parametrize(("sensor", "field", "bad"), [
    ("camera", "device", 0), ("camera", "device", "/dev/video0"),
    ("camera", "width", True), ("camera", "height", -1),
    ("camera", "fps", float("nan")), ("camera", "fps", 241),
    ("camera", "fourcc", "YUYV"), ("camera", "frame_id", "/leading_slash"),
    ("camera", "frame_timeout", 6), ("camera", "calibration_file", "missing.yaml"),
    ("lidar", "baud", 115200), ("lidar", "inverted", "false"),
    ("lidar", "scan_mode", "guessed"), ("lidar", "device", "/dev/ttyUSB0"),
    ("lidar", "device", "/dev/serial/by-id/../../ttyUSB0"),
])
def test_invalid_sensor_values_rejected(tmp_path, sensor, field, bad):
    data = fixture()
    data["sources"][sensor] = "opencv" if sensor == "camera" else "sllidar_c1"
    data[sensor] = camera() if sensor == "camera" else lidar()
    data[sensor][field] = bad
    with pytest.raises(ValueError):
        load_profile(write(tmp_path, data))


def test_sensor_settings_cannot_be_tuning_overrides(tmp_path):
    for field in (*camera(), "serial_port", "serial_baudrate", "inverted", "angle_compensate", "scan_mode"):
        path = tmp_path / "tuning.yaml"
        path.write_text(yaml.safe_dump({"real_camera": {"ros__parameters": {field: "override"}}}))
        with pytest.raises(ValueError):
            validate_tuning(str(path))


def test_c1_missing_package_is_actionable(monkeypatch):
    def missing(name):
        raise PackageNotFoundError(name)
    monkeypatch.setattr(sensor_launch, "get_package_prefix", missing)
    with pytest.raises(ValueError, match="pinned sllidar_ros2"):
        sensor_launch.sensor_nodes({"sources": {"lidar": "sllidar_c1"}, "lidar": lidar()})


def test_selected_sensors_join_critical_supervision(tmp_path, monkeypatch):
    path = Path(__file__).resolve().parents[1] / "launch/real.launch.py"
    spec = importlib.util.spec_from_file_location("real_sensor_launch", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    data = fixture()
    data["sources"]["camera"] = "opencv"
    data["camera"] = camera()
    events = []
    monkeypatch.setattr(module, "acquire_session_locks", lambda: events.append("lock"))
    context = LaunchContext()
    context.launch_configurations.update({"mode": "auto", "actuation": "disabled", "rviz": "false",
        "rviz_frame": "base_link", "visualization_debug": "auto", "hardware_config": write(tmp_path, data), "params_file": ""})
    actions = module.start(context)
    nodes = [action for action in actions if isinstance(action, sensor_launch.Node)]
    assert events == ["lock"]
    # A handler for each node precedes all processes, including the selected camera.
    assert len(actions) == 2 * len(nodes)
    assert any(node.node_package == "uamc_io" and node.node_executable == "camera" for node in nodes)
    assert not any(node.node_package == "sllidar_ros2" for node in nodes)


def test_c1_uses_only_vendor_node_and_profile_values(tmp_path, monkeypatch):
    executable = tmp_path / "lib/sllidar_ros2/sllidar_node"
    executable.parent.mkdir(parents=True)
    executable.touch()
    monkeypatch.setattr(sensor_launch, "get_package_prefix", lambda name: str(tmp_path))
    nodes = sensor_launch.sensor_nodes({"sources": {"lidar": "sllidar_c1"}, "lidar": lidar()})
    assert len(nodes) == 1
    node = nodes[0]
    assert node.node_package == "sllidar_ros2"
    assert node.node_executable == "sllidar_node"
    # Parameter evaluation verifies the real types and blocks package-default ports.
    from launch_ros.utilities import evaluate_parameters
    values = evaluate_parameters(LaunchContext(), node._Node__parameters)[0]
    assert values == {"use_sim_time": False, "channel_type": "serial",
                      "serial_port": lidar()["device"], "serial_baudrate": 460800,
                      "frame_id": "laser", "inverted": False,
                      "angle_compensate": True, "scan_mode": "Standard"}


def test_shared_lidar_actuator_port_rejected(tmp_path):
    data = fixture()
    data["sources"]["lidar"] = "sllidar_c1"
    data["lidar"] = lidar()
    data["serial"] = {"device": lidar()["device"]}
    with pytest.raises(ValueError, match="same serial device"):
        load_profile(write(tmp_path, data))
