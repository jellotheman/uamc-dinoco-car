"""Remote viewer only; never starts or supervises a vehicle stack."""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from uamc_bringup.real_view import rviz_action


def start(context):
    return [rviz_action(LaunchConfiguration("rviz_frame").perform(context))]


def generate_launch_description():
    return LaunchDescription([DeclareLaunchArgument("rviz_frame", default_value="odom"), OpaqueFunction(function=start)])
