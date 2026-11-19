import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from arac.config import load_config  # noqa: E402
from arac.gpio_backend import MockBackend  # noqa: E402
from arac.motor import Motor, Standby  # noqa: E402

BCM_USABLE = set(range(2, 28))


class TestMotor(unittest.TestCase):
    def test_direction_and_pwm(self):
        g = MockBackend()
        m = Motor(g, 12, 5, 6)
        m.set(0.5)
        self.assertEqual((g.levels[5], g.levels[6], g.pwm_duty[12]), (1, 0, 50.0))
        m.set(-0.25)
        self.assertEqual((g.levels[5], g.levels[6], g.pwm_duty[12]), (0, 1, 25.0))
        m.stop()
        self.assertEqual((g.levels[5], g.levels[6], g.pwm_duty[12]), (0, 0, 0.0))

    def test_invert(self):
        g = MockBackend()
        Motor(g, 13, 20, 21, invert=True).set(0.4)
        self.assertEqual((g.levels[20], g.levels[21]), (0, 1))

    def test_standby_starts_low(self):
        g = MockBackend()
        s = Standby(g, 26)
        self.assertEqual(g.levels[26], 0)
        s.enable()
        self.assertEqual(g.levels[26], 1)
        s.disable()
        self.assertEqual(g.levels[26], 0)


class TestPins(unittest.TestCase):
    def test_pins_unique_and_valid(self):
        p = load_config()["pins"]
        used = [p["driver"]["stby"]]
        for side in ("left", "right"):
            m, e = p["motors"][side], p["encoders"][side]
            used += [m["pwm"], m["in1"], m["in2"], e["a"], e["b"]]
        self.assertEqual(len(used), len(set(used)), f"aynı GPIO iki kez kullanılmış: {used}")
        self.assertTrue(set(used) <= BCM_USABLE)
        self.assertFalse({2, 3} & set(used), "GPIO2/3 I2C (BNO055) için ayrılmış")


if __name__ == "__main__":
    unittest.main()
