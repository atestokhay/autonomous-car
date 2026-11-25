"""Bringup + duvar takibi.   ros2 launch ros/launch/wall_follow.launch.py side:=right v_scale:=0.5
countdown:=3 (varsayılan): düğüm hareketten önce 3 sn bekler. Başlat butonu (tools/baslat_butonu.py) kendi
5 sn geri sayımını yaptığı için countdown:=0 verir."""
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
        DeclareLaunchArgument("countdown", default_value="3.0"),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(str(HERE / "bringup.launch.py"))),
        ExecuteProcess(
            cmd=["python3", str(SOFTWARE / "ros" / "wall_follow_node.py"),
                 "--side", LaunchConfiguration("side"), "--v-scale", LaunchConfiguration("v_scale"),
                 "--countdown", LaunchConfiguration("countdown")],
            output="screen"),
    ])
