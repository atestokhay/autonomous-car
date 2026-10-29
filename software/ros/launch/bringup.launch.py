"""LiDAR + sürüş düğümü + base_link->laser TF.
  ros2 launch ros/launch/bringup.launch.py            (gerçek robot)
  ros2 launch ros/launch/bringup.launch.py mock:=true (donanımsız deneme, LiDAR yok)"""
import math
import pathlib

import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

SOFTWARE = pathlib.Path(__file__).resolve().parents[2]


def _cfg():
    pins = yaml.safe_load(open(SOFTWARE / "config" / "pins.yaml", encoding="utf-8"))
    robot = yaml.safe_load(open(SOFTWARE / "config" / "robot.yaml", encoding="utf-8"))
    cal = SOFTWARE / "config" / "robot_cal.yaml"
    if cal.exists():
        robot.update(yaml.safe_load(open(cal, encoding="utf-8")) or {})
    return pins, robot


def generate_launch_description():
    pins, robot = _cfg()
    lidar_launch = pathlib.Path(get_package_share_directory("sllidar_ros2")) / "launch" / "sllidar_s3_launch.py"
    x, y = robot.get("lidar_x_m") or 0.0, robot.get("lidar_y_m") or 0.0
    yaw = math.radians(robot.get("lidar_yaw_deg") or 0.0)
    mock = LaunchConfiguration("mock")
    return LaunchDescription([
        DeclareLaunchArgument("mock", default_value="false"),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(str(lidar_launch)),
            launch_arguments={"serial_port": pins["lidar"]["port"],
                              "serial_baudrate": str(pins["lidar"]["baud"]),
                              "frame_id": "laser"}.items(),
            condition=UnlessCondition(mock)),
        Node(package="tf2_ros", executable="static_transform_publisher", name="base_to_laser",
             arguments=["--x", str(x), "--y", str(y), "--z", "0.10", "--yaw", str(yaw),
                        "--frame-id", "base_link", "--child-frame-id", "laser"]),
        ExecuteProcess(cmd=["python3", str(SOFTWARE / "ros" / "drive_node.py")], output="screen",
                       condition=UnlessCondition(mock)),
        ExecuteProcess(cmd=["python3", str(SOFTWARE / "ros" / "drive_node.py"), "--mock"], output="screen",
                       condition=IfCondition(mock)),
    ])
