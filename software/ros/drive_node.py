#!/usr/bin/env python3
"""ROS 2 sürüş düğümü: /cmd_vel (geometry_msgs/Twist) -> iki tekerlek PID -> /odom + TF (odom->base_link).
Odometride mesafe enkoderden, dönüş açısı BNO055 gyro'dan (pins.yaml imu.use_for_heading; IMU yoksa ya da
okunamazsa otomatik olarak enkoderden). KOMUT 0,5 sn gelmezse araç durur. Hata/Ctrl+C'de motorlar durdurulur.
Çalıştır: source /opt/ros/jazzy/setup.bash && python3 ros/drive_node.py [--mock]"""
import argparse
import math
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import rclpy  # noqa: E402
from geometry_msgs.msg import Twist, TransformStamped  # noqa: E402
from nav_msgs.msg import Odometry  # noqa: E402
from rclpy.node import Node  # noqa: E402
from tf2_ros import TransformBroadcaster  # noqa: E402

from arac.config import load_config  # noqa: E402
from arac.factory import build_drive, close_hardware  # noqa: E402
from arac.imu import open_imu  # noqa: E402
from arac.loop import try_realtime  # noqa: E402


class DriveNode(Node):
    def __init__(self, mock):
        super().__init__("arac_drive")
        cfg = load_config()
        self.hz = cfg["pid"]["loop_hz"]
        self.gpio, self.parts, self.drive = build_drive(cfg, mock)
        self.imu, imu_msg = (None, "deneme modu: IMU yok, açı enkoderden") if mock else open_imu(cfg)
        self.imu_errors = 0
        (self.get_logger().info if self.imu else self.get_logger().warning)(imu_msg)
        self.sub = self.create_subscription(Twist, "cmd_vel", self.on_cmd, 10)
        self.pub = self.create_publisher(Odometry, "odom", 10)
        self.tf = TransformBroadcaster(self)
        self.mock = mock
        self.last = time.monotonic()
        self.n = 0
        self.timer = self.create_timer(1.0 / self.hz, self.tick)
        self.get_logger().info(f"Sürüş düğümü hazır ({self.hz} Hz, mock={mock}). Gerçek zamanlı: {try_realtime()}")

    def on_cmd(self, msg):
        self.drive.set_cmd(msg.linear.x, msg.angular.z, time.monotonic())

    def tick(self):
        now = time.monotonic()
        dt, self.last = now - self.last, now
        if dt <= 0.0:
            return
        heading = self.read_heading()
        try:
            x, y, th, v, w = self.drive.update(dt, now, heading)
        except RuntimeError as e:
            self.get_logger().error(f"DURDU: {e}")
            self.shutdown()
            raise SystemExit(1)
        if self.mock:
            for p in self.parts.values():
                p["plant"].step(dt)
        self.n += 1
        if self.n % 2:                       # odometriyi hz/2 hızında yayınla
            return
        stamp = self.get_clock().now().to_msg()
        qz, qw = math.sin(th / 2.0), math.cos(th / 2.0)
        o = Odometry()
        o.header.stamp, o.header.frame_id, o.child_frame_id = stamp, "odom", "base_link"
        o.pose.pose.position.x, o.pose.pose.position.y = x, y
        o.pose.pose.orientation.z, o.pose.pose.orientation.w = qz, qw
        o.twist.twist.linear.x, o.twist.twist.angular.z = v, w
        o.pose.covariance[0] = o.pose.covariance[7] = 0.01
        o.pose.covariance[35] = 0.05
        o.twist.covariance[0] = o.twist.covariance[35] = 0.01
        self.pub.publish(o)
        t = TransformStamped()
        t.header.stamp, t.header.frame_id, t.child_frame_id = stamp, "odom", "base_link"
        t.transform.translation.x, t.transform.translation.y = x, y
        t.transform.rotation.z, t.transform.rotation.w = qz, qw
        self.tf.sendTransform(t)

    def read_heading(self):
        """IMU açısı ya da None. Arka arkaya 20 okuma hatasında IMU bırakılır, açı enkoderden devam eder."""
        if self.imu is None:
            return None
        try:
            h = self.imu.yaw()
            self.imu_errors = 0
            return h
        except Exception as e:  # noqa: BLE001  (I2C hatası motor kontrolünü DURDURMAMALI)
            self.imu_errors += 1
            if self.imu_errors >= 20:
                self.get_logger().error(f"BNO055 okunamıyor ({e}): açı artık ENKODERDEN hesaplanıyor")
                self.close_imu()
            return None

    def close_imu(self):
        if self.imu is not None:
            try:
                self.imu.close()
            except Exception:  # noqa: BLE001
                pass
            self.imu = None

    def shutdown(self):
        try:
            self.drive.stop()
        finally:
            close_hardware(self.gpio, self.parts)
            self.close_imu()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", action="store_true", help="donanımsız (simüle motor)")
    a, _ = ap.parse_known_args()
    rclpy.init()
    node = DriveNode(a.mock)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
