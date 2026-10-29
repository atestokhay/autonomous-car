"""Bringup + duvar takibi.   ros2 launch ros/launch/wall_follow.launch.py side:=right v_scale:=0.5"""
import pathlib

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration

HERE = pathlib.Path(__file__).resolve().parent
SOFTWARE = HERE.parents[1]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument("side", default_value="right"),
        DeclareLaunchArgument("v_scale", default_value="0.5"),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(str(HERE / "bringup.launch.py"))),
        ExecuteProcess(
            cmd=["python3", str(SOFTWARE / "ros" / "wall_follow_node.py"),
                 "--side", LaunchConfiguration("side"), "--v-scale", LaunchConfiguration("v_scale")],
            output="screen"),
    ])
