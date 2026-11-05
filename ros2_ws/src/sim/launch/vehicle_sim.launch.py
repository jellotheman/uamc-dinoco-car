"""Gazebo server, model, sensor bridges, and fail-closed drive adapter."""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, EmitEvent, IncludeLaunchDescription, RegisterEventHandler
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration, PythonExpression
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    sim = get_package_share_directory('uamc_sim')
    desc = get_package_share_directory('uamc_description')
    gui = LaunchConfiguration('gui')
    rviz = LaunchConfiguration('rviz')
    world = os.path.join(sim, 'worlds', 'practice.sdf')
    robot = ParameterValue(Command(['xacro ', os.path.join(desc, 'urdf', 'vehicle.urdf.xacro')]), value_type=str)
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py')),
        launch_arguments={'gz_args': [world, ' -r ', PythonExpression(["'' if '", gui, "' == 'true' else '-s'" ]), ' ', LaunchConfiguration('gz_extra_args')]}.items())
    state = Node(package='robot_state_publisher', executable='robot_state_publisher',
                 parameters=[{'robot_description': robot, 'use_sim_time': True}], output='screen')
    spawn = Node(package='ros_gz_sim', executable='create', arguments=['-name', 'uamc', '-topic', 'robot_description', '-z', '0.05'], output='screen')
    bridge = Node(package='ros_gz_bridge', executable='parameter_bridge',
                  parameters=[{'config_file': os.path.join(sim, 'config', 'bridge.yaml')}], output='screen')
    adapter = Node(package='uamc_sim', executable='ackermann_adapter', output='screen')
    rviz_node = Node(package='rviz2', executable='rviz2', arguments=['-d', os.path.join(sim, 'config', 'practice.rviz')],
                     parameters=[{'use_sim_time': True}], condition=IfCondition(rviz), output='screen')
    return LaunchDescription([
        DeclareLaunchArgument('gui', default_value='false'),
        DeclareLaunchArgument('rviz', default_value='false'),
        DeclareLaunchArgument('gz_extra_args', default_value=''),
        gazebo, state, spawn, bridge, adapter, rviz_node,
        RegisterEventHandler(OnProcessExit(target_action=bridge, on_exit=[EmitEvent(event=Shutdown(reason='Gazebo bridge exited'))])),
        RegisterEventHandler(OnProcessExit(target_action=adapter, on_exit=[EmitEvent(event=Shutdown(reason='Gazebo command adapter exited'))])),
    ])
