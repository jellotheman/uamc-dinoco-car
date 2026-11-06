"""Real-time, fail-closed stack; no Gazebo or inferred hardware drivers."""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, EmitEvent, OpaqueFunction, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from uamc_bringup.real_config import load_profile, validate_tuning, validate_description
from uamc_bringup.real_session import acquire_session_locks
from uamc_bringup.real_view import rviz_action


def start(context):
    arg = lambda name: LaunchConfiguration(name).perform(context)
    mode, actuation, debug = arg("mode"), arg("actuation"), arg("visualization_debug").lower()
    if mode not in ("auto", "manual"):
        raise ValueError("mode must be auto or manual")
    if debug not in ("auto", "true", "false"):
        raise ValueError("visualization_debug must be auto, true or false")
    if arg("rviz").lower() not in ("true", "false"):
        raise ValueError("rviz must be true or false")
    if arg("rviz_frame") not in ("odom", "base_link"):
        raise ValueError("rviz_frame must be odom or base_link")
    profile = load_profile(arg("hardware_config"), actuation)
    tuning = validate_tuning(arg("params_file"))
    rviz = rviz_action(arg("rviz_frame")) if arg("rviz").lower() == "true" else None
    common = {"use_sim_time": False}
    serial = profile.get("serial", {})
    io_params = {"transport": "real" if actuation == "serial" else "disabled"}
    if actuation == "serial":
        io_params.update({("serial_device" if k == "device" else "serial_baud" if k == "baud" else k): v for k, v in serial.items()})
    io = Node(package="uamc_io", executable="vehicle_io", parameters=tuning + [common, io_params], output="screen")
    gate_params = {"mode": mode}
    if actuation == "serial":
        gate_params.update({"max_speed": serial["max_speed"], "max_steering": serial["max_steer"], "max_reverse": 0.0})
    gate = Node(package="uamc_control", executable="safety_gate", parameters=tuning + [common, gate_params], output="screen")
    debug_params = [] if debug == "auto" else [{"debug_enabled": debug == "true"}]
    ground = [{"ground_z": profile["model"]["ground_z"]}] if "model" in profile else []
    ekf = os.path.join(get_package_share_directory("uamc_bringup"), "config", "ekf.yaml")
    nodes = [io, gate,
        Node(package="uamc_control", executable="lane_planner", parameters=tuning + [common], output="screen"),
        Node(package="robot_localization", executable="ekf_node", name="ekf_filter_node", parameters=[ekf] + tuning + [common], remappings=[("odometry/filtered", "/odometry/filtered")], output="screen")]
    if ground:
        model = profile["model"]
        geometry = {key: model[key] for key in ("wheelbase", "front", "rear", "half_width")}
        controller = {"wheelbase": model["wheelbase"]}
        if actuation == "serial":
            controller.update({"speed": serial["max_speed"], "max_steering": serial["max_steer"]})
        nodes.extend([Node(package="uamc_perception", executable="lane_detector", parameters=tuning + [common] + debug_params + ground, output="screen"),
                      Node(package="uamc_perception", executable="obstacle_detector", parameters=tuning + [common] + debug_params + [geometry], output="screen"),
                      Node(package="uamc_control", executable="path_controller", parameters=tuning + [common, controller], output="screen")])
    if mode == "manual":
        nodes += [Node(package="joy", executable="joy_node", parameters=[common], output="screen"), Node(package="uamc_io", executable="manual_joy", parameters=tuning + [common, ({"max_speed": serial["max_speed"], "max_steer": serial["max_steer"], "allow_reverse": False} if actuation == "serial" else {})], output="screen")]
    if "model" in profile:
        with open(profile["model"]["description_file"], encoding="utf-8") as stream:
            description = stream.read()
        validate_description(description)
        nodes.append(Node(package="robot_state_publisher", executable="robot_state_publisher", parameters=[common, {"robot_description": description}], output="screen"))
    critical = list(nodes)
    if rviz:
        nodes.append(rviz)
        critical.append(rviz)
    handlers = [RegisterEventHandler(OnProcessExit(target_action=node, on_exit=[EmitEvent(event=Shutdown(reason="Critical real stack process exited"))])) for node in critical]
    acquire_session_locks()
    return handlers + nodes


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument("hardware_config", default_value="", description="Private measured hardware profile; empty selects external observation"),
        DeclareLaunchArgument("actuation", default_value="disabled", description="disabled or explicitly commissioned serial output"),
        DeclareLaunchArgument("mode", default_value="auto", description="auto or manual; selected before startup"),
        DeclareLaunchArgument("rviz", default_value="false", description="Open local RViz; requires a graphical session"),
        DeclareLaunchArgument("visualization_debug", default_value="auto", description="auto preserves detector tuning; true/false overrides diagnostic generation"),
        DeclareLaunchArgument("params_file", default_value="", description="Optional named-node tuning; protected hardware parameters cannot be overridden"),
        DeclareLaunchArgument("rviz_frame", default_value="odom", description="odom or explicit base_link observation without localization"),
        OpaqueFunction(function=start),
    ])
