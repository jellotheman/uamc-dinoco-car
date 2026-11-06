"""Strict, non-ROS hardware profile validation; no devices are opened here."""
import math
from pathlib import Path
import yaml


def _mapping(value, required, optional=(), where="profile"):
    if not isinstance(value, dict) or set(value) - set(required) - set(optional) or set(required) - set(value):
        raise ValueError(f"{where}: expected keys {sorted(required)}, optional {sorted(optional)}")
    return value


def _text(value, where):
    if not isinstance(value, str) or not value.strip() or value.strip().lower() in ("replace me", "placeholder", "todo"):
        raise ValueError(f"{where}: a recorded value is required")
    return value


def _number(value, where, low=0, inclusive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or (value < low if inclusive else value <= low):
        raise ValueError(f"{where}: invalid finite bound")
    return float(value)


def _file(base, value, where):
    path = Path(_text(value, where)).expanduser()
    path = (base / path).resolve() if not path.is_absolute() else path.resolve()
    if not path.is_file():
        raise ValueError(f"{where}: file not found: {path}")
    return str(path)


def load_profile(path, actuation="disabled"):
    if actuation not in ("disabled", "serial"):
        raise ValueError("actuation must be disabled or serial")
    if not path:
        if actuation == "serial":
            raise ValueError("serial actuation requires hardware_config")
        return {}
    path = Path(path).expanduser().resolve()
    try:
        with path.open(encoding="utf-8") as stream:
            data = yaml.safe_load(stream)
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"invalid hardware profile: {exc}") from exc
    _mapping(data, ("schema_version", "identification", "sources"), ("model", "serial"))
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise ValueError("unsupported hardware profile schema_version")
    ident = _mapping(data["identification"], ("hardware", "firmware", "measurement_record"), where="identification")
    for key, value in ident.items():
        _text(value, key)
    sources = _mapping(data["sources"], ("camera", "lidar", "imu", "wheel", "health"), where="sources")
    if any(value != "external" for value in sources.values()):
        raise ValueError("only external actual sensor sources are supported")
    if actuation == "serial" and "model" not in data:
        raise ValueError("serial actuation requires a measured model and ground height")
    if "model" in data:
        model = _mapping(data["model"], ("description_file", "ground_z", "wheelbase", "front", "rear", "half_width"), where="model")
        model["description_file"] = _file(path.parent, model["description_file"], "description_file")
        with open(model["description_file"], encoding="utf-8") as stream:
            validate_description(stream.read())
        if isinstance(model["ground_z"], bool) or not isinstance(model["ground_z"], (int, float)) or not math.isfinite(model["ground_z"]):
            raise ValueError("ground_z must be finite")
        model["ground_z"] = float(model["ground_z"])
        for key in ("wheelbase", "front", "rear", "half_width"):
            model[key] = _number(model[key], key)
    if "serial" in data:
        fields = ("device", "baud", "calibration_file", "handshake_timeout", "write_timeout", "command_timeout", "health_timeout", "max_source_age", "future_tolerance", "max_speed", "max_steer")
        serial = _mapping(data["serial"], fields, where="serial")
        device = _text(serial["device"], "serial.device")
        if not device.startswith("/dev/serial/by-"):
            raise ValueError("serial.device must use an explicit stable /dev/serial/by-* path")
        if type(serial["baud"]) is not int or serial["baud"] != 115200:
            raise ValueError("serial.baud must be 115200")
        serial["calibration_file"] = _file(path.parent, serial["calibration_file"], "calibration_file")
        for key in fields[3:]:
            serial[key] = _number(serial[key], key, inclusive=(key == "future_tolerance"))
        for key, maximum in {"handshake_timeout": 30.0, "write_timeout": 0.5, "command_timeout": 5.0, "health_timeout": 5.0, "max_source_age": 5.0, "future_tolerance": 1.0}.items():
            if serial[key] > maximum:
                raise ValueError(f"{key} exceeds bounded maximum {maximum}")
        from uamc_io.calibration import load_calibration, validate_caps
        validate_caps(load_calibration(serial["calibration_file"]), serial["max_speed"], serial["max_steer"])
    elif actuation == "serial":
        raise ValueError("serial actuation requires a complete serial profile")
    return data


