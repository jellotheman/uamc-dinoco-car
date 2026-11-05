"""Gazebo server, model, sensor bridges, and fail-closed drive adapter."""
import os

from ament_index_python.packages import get_package_prefix, get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, EmitEvent, ExecuteProcess, OpaqueFunction, RegisterEventHandler
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

from uamc_sim.session_lock import acquire_session_lock
from uamc_sim.scenario import resolve_scenario


def start_simulation(context):
    # Launch introspection does not run OpaqueFunction, while a duplicate run
    # fails before any Gazebo, bridge, RViz or adapter processes are started.
    sim = get_package_share_directory('uamc_sim')
    selected = resolve_scenario(sim, LaunchConfiguration('scenario').perform(context),
                                LaunchConfiguration('params_file').perform(context))
    acquire_session_lock()
    desc = get_package_share_directory('uamc_description')
    gui = LaunchConfiguration('gui').perform(context).lower() in ('true', '1', 'yes')
    world = selected.world
    extra_args = LaunchConfiguration('gz_extra_args').perform(context)
    robot = ParameterValue(Command(['xacro ', os.path.join(desc, 'urdf', 'vehicle.urdf.xacro')]), value_type=str)
    gazebo_args = ['--world', world, '--extra-args=' + extra_args, '--expected-parent', str(os.getpid())]
    if gui:
        gazebo_args.append('--gui')
    gazebo = ExecuteProcess(cmd=[os.path.join(get_package_prefix('uamc_sim'), 'lib', 'uamc_sim', 'gazebo_supervisor'), *gazebo_args], name='gazebo_supervisor', output='screen')
    state = Node(package='robot_state_publisher', executable='robot_state_publisher',
                 parameters=[{'robot_description': robot, 'use_sim_time': True}], output='screen')
    spawn = Node(package='ros_gz_sim', executable='create', arguments=['-world', selected.world_name, '-name', 'uamc', '-topic', 'robot_description',
                            '-x', str(selected.spawn[0]), '-y', str(selected.spawn[1]),
                            '-z', str(selected.spawn[2]), '-Y', str(selected.spawn[3])], output='screen')
    bridge = Node(package='ros_gz_bridge', executable='parameter_bridge',
                  parameters=[{'config_file': os.path.join(sim, 'config', 'bridge.yaml')}], output='screen')
    adapter = Node(package='uamc_sim', executable='ackermann_adapter', output='screen')
    rviz = Node(package='rviz2', executable='rviz2', arguments=['-d', selected.rviz_config],
                parameters=[{'use_sim_time': True}], condition=IfCondition(LaunchConfiguration('rviz')), output='screen')
    shutdown = lambda name: [EmitEvent(event=Shutdown(reason=name + ' exited'))]
    return [
        # Install handlers before starting processes so even an immediate exit is caught.
        RegisterEventHandler(OnProcessExit(target_action=gazebo, on_exit=shutdown('Gazebo'))),
        RegisterEventHandler(OnProcessExit(target_action=bridge, on_exit=shutdown('Gazebo bridge'))),
        RegisterEventHandler(OnProcessExit(target_action=adapter, on_exit=shutdown('Gazebo command adapter'))),
        RegisterEventHandler(OnProcessExit(target_action=rviz, on_exit=shutdown('RViz'))),
        gazebo, state, spawn, bridge, adapter, rviz,
    ]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('scenario', default_value='practice'),
        DeclareLaunchArgument('params_file', default_value=''),
        DeclareLaunchArgument('gui', default_value='false'),
        DeclareLaunchArgument('rviz', default_value='false'),
        DeclareLaunchArgument('gz_extra_args', default_value=''),
        OpaqueFunction(function=start_simulation),
    ])
