import math
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from arac import calibration, rplidar_probe  # noqa: E402
from arac.config import load_config  # noqa: E402
from arac.factory import build_drive  # noqa: E402
from arac.gpio_backend import parse_gpiodetect  # noqa: E402
from arac.kinematics import Kinematics, Odometry, corrected_base, corrected_radius, wrap_pi  # noqa: E402

R, B, TPR = 0.032, 0.160, 392


def run(drive, parts, seconds, v, w, dt=0.01, t0=0.0):
    t = t0
    for _ in range(int(seconds / dt)):
        t += dt
        drive.set_cmd(v, w, t)
        drive.update(dt, t)
        for p in parts.values():
            p["plant"].step(dt)
    return t


def make():
    cfg = load_config()
    cfg["robot"]["wheel_radius_m"], cfg["robot"]["wheel_base_m"], cfg["robot"]["ticks_per_rev"] = R, B, TPR
    _, parts, drive = build_drive(cfg, mock=True)
    return parts, drive


class DriveTest(unittest.TestCase):
    def test_straight_speed_and_odometry(self):
        parts, drive = make()
        run(drive, parts, 5.0, 0.30, 0.0)
        self.assertAlmostEqual(drive.v, 0.30, delta=0.02)
        self.assertGreater(drive.odom.x, 1.2)
        self.assertAlmostEqual(drive.odom.y, 0.0, delta=0.02)
        self.assertAlmostEqual(parts["left"]["plant"].omega * R, 0.30, delta=0.02)

    def test_spin_in_place(self):
        parts, drive = make()
        run(drive, parts, 3.0, 0.0, 1.0)
        self.assertAlmostEqual(drive.w, 1.0, delta=0.08)
        self.assertAlmostEqual(drive.odom.x, 0.0, delta=0.02)
        self.assertGreater(drive.odom.th, 2.0)

    def test_arc(self):
        parts, drive = make()
        run(drive, parts, 4.0, 0.25, 0.5)
        self.assertGreater(drive.odom.th, 1.4)
        self.assertGreater(drive.odom.y, 0.2)

    def test_timeout_stops_robot(self):
        parts, drive = make()
        t = run(drive, parts, 2.0, 0.3, 0.0)
        for _ in range(100):               # komut kesildi: 1 sn boyunca set_cmd yok
            t += 0.01
            drive.update(0.01, t)
            for p in parts.values():
                p["plant"].step(0.01)
        self.assertTrue(drive.stale)
        self.assertLess(abs(parts["left"]["plant"].omega), 1.0)

    def test_speed_limited(self):
        parts, drive = make()
        run(drive, parts, 3.0, 5.0, 0.0)   # imkânsız hız: max_speed_rad_s'e kırpılır
        self.assertLessEqual(parts["left"]["plant"].omega, load_config()["pid"]["max_speed_rad_s"] + 1.0)


class KinematicsTest(unittest.TestCase):
    def test_roundtrip(self):
        k = Kinematics(R, B)
        wl, wr = k.twist_to_wheels(0.3, 0.8)
        v, w = k.wheels_to_twist(wl, wr)
        self.assertAlmostEqual(v, 0.3)
        self.assertAlmostEqual(w, 0.8)

    def test_limit_keeps_ratio(self):
        wl, wr = Kinematics.limit(10.0, 20.0, 15.0)
        self.assertAlmostEqual(wr, 15.0)
        self.assertAlmostEqual(wl / wr, 0.5)

    def test_odometry_circle(self):
        k = Kinematics(R, B)
        o = Odometry(k, TPR)
        wl, wr = k.twist_to_wheels(0.2, 0.5)   # yarıçap 0.4 m daire
        steps, dt = 1000, 0.01
        cl = cr = 0.0
        o.update(0, 0)
        for _ in range(int(2 * math.pi / 0.5 / dt)):
            cl += wl * dt * TPR / (2 * math.pi)
            cr += wr * dt * TPR / (2 * math.pi)
            o.update(int(round(cl)), int(round(cr)))
        self.assertAlmostEqual(o.x, 0.0, delta=0.03)       # tam tur: başlangıca döner
        self.assertAlmostEqual(o.y, 0.0, delta=0.03)

    def test_wrap(self):
        self.assertAlmostEqual(abs(wrap_pi(3 * math.pi)), math.pi)


class CalibrationTest(unittest.TestCase):
    def test_radius_from_push(self):
        true_r, dist = 0.0335, 1.0
        ticks = int(round(dist / true_r / (2 * math.pi) * TPR))
        r = calibration.wheel_radius_from_push(dist, ticks, ticks + 1, TPR)
        self.assertAlmostEqual(r, true_r, delta=0.0005)

    def test_base_from_spin(self):
        true_b, turns = 0.172, 3
        theta = turns * 2 * math.pi
        dphi = theta * true_b / 2 / R
        tl, tr = -int(round(dphi * TPR / (2 * math.pi))), int(round(dphi * TPR / (2 * math.pi)))
        b = calibration.wheel_base_from_spin(theta, tl, tr, TPR, R)
        self.assertAlmostEqual(b, true_b, delta=0.002)

    def test_corrections(self):
        self.assertAlmostEqual(corrected_radius(0.03, 0.9, 1.0), 0.03 * 1.0 / 0.9)
        self.assertAlmostEqual(corrected_base(0.16, 6.0, 6.28), 0.16 * 6.0 / 6.28)


class ProbeTest(unittest.TestCase):
    class FakePort:
        def __init__(self, replies):
            self.replies, self.buf, self.sent = replies, b"", []

        def reset_input_buffer(self):
            self.buf = b""

        def write(self, data):
            self.sent.append(data)
            self.buf = self.replies[data[1]]

        def read(self, n):
            out, self.buf = self.buf[:n], self.buf[n:]
            return out

    def test_probe_ok(self):
        info_payload = bytes([0x61, 5, 1, 18]) + bytes(range(16))
        replies = {0x50: bytes([0xA5, 0x5A, 20, 0, 0, 0, 0x04]) + info_payload,
                   0x52: bytes([0xA5, 0x5A, 3, 0, 0, 0, 0x06, 0, 0, 0])}
        port = self.FakePort(replies)
        info, health = rplidar_probe.probe(port)
        self.assertEqual(info["firmware"], "1.05")
        self.assertEqual(health[0], 0)
        self.assertEqual(port.sent, [b"\xA5\x50", b"\xA5\x52"])

    def test_probe_silent_port(self):
        port = self.FakePort({0x50: b"", 0x52: b""})
        with self.assertRaises(RuntimeError):
            rplidar_probe.probe(port)

    def test_health_error_text(self):
        self.assertIn("HATA", rplidar_probe.parse_health(bytes([2, 0x34, 0x12]))[2])


class GpioDetectTest(unittest.TestCase):
    def test_parse(self):
        txt = "gpiochip0 [gpio-brcmstb@107d508500] (32 lines)\ngpiochip4 [pinctrl-rp1] (54 lines)\n"
        self.assertEqual(parse_gpiodetect(txt), 4)
        self.assertEqual(parse_gpiodetect("gpiochip0 [pinctrl-rp1] (54 lines)"), 0)
        self.assertIsNone(parse_gpiodetect("gpiochip0 [foo] (1 lines)"))


if __name__ == "__main__":
    unittest.main()
