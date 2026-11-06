"""Build an isolated RViz configuration without changing the installed asset."""
import os
import tempfile
import yaml
from ament_index_python.packages import get_package_share_directory


def rviz_action(frame):
    if frame not in ("odom", "base_link"):
        raise ValueError("rviz_frame must be odom or base_link")
    if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        raise ValueError("RViz requires a graphical display; use rviz:=false and launch real_view on a workstation")
    from launch_ros.actions import Node
    path = os.path.join(get_package_share_directory("uamc_dashboard"), "config", "real.rviz")
    with open(path, encoding="utf-8") as stream:
        config = yaml.safe_load(stream)
    config["Visualization Manager"]["Global Options"]["Fixed Frame"] = frame
    # RViz opens the file after launch returns. The launch process owns its lifetime.
    handle = tempfile.NamedTemporaryFile(mode="w", suffix=".rviz", delete=False, encoding="utf-8")
    try:
        yaml.safe_dump(config, handle, sort_keys=False)
    finally:
        handle.close()
    import atexit
    atexit.register(lambda: os.path.exists(handle.name) and os.unlink(handle.name))
    return Node(package="rviz2", executable="rviz2", arguments=["-d", handle.name], parameters=[{"use_sim_time": False}], output="screen")
