import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from arac.config import load_config  # noqa: E402
from arac.pid import PID, SlewLimiter  # noqa: E402
from arac.sim import SimPlant  # noqa: E402


def run(pid, plant, setpoint, seconds, dt=0.01, slew=60.0):
    lim, w_hist = SlewLimiter(slew), []
    for _ in range(int(seconds / dt)):
        sp = lim.step(setpoint, dt)
        plant.duty = pid.update(sp, plant.omega, dt)
        plant.step(dt)
        w_hist.append(plant.omega)
    return w_hist


class PidTest(unittest.TestCase):
    def pid(self, **kw):
        base = dict(load_config()["pid"]["left"])
        base.update(kw)
        return PID(**base)

    def test_reaches_setpoint(self):
        w = run(self.pid(), SimPlant(), 20.0, 3.0)
        self.assertAlmostEqual(w[-1], 20.0, delta=0.4)

    def test_overshoot_small(self):
        w = run(self.pid(), SimPlant(), 20.0, 3.0)
        self.assertLess(max(w), 20.0 * 1.05)

    def test_model_mismatch_integral_fixes_it(self):
        # kff gerçek motordan %25 farklı: integral telafi etmeli
        w = run(self.pid(), SimPlant(k=28.0, deadband=0.15), 20.0, 4.0)
        self.assertAlmostEqual(w[-1], 20.0, delta=0.5)

    def test_reverse(self):
        w = run(self.pid(), SimPlant(), -15.0, 3.0)
        self.assertAlmostEqual(w[-1], -15.0, delta=0.4)

    def test_output_bounded_and_antiwindup(self):
        p, plant = self.pid(), SimPlant()
        for _ in range(300):             # imkânsız hedef: doyum
            plant.duty = p.update(500.0, plant.omega, 0.01)
            self.assertLessEqual(abs(plant.duty), 1.0)
            plant.step(0.01)
        self.assertLessEqual(abs(p._i), p.i_limit)
        w = run(p, plant, 10.0, 2.0)     # sonra normal hedefe hızlı dönebilmeli
        self.assertAlmostEqual(w[-1], 10.0, delta=0.5)

    def test_stop_command_zero_output(self):
        p = self.pid()
        self.assertEqual(p.update(0.0, 0.1, 0.01), 0.0)


if __name__ == "__main__":
    unittest.main()
