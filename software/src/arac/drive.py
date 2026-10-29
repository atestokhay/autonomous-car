"""Hız komutu (v, w) -> iki tekerlek PID -> odometri. ROS'suz, simülasyonda test edilir."""
from .kinematics import Kinematics  # noqa: F401  (limit için)


class DriveController:
    """cmd_timeout: komut bu süreden eskiyse hedef sıfırlanır (haberleşme koparsa araç durur)."""

    def __init__(self, left, right, kin, odom, max_wheel_speed, cmd_timeout=0.5):
        self.left, self.right, self.kin, self.odom = left, right, kin, odom
        self.max_wheel_speed, self.cmd_timeout = max_wheel_speed, cmd_timeout
        self._v = self._w = 0.0
        self._cmd_t = None
        self.stale = True
        self.v = self.w = 0.0          # ölçülen (filtreli) hız: yayınlanacak değer bu

    def set_cmd(self, v, w, now):
        self._v, self._w, self._cmd_t = float(v), float(w), now

    def update(self, dt, now):
        """Bir kontrol adımı. Döner: (x, y, th, v, w). Tekerlek güvenliği RuntimeError fırlatabilir."""
        self.stale = self._cmd_t is None or (now - self._cmd_t) > self.cmd_timeout
        v, w = (0.0, 0.0) if self.stale else (self._v, self._w)
        wl, wr = self.kin.twist_to_wheels(v, w)
        wl, wr = Kinematics.limit(wl, wr, self.max_wheel_speed)
        self.left.set_target(wl)
        self.right.set_target(wr)
        self.left.update(dt)
        self.right.update(dt)
        x, y, th = self.odom.update(self.left.encoder.count, self.right.encoder.count, dt)
        # Anlık odometri hızı tek enkoder darbesine kuantalıdır; filtreli tekerlek hızlarını kullan.
        self.v, self.w = self.kin.wheels_to_twist(self.left.speed, self.right.speed)
        return x, y, th, self.v, self.w

    def stop(self):
        self.left.stop()
        self.right.stop()
