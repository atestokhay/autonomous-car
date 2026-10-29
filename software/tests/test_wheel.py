import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from arac.pid import PID  # noqa: E402
from arac.sim import SimEncoder, SimMotor, SimPlant  # noqa: E402
from arac.wheel import WheelSpeedController  # noqa: E402


class WheelTest(unittest.TestCase):
    def build(self, flip=False):
        plant = SimPlant(1000)
        enc = SimEncoder(plant)
        if flip:  # enkoder ters bağlı gibi
            class Flipped(SimEncoder):
                @property
                def count(self):
                    return -int(self.plant.pos_ticks)
            enc = Flipped(plant)
        pid = PID(0.02, 0.1, 0.0, 0.027, 0.10)
        return plant, WheelSpeedController(SimMotor(plant), enc, pid, 1000)

    def test_closed_loop_tracks(self):
        plant, c = self.build()
        c.set_target(20.0)
        for _ in range(400):
            c.update(0.01)
            plant.step(0.01)
        self.assertAlmostEqual(c.speed, 20.0, delta=1.0)

    def test_reversed_encoder_triggers_safety(self):
        plant, c = self.build(flip=True)
        c.set_target(20.0)
        with self.assertRaises(RuntimeError):
            for _ in range(600):
                c.update(0.01)
                plant.step(0.01)
        self.assertEqual(plant.duty, 0.0)


if __name__ == "__main__":
    unittest.main()
