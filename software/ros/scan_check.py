#!/usr/bin/env python3
"""ROS 2 /scan sağlık kontrolü: 5 sn dinler, tarama hızını ve geçerli nokta oranını ve ön/yan mesafeleri yazar."""
import math
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import rclpy  # noqa: E402
from rclpy.node import Node  # noqa: E402
from rclpy.qos import qos_profile_sensor_data  # noqa: E402
from sensor_msgs.msg import LaserScan  # noqa: E402

from arac.config import load_config  # noqa: E402
from arac.scan import ScanView  # noqa: E402


class Check(Node):
    def __init__(self):
        super().__init__("arac_scan_check")
        self.robot = load_config()["robot"]
        self.msgs = []
        self.create_subscription(LaserScan, "scan", lambda m: self.msgs.append((time.monotonic(), m)),
                                 qos_profile_sensor_data)


def main():
    rclpy.init()
    node = Check()
    end = time.monotonic() + 5.0
    print("5 sn /scan dinleniyor...")
    while time.monotonic() < end:
        rclpy.spin_once(node, timeout_sec=0.1)
    if not node.msgs:
        print("HATA: /scan mesajı gelmedi. LiDAR launch'ı çalışıyor mu? (notes/sorun-giderme.md)")
        sys.exit(1)
    t0, t1 = node.msgs[0][0], node.msgs[-1][0]
    hz = (len(node.msgs) - 1) / (t1 - t0) if t1 > t0 else 0.0
    m = node.msgs[-1][1]
    view = ScanView.from_laserscan(m, node.robot)
    valid = len(view) / max(1, len(m.ranges)) * 100
    print(f"Tarama hızı: {hz:.1f} Hz (S3'te ~10 beklenir)  |  nokta sayısı: {len(m.ranges)}  |  geçerli: %{valid:.0f}")
    for name, c in (("ön", 0), ("sol", 90), ("arka", 180), ("sağ", -90)):
        d = view.sector_min(math.radians(c), math.radians(15))
        print(f"  {name:5s}: {d:.2f} m" if d != math.inf else f"  {name:5s}: (nokta yok)")
    print("\nBir nesneyi aracın önüne koyunca 'ön' değeri düşmeli. Düşmüyorsa lidar_yaw_deg (robot.yaml) yanlış olabilir.")
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
