"""LiDAR + sürüş düğümü + base_link->laser TF.
  ros2 launch ros/launch/bringup.launch.py            (gerçek robot)
  ros2 launch ros/launch/bringup.launch.py mock:=true (donanımsız deneme, LiDAR yok)"""
import math
import pathlib

import yaml
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.conditions import IfCondition, UnlessCondition
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
    x, y = robot.get("lidar_x_m") or 0.0, robot.get("lidar_y_m") or 0.0
    yaw = math.radians(robot.get("lidar_yaw_deg") or 0.0)
    mock = LaunchConfiguration("mock")
    return LaunchDescription([
        DeclareLaunchArgument("mock", default_value="false"),
        # sllidar_ros2 launch dosyasının adına bağlı kalmamak için sürücü düğümü doğrudan başlatılır.
        Node(package="sllidar_ros2", executable="sllidar_node", name="sllidar_node", output="screen",
             parameters=[{"channel_type": "serial",
                          "serial_port": pins["lidar"]["port"],
                          "serial_baudrate": int(pins["lidar"]["baud"]),
                          "frame_id": "laser",
                          "inverted": False,
                          "angle_compensate": True}],
             condition=UnlessCondition(mock)),
        Node(package="tf2_ros", executable="static_transform_publisher", name="base_to_laser",
             arguments=["--x", str(x), "--y", str(y), "--z", "0.10", "--yaw", str(yaw),
                        "--frame-id", "base_link", "--child-frame-id", "laser"]),
        ExecuteProcess(cmd=["python3", str(SOFTWARE / "ros" / "drive_node.py")], output="screen",
                       condition=UnlessCondition(mock)),
        ExecuteProcess(cmd=["python3", str(SOFTWARE / "ros" / "drive_node.py"), "--mock"], output="screen",
                       condition=IfCondition(mock)),
    ])
