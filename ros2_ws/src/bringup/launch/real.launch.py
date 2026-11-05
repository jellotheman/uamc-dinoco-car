"""Fail-closed bench profile; unverified hardware drivers are deliberately absent."""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node


def generate_launch_description():
    mode = LaunchConfiguration('mode')
    manual = IfCondition(PythonExpression(["'", mode, "' == 'manual'"]))
    config = os.path.join(get_package_share_directory('uamc_bringup'), 'config', 'ekf.yaml')
    return LaunchDescription([
        DeclareLaunchArgument('mode', default_value='auto', description='auto or manual; choose before starting'),
        Node(package='uamc_io', executable='vehicle_io', parameters=[{'transport': 'disabled'}], output='screen'),
        Node(package='uamc_control', executable='safety_gate', parameters=[{'mode': mode}], output='screen'),
        Node(package='uamc_perception', executable='lane_detector', output='screen'),
        Node(package='uamc_perception', executable='obstacle_detector', output='screen'),
        Node(package='uamc_control', executable='lane_planner', output='screen'),
        Node(package='uamc_control', executable='path_controller', output='screen'),
        Node(package='robot_localization', executable='ekf_node', name='ekf_filter_node', parameters=[config], remappings=[('odometry/filtered', '/odometry/filtered')], output='screen'),
        Node(package='joy', executable='joy_node', condition=manual, output='screen'),
        Node(package='uamc_io', executable='manual_joy', condition=manual, output='screen'),
    ])
