"""Bringup + slam_toolbox (haritalama).   ros2 launch ros/launch/slam.launch.py
Harita kaydı: ros2 run nav2_map_server map_saver_cli -f ~/harita   (ros-jazzy-nav2-map-server gerekir)"""
import pathlib

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource

HERE = pathlib.Path(__file__).resolve().parent
SOFTWARE = HERE.parents[1]


def generate_launch_description():
    slam = pathlib.Path(get_package_share_directory("slam_toolbox")) / "launch" / "online_async_launch.py"
    return LaunchDescription([
        IncludeLaunchDescription(PythonLaunchDescriptionSource(str(HERE / "bringup.launch.py"))),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(str(slam)),
            launch_arguments={"slam_params_file": str(SOFTWARE / "config" / "slam_toolbox.yaml"),
                              "use_sim_time": "false"}.items()),
    ])
