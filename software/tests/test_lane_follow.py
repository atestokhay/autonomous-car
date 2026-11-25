"""Şerit ortalama: yarışma pistinde (şartname Şekil AC-2) çarpmadan, ters geçiş yapmadan tur atmalı."""
import importlib.util
import math
import pathlib
import unittest

SIM = pathlib.Path(__file__).resolve().parents[1] / "stages" / "09-serit-ortalama" / "sim_pist.py"
spec = importlib.util.spec_from_file_location("sim_pist", SIM)
sim_pist = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sim_pist)


class LaneFollowTrackTest(unittest.TestCase):
    def test_single_robot_laps(self):
        r = sim_pist.sim("test-1", [(0.30, 1.35, -math.pi / 2)], seconds=75.0, out=None)
        self.assertGreaterEqual(r["laps"][0] - 1, 2, "75 sn'de en az 2 tam tur bekleniyor")
        self.assertEqual(r["back"][0], 0, "ters yönde çizgi geçişi olmamalı")
        self.assertEqual(r["bump_s"][0], 0.0, "duvara temas olmamalı")

    def test_two_robots_no_contact(self):
        r = sim_pist.sim("test-2", [(0.30, 1.35, -math.pi / 2), (0.30, 1.65, -math.pi / 2)],
                         seconds=60.0, out=None)
        self.assertGreater(r["rr_min"], 0.20, "robotlar birbirine değmemeli (20 cm gövde)")
        self.assertEqual(sum(r["back"]), 0)

    def test_robot_ahead_is_detected(self):
        """Önde 40 cm'de duran 20x15 cm rakip, robot olarak bulunmalı (duvardan ayrılmalı)."""
        import random
        from arac.lane_follow import find_robots
        from arac.scan import ScanView
        world = sim_pist.World(sim_pist.WALLS + sim_pist.box(0.30, 1.20, -math.pi / 2))
        r, amin, inc = world.scan(0.30, 1.60, -math.pi / 2, n=720, noise=0.01, dropout=0.03,
                                  rng=random.Random(1))
        v = ScanView(r, amin, inc)
        bots = find_robots(v.xs, v.ys, sim_pist.load_config()["nav"]["lane_follow"])
        near = [b for b in bots if 0.25 < b[0] < 0.45 and abs(b[1]) < 0.08]
        self.assertEqual(len(near), 1, f"bulunan kümeler: {[(round(b[0], 2), round(b[1], 2)) for b in bots]}")

    def test_slow_rival_not_stuck(self):
        """Faz 1: önde yavaş (0.15 m/s, robot tanımasız) iki rakip. Bizimki takılmamalı, ters gitmemeli,
        değmemeli."""
        down = -math.pi / 2
        slow = {"v_max": 0.15, "robot_detect": False}
        r = sim_pist.sim("test-yavas", [(0.30, 1.60, down), (0.15, 1.30, down), (0.45, 1.30, down)],
                         seconds=100.0, out=None, params=[{}, slow, slow])
        self.assertGreaterEqual(r["laps"][0] - 1, 1, "yavaş rakiplerin arkasında takılmamalı")
        self.assertEqual(sum(r["back"]), 0, "ters yönde çizgi geçişi olmamalı")
        self.assertEqual(r["contact_s"], 0.0, "robotlar birbirine değmemeli")


if __name__ == "__main__":
    unittest.main()
