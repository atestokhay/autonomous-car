"""Diferansiyel sürüş kinematiği ve odometri. Konvansiyon: x ileri, y sol, açı saat yönünün tersi (+)."""
import math

TWO_PI = 2.0 * math.pi


def wrap_pi(a):
    return (a + math.pi) % TWO_PI - math.pi


class Kinematics:
    def __init__(self, wheel_radius, wheel_base):
        self.r, self.b = wheel_radius, wheel_base

    def twist_to_wheels(self, v, w):
        """(m/s, rad/s) -> (sol, sağ) tekerlek açısal hızı rad/s."""
        return (v - w * self.b / 2.0) / self.r, (v + w * self.b / 2.0) / self.r

    def wheels_to_twist(self, wl, wr):
        vl, vr = wl * self.r, wr * self.r
        return (vl + vr) / 2.0, (vr - vl) / self.b

    @staticmethod
    def limit(wl, wr, max_speed):
        """İki tekerleği oranı bozmadan max_speed (rad/s) altına ölçekler."""
        m = max(abs(wl), abs(wr))
        if m <= max_speed or m == 0.0:
            return wl, wr
        k = max_speed / m
        return wl * k, wr * k


class Odometry:
    """Enkoder sayımlarından poz. Sayımlar ileri yönde artmalı (invert ayarları buna göre)."""

    def __init__(self, kin, ticks_per_rev, x=0.0, y=0.0, th=0.0):
        self.kin, self.rad_per_tick = kin, TWO_PI / ticks_per_rev
        self.x, self.y, self.th = x, y, th
        self.v = self.w = 0.0
        self._last = None

    def reset_counts(self, left, right):
        self._last = (left, right)

    def update(self, left, right, dt=None):
        if self._last is None:
            self._last = (left, right)
            return self.x, self.y, self.th
        dl = (left - self._last[0]) * self.rad_per_tick * self.kin.r
        dr = (right - self._last[1]) * self.rad_per_tick * self.kin.r
        self._last = (left, right)
        d, dth = (dl + dr) / 2.0, (dr - dl) / self.kin.b
        if abs(dth) < 1e-9:
            self.x += d * math.cos(self.th)
            self.y += d * math.sin(self.th)
        else:                                   # tam yay integrasyonu
            R = d / dth
            self.x += R * (math.sin(self.th + dth) - math.sin(self.th))
            self.y -= R * (math.cos(self.th + dth) - math.cos(self.th))
        self.th = wrap_pi(self.th + dth)
        if dt:
            self.v, self.w = d / dt, dth / dt
        return self.x, self.y, self.th


def corrected_radius(radius, odom_dist, actual_dist):
    """Düz gidiş kalibrasyonu: odometri odom_dist dedi, gerçek actual_dist ölçüldü."""
    return radius * actual_dist / odom_dist


def corrected_base(base, odom_angle, actual_angle):
    """Yerinde dönüş kalibrasyonu (açılar aynı birimde): odometri odom_angle dedi, gerçek actual_angle."""
    return base * odom_angle / actual_angle
