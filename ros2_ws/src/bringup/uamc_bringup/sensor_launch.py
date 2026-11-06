"""Explicit sensor processes; no arbitrary package or executable in profiles."""
from pathlib import Path
from ament_index_python.packages import get_package_prefix, PackageNotFoundError
from launch_ros.actions import Node


def sensor_nodes(profile):
    nodes = []
    if profile.get("sources", {}).get("camera") == "opencv":
        nodes.append(Node(package="uamc_io", executable="camera", name="real_camera",
                          parameters=[{"use_sim_time": False}, profile["camera"]], output="screen"))
    if profile.get("sources", {}).get("lidar") == "sllidar_c1":
        try:
            prefix = get_package_prefix("sllidar_ros2")
        except PackageNotFoundError as exc:
            raise ValueError("sllidar_c1 requires the pinned sllidar_ros2 build; see docs/guides/real-car.md") from exc
        if not (Path(prefix) / "lib/sllidar_ros2/sllidar_node").is_file():
            raise ValueError("sllidar_ros2 is indexed but its sllidar_node executable is missing")
        values = profile["lidar"]
        params = {"use_sim_time": False, "channel_type": "serial", "serial_port": values["device"],
                  "serial_baudrate": values["baud"], "frame_id": values["frame_id"],
                  "inverted": values["inverted"], "angle_compensate": values["angle_compensate"],
                  "scan_mode": values["scan_mode"]}
        nodes.append(Node(package="sllidar_ros2", executable="sllidar_node", name="real_lidar", namespace="/sensors/lidar",
                          parameters=[params], remappings=[("scan", "/scan")], output="screen"))
    return nodes
