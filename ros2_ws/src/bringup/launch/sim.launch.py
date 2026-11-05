import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, RegisterEventHandler, EmitEvent
from launch.event_handlers import OnProcessExit
from launch.conditions import IfCondition
from launch.substitutions import PythonExpression
from launch.events import Shutdown
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    config = os.path.join(get_package_share_directory('uamc_bringup'), 'config', 'ekf.yaml')
    sim = IncludeLaunchDescription(PythonLaunchDescriptionSource(os.path.join(
        get_package_share_directory('uamc_sim'), 'launch', 'vehicle_sim.launch.py')),
        launch_arguments={'rviz': LaunchConfiguration('rviz'), 'gui': LaunchConfiguration('gui'), 'gz_extra_args': LaunchConfiguration('gz_extra_args')}.items())
    common = {'use_sim_time': True}
    mode = LaunchConfiguration('mode')
    manual = IfCondition(PythonExpression(["'", mode, "' == 'manual'"]))
    gate = Node(package='uamc_control', executable='safety_gate', parameters=[common, {'mode': mode}], output='screen')
    nodes = [
        Node(package='joy', executable='joy_node', condition=manual, parameters=[common], output='screen'),
        Node(package='uamc_io', executable='manual_joy', condition=manual, parameters=[common], output='screen'),
        Node(package='uamc_io', executable='vehicle_io', parameters=[common, {'transport': 'fake'}], output='screen'),
        Node(package='uamc_perception', executable='lane_detector', parameters=[common, {'ground_z': -0.045}], output='screen'),
        Node(package='uamc_perception', executable='obstacle_detector', parameters=[common], output='screen'),
        Node(package='uamc_control', executable='lane_planner', parameters=[common], output='screen'),
        Node(package='uamc_control', executable='path_controller', parameters=[common], output='screen'),
        Node(package='robot_localization', executable='ekf_node', name='ekf_filter_node', parameters=[config, common], remappings=[('odometry/filtered', '/odometry/filtered')], output='screen'),
        gate,
        RegisterEventHandler(OnProcessExit(target_action=gate, on_exit=[EmitEvent(event=Shutdown(reason='Safety gate exited'))])),
    ]
    return LaunchDescription([DeclareLaunchArgument('mode', default_value='auto'), DeclareLaunchArgument('rviz', default_value='false'), DeclareLaunchArgument('gui', default_value='false'),
                              DeclareLaunchArgument('gz_extra_args', default_value=''), sim] + nodes)
