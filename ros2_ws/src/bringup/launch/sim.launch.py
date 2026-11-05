"""Shared simulation stack; validate the selected scenario before processes start."""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, EmitEvent, IncludeLaunchDescription,
                            OpaqueFunction, RegisterEventHandler)
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node

from uamc_sim.scenario import resolve_scenario


def start_bringup(context):
    sim_share = get_package_share_directory('uamc_sim')
    scenario = LaunchConfiguration('scenario').perform(context)
    params_file = LaunchConfiguration('params_file').perform(context)
    selected = resolve_scenario(sim_share, scenario, params_file)
    config = os.path.join(get_package_share_directory('uamc_bringup'), 'config', 'ekf.yaml')
    sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(sim_share, 'launch', 'vehicle_sim.launch.py')),
        launch_arguments={
            'scenario': scenario, 'params_file': params_file,
            'rviz': LaunchConfiguration('rviz'), 'gui': LaunchConfiguration('gui'),
            'gz_extra_args': LaunchConfiguration('gz_extra_args'),
        }.items())
    common = {'use_sim_time': True}
    mode = LaunchConfiguration('mode')
    manual = IfCondition(PythonExpression(["'", mode, "' == 'manual'"]))
    # Per-node named ROS YAML entries only; fixed simulation values are applied
    # last, so a tuning file cannot silently change mode or transport.
    tuning = [selected.node_parameters] if selected.node_parameters else []
    gate = Node(package='uamc_control', executable='safety_gate',
                parameters=tuning + [common, {'mode': mode}], output='screen')
    nodes = [
        Node(package='joy', executable='joy_node', condition=manual, parameters=tuning + [common], output='screen'),
        Node(package='uamc_io', executable='manual_joy', condition=manual, parameters=tuning + [common], output='screen'),
        Node(package='uamc_io', executable='vehicle_io', parameters=tuning + [common, {'transport': 'fake'}], output='screen'),
        Node(package='uamc_perception', executable='lane_detector', parameters=tuning + [common, {'ground_z': -0.045}], output='screen'),
        Node(package='uamc_perception', executable='obstacle_detector', parameters=tuning + [common], output='screen'),
        Node(package='uamc_control', executable='lane_planner', parameters=tuning + [common], output='screen'),
        Node(package='uamc_control', executable='path_controller', parameters=tuning + [common], output='screen'),
        Node(package='robot_localization', executable='ekf_node', name='ekf_filter_node',
             parameters=[config] + tuning + [common], remappings=[('odometry/filtered', '/odometry/filtered')], output='screen'),
        gate,
        RegisterEventHandler(OnProcessExit(target_action=gate, on_exit=[EmitEvent(event=Shutdown(reason='Safety gate exited'))])),
    ]
    # The included launch acquires its lock before returning any process actions.
    return [sim] + nodes


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('scenario', default_value='practice'),
        DeclareLaunchArgument('params_file', default_value=''),
        DeclareLaunchArgument('mode', default_value='auto'),
        DeclareLaunchArgument('rviz', default_value='false'),
        DeclareLaunchArgument('gui', default_value='false'),
        DeclareLaunchArgument('gz_extra_args', default_value=''),
        OpaqueFunction(function=start_bringup),
    ])
