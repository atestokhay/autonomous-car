import math
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from arac import imu as imu_mod  # noqa: E402
from arac.imu import Bno055  # noqa: E402
from arac.kinematics import Kinematics, Odometry  # noqa: E402


class FakeBus:
    """BNO055 kayıt haritası taklidi. heading_deg: çipin kendi açısı (saat yönünde artar)."""

    def __init__(self, chip_id=0xA0):
        self.regs = {0x00: chip_id, 0x35: 0b11110000}
        self.heading_deg = 0.0
        self.writes = []
        self.fail = False

    def read_byte(self, reg):
        return self.regs.get(reg, 0)

    def write_byte(self, reg, value):
        self.writes.append((reg, value))
        self.regs[reg] = value

    def read_block(self, reg, n):
        if self.fail:
            raise OSError("I2C hata")
        assert reg == 0x1A and n == 2
        raw = int(round(self.heading_deg * 16)) & 0xFFFF
        return bytes([raw & 0xFF, raw >> 8])


def no_sleep(_):
    pass


class Bno055Test(unittest.TestCase):
    def test_init_sets_imuplus_mode(self):
        bus = FakeBus()
        Bno055(bus, sleep=no_sleep)
        self.assertEqual(bus.writes[0], (0x3D, 0x00))          # önce CONFIG
        self.assertEqual(bus.writes[-1], (0x3D, 0x08))         # en son IMUPLUS

    def test_wrong_chip_raises(self):
        with self.assertRaises(RuntimeError):
            Bno055(FakeBus(chip_id=0x00), sleep=no_sleep)

    def test_bad_mode_raises(self):
        with self.assertRaises(ValueError):
            Bno055(FakeBus(), mode="pusula", sleep=no_sleep)

    def test_clockwise_heading_becomes_negative_yaw(self):
        bus = FakeBus()
        b = Bno055(bus, sleep=no_sleep)
        bus.heading_deg = 90.0                                 # çip: saat yönünde 90°
        self.assertAlmostEqual(b.yaw(), -math.pi / 2, places=3)
        bus.heading_deg = 270.0                                # = saat yönünün tersine 90°
        self.assertAlmostEqual(b.yaw(), math.pi / 2, places=3)

    def test_invert(self):
        bus = FakeBus()
        b = Bno055(bus, invert=True, sleep=no_sleep)
        bus.heading_deg = 90.0
        self.assertAlmostEqual(b.yaw(), math.pi / 2, places=3)

    def test_calibration_bits(self):
        self.assertEqual(Bno055(FakeBus(), sleep=no_sleep).calibration(), (3, 3, 0, 0))

    def test_open_imu_disabled_and_missing(self):
        imu, msg = imu_mod.open_imu({"pins": {"imu": {"use_for_heading": False}}})
        self.assertIsNone(imu)
        imu, msg = imu_mod.open_imu({"pins": {}})
        self.assertIsNone(imu)
        # lgpio/I2C yoksa (bu bilgisayar gibi) çökmez, None döner
        orig = imu_mod.LgpioI2C

        def boom(*a):
            raise OSError("no /dev/i2c-1")
        imu_mod.LgpioI2C = boom
        try:
            imu, msg = imu_mod.open_imu({"pins": {"imu": {"use_for_heading": True}}})
        finally:
            imu_mod.LgpioI2C = orig
        self.assertIsNone(imu)
        self.assertIn("enkoder", msg)


class OdometryHeadingTest(unittest.TestCase):
    R, B, TPR = 0.02, 0.15, 1400

    def test_heading_none_is_same_as_before(self):
        a = Odometry(Kinematics(self.R, self.B), self.TPR)
        b = Odometry(Kinematics(self.R, self.B), self.TPR)
        for i in range(1, 200):
            a.update(i * 10, i * 13, 0.01)
            b.update(i * 10, i * 13, 0.01, None)
        self.assertEqual((a.x, a.y, a.th), (b.x, b.y, b.th))

    def test_gyro_heading_overrides_wheel_slip(self):
        # Sağ tekerlek kayıyor (sayım fazla) ama araç gerçekte DÜZ gidiyor: gyro açı 0 der.
        o = Odometry(Kinematics(self.R, self.B), self.TPR)
        for i in range(0, 200):
            o.update(i * 10, i * 12, 0.01, 0.0)
        self.assertAlmostEqual(o.th, 0.0, places=6)
        self.assertAlmostEqual(o.y, 0.0, places=6)
        self.assertGreater(o.x, 0.15)

    def test_heading_delta_and_wrap(self):
        o = Odometry(Kinematics(self.R, self.B), self.TPR)
        o.update(0, 0, 0.01, 3.0)                               # çapa
        o.update(0, 0, 0.01, -3.0)                              # +pi sınırını geçti: fark ≈ +0.283
        self.assertAlmostEqual(o.th, 2 * math.pi - 6.0, places=6)

    def test_dropout_reanchors_without_jump(self):
        o = Odometry(Kinematics(self.R, self.B), self.TPR)
        o.update(0, 0, 0.01, 1.0)
        o.update(0, 0, 0.01, 1.2)                               # +0.2
        o.update(0, 0, 0.01, None)                              # okuma yok: enkoder (0 fark)
        o.update(0, 0, 0.01, 2.5)                               # yeni çapa, sıçrama YOK
        o.update(0, 0, 0.01, 2.6)                               # +0.1
        self.assertAlmostEqual(o.th, 0.3, places=6)


class DriveNodeImuFallbackTest(unittest.TestCase):
    def test_read_errors_fall_back_to_encoders(self):
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
        import test_ros_smoke as smoke
        smoke.install_fakes()
        node = smoke.load("drive_node").DriveNode(mock=True)
        bus = FakeBus()
        node.imu = Bno055(bus, sleep=no_sleep)
        bus.heading_deg = 10.0
        self.assertAlmostEqual(node.read_heading(), math.radians(-10.0), places=3)
        bus.fail = True
        for _ in range(19):
            self.assertIsNone(node.read_heading())
            self.assertIsNotNone(node.imu)                     # kısa kesinti: IMU bırakılmaz
        node.read_heading()
        self.assertIsNone(node.imu)                             # 20 hata: enkodere geçildi
        node.tick()                                             # düğüm çalışmaya devam eder
        node.shutdown()


if __name__ == "__main__":
    unittest.main()
