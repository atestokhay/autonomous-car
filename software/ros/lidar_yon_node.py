#!/usr/bin/env python3
"""LiDAR'ın araca göre yönünü kendisi bulur: tarama al → kısa süre İLERİ git → tarama al → karşılaştır.
Sonucu config/robot_cal.yaml → lidar_yaw_deg'e yazar. bringup.launch.py çalışıyor olmalı.
Çıkış kodu: 0 = bulundu, 3 = araç düz gitmedi (bir motor ters), 1 = hata."""
import argparse
import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import rclpy  # noqa: E402
import yaml  # noqa: E402
from geometry_msgs.msg import Twist  # noqa: E402
from rclpy.node import Node  # noqa: E402
from rclpy.qos import qos_profile_sensor_data  # noqa: E402
from sensor_msgs.msg import LaserScan  # noqa: E402

from arac.config import CONFIG_DIR, load_config  # noqa: E402
from arac.lidar_yon import find_front  # noqa: E402


class YonNode(Node):
    def __init__(self):
        super().__init__("arac_lidar_yon")
        self.scan = None
        self.create_subscription(LaserScan, "scan", self.on_scan, qos_profile_sensor_data)
        self.pub = self.create_publisher(Twist, "cmd_vel", 10)

    def on_scan(self, m):
        self.scan = (list(m.ranges), m.angle_min, m.angle_increment)

    def spin_for(self, sec, v=0.0):
        end = time.monotonic() + sec
        while time.monotonic() < end:
            t = Twist()
            t.linear.x = v
            self.pub.publish(t)
            rclpy.spin_once(self, timeout_sec=0.05)

    def fresh_scan(self, timeout=8.0):
        self.scan = None
        end = time.monotonic() + timeout
        while self.scan is None and time.monotonic() < end:
            self.spin_for(0.1)
        if self.scan is None:
            raise RuntimeError("/scan gelmiyor (LiDAR çalışmıyor).")
        self.spin_for(0.3)   # bir tam tur daha bekle, son taramayı al
        return self.scan


def save_cal(key, value):
    p = CONFIG_DIR / "robot_cal.yaml"
    d = (yaml.safe_load(p.read_text(encoding="utf-8")) if p.exists() else None) or {}
    d[key] = value
    p.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sure", type=float, default=1.5, help="ileri gitme süresi (sn)")
    a = ap.parse_args()
    v = load_config()["nav"]["wall_follow"]["v_max"]
    rclpy.init()
    node = YonNode()
    code = 1
    try:
        node.spin_for(2.0)                       # sürüş düğümü ve LiDAR otursun
        before = node.fresh_scan()
        node.spin_for(a.sure, v)                 # İLERİ
        node.spin_for(1.0)                       # dur, otur
        after = node.fresh_scan()
        r = find_front(before, after)
        print("LiDAR yön ölçümü:", json.dumps(r))
        if abs(r["rot_deg"]) > 12:
            print(f"Araç düz gitmek yerine {r['rot_deg']}° döndü: bir motor ters dönüyor.")
            code = 3
        elif r["move_m"] < 0.03:
            print(f"Araç ilerlemedi (ölçülen {r['move_m'] * 100:.1f} cm): motorlar/teker zemini kontrol et.")
            code = 1
        else:
            save_cal("lidar_yaw_deg", r["yaw_deg"])
            print(f"lidar_yaw_deg = {r['yaw_deg']} → config/robot_cal.yaml")
            code = 0
    except RuntimeError as e:
        print("HATA:", e)
    finally:
        node.spin_for(0.3)
        node.destroy_node()
        rclpy.shutdown()
    sys.exit(code)


if __name__ == "__main__":
    main()
