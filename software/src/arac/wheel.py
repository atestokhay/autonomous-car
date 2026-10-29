import math
from collections import deque

from .pid import SlewLimiter


class WheelSpeedController:
    """Tek tekerlek hız kontrolü (rad/s). Pozitif hedef = ileri.
    Hız: son `speed_window` döngü penceresinden (tek döngüdeki 1-tick kuantalamasını azaltır)."""

    BAD_DUTY, BAD_TIME = 0.6, 0.5  # yüksek duty + hız yok/ters => kaçış (runaway) koruması

    def __init__(self, motor, encoder, pid, ticks_per_rev, speed_alpha=0.6,
                 max_accel=60.0, speed_window=4):
        self.motor, self.encoder, self.pid = motor, encoder, pid
        self._rad_per_tick = 2.0 * math.pi / ticks_per_rev
        self._alpha = speed_alpha
        self._slew = SlewLimiter(max_accel)
        self._t = 0.0
        self._hist = deque([(encoder.count, 0.0)], maxlen=speed_window + 1)
        self._bad = 0.0
        self.target = 0.0
        self.speed = 0.0
        self.duty = 0.0

    def reset(self):
        """Döngü başlamadan hemen önce çağır: eski sayım/zaman geçmişini ve integrali sıfırlar."""
        self._t = 0.0
        self._hist.clear()
        self._hist.append((self.encoder.count, 0.0))
        self._slew.value = 0.0
        self._bad = 0.0
        self.speed = self.duty = 0.0
        self.pid.reset()

    def set_target(self, rad_s):
        self.target = rad_s

    def update(self, dt):
        self._t += dt
        c = self.encoder.count
        self._hist.append((c, self._t))
        c0, t0 = self._hist[0]
        raw = (c - c0) * self._rad_per_tick / (self._t - t0)
        self.speed += self._alpha * (raw - self.speed)
        sp = self._slew.step(self.target, dt)
        self.duty = self.pid.update(sp, self.speed, dt)

        # Enkoder yönü ters / tekerlek sıkışık: tam gaz verip gitmesin
        if abs(self.duty) >= self.BAD_DUTY and sp * self.speed <= 0.0:
            self._bad += dt
            if self._bad > self.BAD_TIME:
                self.stop()
                raise RuntimeError(
                    "Hız tepkisi yok/ters: enkoder invert ayarını veya tekerlek sıkışmasını kontrol et")
        else:
            self._bad = 0.0

        self.motor.set(self.duty)
        return sp, self.speed, self.duty

    def stop(self):
        self.target = 0.0
        self.motor.stop()
