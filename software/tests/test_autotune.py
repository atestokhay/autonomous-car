import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from arac import tuning  # noqa: E402
from arac.autotune import Rig, autotune_side  # noqa: E402
from arac.config import load_config  # noqa: E402
from arac.sim import SimEncoder, SimMotor, SimPlant  # noqa: E402

PC = load_config()["pid"]
TICKS = 392


class Flipped(SimEncoder):
    @property
    def count(self):
        return -int(self.plant.pos_ticks)


def rig_for(plant, enc_cls=SimEncoder):
    return Rig(SimMotor(plant), enc_cls(plant), plant, virtual=True)


class AutotuneTest(unittest.TestCase):
    def check(self, K, tau, db):
        r = autotune_side(rig_for(SimPlant(TICKS, k=K, tau=tau, deadband=db)), TICKS, PC, log=lambda *_: None)
        p = r["params"]
        self.assertAlmostEqual(p["kff"] * K, 1.0, delta=0.03)
        self.assertAlmostEqual(p["deadband"], db, delta=0.02)
        self.assertGreater(p["kp"], 0)
        self.assertGreater(p["ki"], 0)
        self.assertLessEqual(r["metrics"]["overshoot_pct"], 8.0)
        self.assertLessEqual(r["metrics"]["ss_err_pct"], 3.0)
        self.assertEqual(r["warnings"], [])

    def test_nominal(self):
        self.check(37.0, 0.08, 0.10)

    def test_weak_slow_motor(self):
        self.check(25.0, 0.15, 0.05)

    def test_strong_fast_motor_big_deadband(self):
        self.check(45.0, 0.04, 0.20)

    def test_reversed_encoder_aborts(self):
        with self.assertRaises(RuntimeError) as cm:
            autotune_side(rig_for(SimPlant(TICKS), Flipped), TICKS, PC, log=lambda *_: None)
        self.assertIn("NEGATİF", str(cm.exception))

    def test_dead_motor_aborts(self):
        with self.assertRaises(RuntimeError):
            autotune_side(rig_for(SimPlant(TICKS, k=0.001)), TICKS, PC, log=lambda *_: None)

    def test_wrong_ticks_warns(self):
        # gerçekte 392 tick/tur ama config 98 sanılırsa: hız 4x büyük görünür
        r = autotune_side(rig_for(SimPlant(TICKS)), 98, PC, log=lambda *_: None)
        self.assertTrue(r["warnings"])

    def test_tuning_math(self):
        pts = [(0.2, 3.7), (0.4, 11.1), (0.6, 18.5), (0.8, 25.9)]
        m = tuning.model_from_sweep(pts)
        self.assertAlmostEqual(m["K"], 37.0, delta=0.1)
        self.assertAlmostEqual(m["deadband"], 0.1, delta=0.01)


if __name__ == "__main__":
    unittest.main()
