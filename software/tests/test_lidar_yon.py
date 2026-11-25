import math
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from arac.lidar_yon import find_front  # noqa: E402


def room_scan(rx, ry, heading_deg, lidar_yaw_deg, n=720, w=4.0, h=3.0):
    """Dikdörtgen oda (0..w, 0..h). Araç (rx, ry) konumunda heading yönüne bakıyor.
    LiDAR, araca göre lidar_yaw_deg dönük takılı (lidar 0° → araç yönü + lidar_yaw)."""
    ranges = []
    inc = 2 * math.pi / n
    for i in range(n):
        a = math.radians(heading_deg) - math.radians(lidar_yaw_deg) + (-math.pi + i * inc)
        dx, dy = math.cos(a), math.sin(a)
        ts = []
        if dx > 1e-9:
            ts.append((w - rx) / dx)
        if dx < -1e-9:
            ts.append(-rx / dx)
        if dy > 1e-9:
            ts.append((h - ry) / dy)
        if dy < -1e-9:
            ts.append(-ry / dy)
        ranges.append(min(ts))
    return ranges, -math.pi, inc


class TestLidarYon(unittest.TestCase):
    def check(self, mount):
        # mount: LiDAR'ın araca göre dönüklüğü. robot.yaml lidar_yaw_deg = mount olmalı.
        b = room_scan(1.5, 1.2, 30, -mount)
        h = math.radians(30)
        a = room_scan(1.5 + 0.2 * math.cos(h), 1.2 + 0.2 * math.sin(h), 30, -mount)
        r = find_front(b, a)
        self.assertAlmostEqual(((r["yaw_deg"] - mount + 180) % 360) - 180, 0, delta=10)
        self.assertAlmostEqual(r["move_m"], 0.2, delta=0.06)
        self.assertLessEqual(abs(r["rot_deg"]), 3)

    def test_mounts(self):
        for m in (0, 90, 180, -90, 45):
            with self.subTest(mount=m):
                self.check(m)

    def test_spin_detected(self):
        b = room_scan(1.5, 1.2, 0, 0)
        a = room_scan(1.5, 1.2, 25, 0)
        self.assertGreater(abs(find_front(b, a)["rot_deg"]), 15)


if __name__ == "__main__":
    unittest.main()
