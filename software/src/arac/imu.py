"""BNO055 (I2C) yönelim okuyucu: odometride dönüş açısını (yaw) gyro füzyonundan alır.
Enkoder mesafeyi, BNO055 dönüş açısını verir; tekerlek kayması açıyı bozmaz.
Mod IMUPLUS (ivmeölçer + gyro, manyetometre YOK): motorların/bataryanın manyetik alanından etkilenmez.
Açı göreli başlar (açılışta 0); odometri sadece açı FARKINI kullanır.
Konvansiyon: dönüş saat yönünün tersine (+), kinematics.py ile aynı."""
import math
import time

REG_CHIP_ID, CHIP_ID = 0x00, 0xA0
REG_PAGE = 0x07
REG_EUL_HEADING = 0x1A      # 2 bayt, LSB önce, 16 LSB = 1 derece, saat yönünde artar
REG_CALIB_STAT = 0x35
REG_UNIT_SEL = 0x3B
REG_OPR_MODE = 0x3D
REG_PWR_MODE = 0x3E
MODE_CONFIG = 0x00
MODES = {"imuplus": 0x08, "ndof": 0x0C}


class LgpioI2C:
    """lgpio ile I2C (Pi 5'te ek paket gerekmez: python3-lgpio zaten kurulu)."""

    def __init__(self, bus, address):
        import lgpio  # sadece Pi'de gerekli

        self._l = lgpio
        self._h = lgpio.i2c_open(int(bus), int(address))

    def read_byte(self, reg):
        return self._l.i2c_read_byte_data(self._h, reg)

    def write_byte(self, reg, value):
        self._l.i2c_write_byte_data(self._h, reg, value)

    def read_block(self, reg, n):
        count, data = self._l.i2c_read_i2c_block_data(self._h, reg, n)
        if count != n:
            raise OSError(f"I2C okuma {count}/{n} bayt")
        return bytes(data)

    def close(self):
        self._l.i2c_close(self._h)


class Bno055:
    def __init__(self, bus, mode="imuplus", invert=False, sleep=time.sleep):
        """bus: read_byte / write_byte / read_block. invert: kart TERS (çip yüzü aşağı) takılıysa True."""
        self.bus, self._sign = bus, (1 if invert else -1)   # BNO055 heading saat yönünde artar -> çevir
        if mode not in MODES:
            raise ValueError(f"imu.mode '{mode}' olamaz; seçenekler: {', '.join(MODES)}")
        if bus.read_byte(REG_CHIP_ID) != CHIP_ID:
            sleep(0.7)                                       # açılıştan hemen sonra çip ~650 ms meşgul
            if bus.read_byte(REG_CHIP_ID) != CHIP_ID:
                raise RuntimeError("BNO055 kimliği okunamadı (0xA0 beklenir): adres/kablolama?")
        bus.write_byte(REG_OPR_MODE, MODE_CONFIG)
        sleep(0.025)
        bus.write_byte(REG_PAGE, 0)
        bus.write_byte(REG_PWR_MODE, 0x00)                   # normal güç
        bus.write_byte(REG_UNIT_SEL, 0x00)                   # derece, dps, Windows yönelim düzeni
        bus.write_byte(REG_OPR_MODE, MODES[mode])
        sleep(0.02)

    def yaw(self):
        """Göreli yönelim (rad), saat yönünün tersi (+), [-pi, pi)."""
        lo, hi = self.bus.read_block(REG_EUL_HEADING, 2)
        raw = (hi << 8) | lo
        if raw >= 0x8000:
            raw -= 0x10000
        a = self._sign * math.radians(raw / 16.0)
        return (a + math.pi) % (2.0 * math.pi) - math.pi

    def calibration(self):
        """(sistem, gyro, ivme, manyetometre), her biri 0..3. IMUPLUS'ta gyro 3 olmalı."""
        s = self.bus.read_byte(REG_CALIB_STAT)
        return (s >> 6) & 3, (s >> 4) & 3, (s >> 2) & 3, s & 3

    def close(self):
        if hasattr(self.bus, "close"):
            self.bus.close()


def open_imu(cfg):
    """pins.yaml `imu` bölümüne göre BNO055'i açar. Döner: (imu ya da None, açıklama)."""
    p = cfg["pins"].get("imu") or {}
    if not p.get("use_for_heading"):
        return None, "IMU kapalı (pins.yaml → imu.use_for_heading: false): açı enkoderden"
    try:
        bus = LgpioI2C(p.get("i2c_bus", 1), p.get("address", 0x28))
    except Exception as e:  # noqa: BLE001  (lgpio yok, /dev/i2c-1 yok, izin yok...)
        return None, f"BNO055 açılamadı ({e}): açı enkoderden hesaplanacak"
    try:
        return Bno055(bus, p.get("mode", "imuplus"), bool(p.get("yaw_invert", False))), "BNO055 hazır: açı gyro'dan"
    except Exception as e:  # noqa: BLE001
        try:
            bus.close()
        except Exception:  # noqa: BLE001
            pass
        return None, f"BNO055 başlatılamadı ({e}): açı enkoderden hesaplanacak"