def validate_tuning(path):
    if not path:
        return []
    try:
        with open(path, encoding="utf-8") as stream:
            data = yaml.safe_load(stream)
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"invalid tuning: {exc}") from exc
    if not isinstance(data, dict) or not data:
        raise ValueError("tuning must be a nonempty named-node mapping")
    protected = {"use_sim_time", "transport", "mode", "serial_device", "serial_baud", "calibration_file", "handshake_timeout", "write_timeout", "command_timeout", "health_timeout", "max_source_age", "future_tolerance", "max_speed", "max_steer", "ground_z", "robot_description", "map_frame", "odom_frame", "base_link_frame", "world_frame", "odom0", "imu0", "publish_tf", "max_steering", "max_reverse", "speed", "wheelbase", "front", "rear", "half_width", "base_frame", "allow_reverse"}
    for node, entry in data.items():
        if not isinstance(node, str) or not node or "*" in node or not isinstance(entry, dict) or set(entry) != {"ros__parameters"} or not isinstance(entry["ros__parameters"], dict):
            raise ValueError("tuning requires exact named-node ros__parameters entries")
        if protected.intersection(entry["ros__parameters"]):
            raise ValueError(f"protected tuning parameter in {node}")
    from rclpy.utilities import remove_ros_args
    remove_ros_args(["validation", "--ros-args", "--params-file", str(path)])
    return [str(path)]


def validate_description(description):
    import xml.etree.ElementTree as ET
    import subprocess
    import tempfile
    try:
        root = ET.fromstring(description)
    except ET.ParseError as exc:
        raise ValueError(f"invalid URDF: {exc}") from exc
    if root.tag != "robot" or any(element.tag.lower().endswith("gazebo") for element in root.iter()):
        raise ValueError("description must be a Gazebo-free expanded URDF")
    if any(element.tag.lower().endswith(("plugin", "ros2_control")) for element in root.iter()):
        raise ValueError("hardware URDF cannot contain plugins or ros2_control")
    links = {link.get("name") for link in root.findall("link")}
    if "base_link" not in links or "odom" in links:
        raise ValueError("URDF must contain base_link and must not own odom")
    joints = root.findall("joint")
    if any(joint.get("type") != "fixed" for joint in joints):
        raise ValueError("hardware model supports fixed measured joints only")
    if any(child.get("link") == "base_link" for joint in joints for child in joint.findall("child")):
        raise ValueError("base_link must be the URDF root")
    for origin in root.iter("origin"):
        for attribute in ("xyz", "rpy"):
            if attribute in origin.attrib:
                try:
                    values = [float(value) for value in origin.attrib[attribute].split()]
                except ValueError as exc:
                    raise ValueError("invalid URDF origin") from exc
                if len(values) != 3 or not all(math.isfinite(value) for value in values):
                    raise ValueError("URDF origins require three finite measured values")
    for box in root.iter("box"):
        try:
            size = [float(value) for value in box.attrib.get("size", "").split()]
        except ValueError as exc:
            raise ValueError("invalid URDF box size") from exc
        if len(size) != 3 or not all(math.isfinite(value) and value > 0 for value in size):
            raise ValueError("URDF box requires three positive finite dimensions")
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".urdf", encoding="utf-8") as handle:
            handle.write(description)
            handle.flush()
            result = subprocess.run(["check_urdf", handle.name], capture_output=True, text=True, timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError(f"URDF validation unavailable: {exc}") from exc
    if result.returncode != 0 or "root Link: base_link" not in result.stdout:
        raise ValueError(f"invalid URDF tree: {result.stderr.strip()}")
    return description
