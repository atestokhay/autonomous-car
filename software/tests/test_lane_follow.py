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


if __name__ == "__main__":
    unittest.main()
