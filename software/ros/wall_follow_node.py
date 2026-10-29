#!/usr/bin/env python3
"""ROS 2 duvar takibi düğümü: /scan (LaserScan) -> /cmd_vel. Taramalar 0,5 sn'den eskiyse (LiDAR koptu)
sıfır hız yayınlar. Başlamadan önce geri sayım yapar.
Çalıştır: python3 ros/wall_follow_node.py --side right --v-scale 0.5"""
import argparse
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import rclpy  # noqa: E402
from geometry_msgs.msg import Twist  # noqa: E402
from rclpy.node import Node  # noqa: E402
from rclpy.qos import qos_profile_sensor_data  # noqa: E402
from sensor_msgs.msg import LaserScan  # noqa: E402

from arac.config import load_config  # noqa: E402
from arac.scan import ScanView  # noqa: E402
from arac.wall_follow import WallFollower  # noqa: E402

RATE_HZ = 20.0
SCAN_STALE_S = 0.5


class WallFollowNode(Node):
    def __init__(self, side, v_scale, stride, countdown):
        super().__init__("arac_wall_follow")
        cfg = load_config()
        p = dict(cfg["nav"]["wall_follow"])
        p["side"] = side or p["side"]
        for k in ("v_max", "v_min", "v_arc", "v_search"):   # ilk denemeler için hız ölçekle
            p[k] *= v_scale
        self.robot_cfg, self.stride = cfg["robot"], max(1, stride)
        self.follower = WallFollower(p, cfg["robot"]["robot_radius_m"])
        self.scan = None
        self.scan_t = 0.0
        self.start_t = time.monotonic() + countdown
        self._last_print = 0.0
        self.sub = self.create_subscription(LaserScan, "scan", self.on_scan, qos_profile_sensor_data)
        self.pub = self.create_publisher(Twist, "cmd_vel", 10)
        self.last = time.monotonic()
        self.timer = self.create_timer(1.0 / RATE_HZ, self.tick)
        self.get_logger().info(f"Duvar takibi ({p['side']}, hız ölçeği {v_scale}) {countdown:.0f} sn sonra başlıyor. "
                               "Durdurmak için Ctrl+C (araç durur).")

    def on_scan(self, msg):
        s = self.stride
        msg.ranges = list(msg.ranges)[::s]
        msg.angle_increment *= s
        self.scan, self.scan_t = msg, time.monotonic()

    def say(self, text):
        if time.monotonic() - self._last_print > 1.0:
            self._last_print = time.monotonic()
            self.get_logger().info(text)

    def tick(self):
        now = time.monotonic()
        dt, self.last = now - self.last, now
        cmd = Twist()
        if now < self.start_t:
            self.say(f"Başlamaya {self.start_t - now:.0f} sn...")
        elif self.scan is None or now - self.scan_t > SCAN_STALE_S:
            self.say("UYARI: /scan gelmiyor veya eski: araç duruyor (LiDAR bağlı mı?)")
        else:
            view = ScanView.from_laserscan(self.scan, self.robot_cfg)
            v, w = self.follower.step(view, max(dt, 1e-3))
            cmd.linear.x, cmd.angular.z = v, w
            info = self.follower.info
            self.say(f"{self.follower.state:11s} v={v:.2f} w={w:+.2f}" +
                     (f" duvar={info['d'] * 100:.0f}cm" if info and self.follower.state == "FOLLOW" else ""))
        self.pub.publish(cmd)

    def stop(self):
        try:
            self.pub.publish(Twist())
        except Exception:
            pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--side", choices=["right", "left"], default=None)
    ap.add_argument("--v-scale", type=float, default=0.5, help="nav.yaml hızlarını ölçekler (ilk denemede 0.5)")
    ap.add_argument("--stride", type=int, default=2, help="her N. LiDAR noktasını kullan (CPU tasarrufu)")
    ap.add_argument("--countdown", type=float, default=3.0)
    a, _ = ap.parse_known_args()
    rclpy.init()
    node = WallFollowNode(a.side, a.v_scale, a.stride, a.countdown)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.stop()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
