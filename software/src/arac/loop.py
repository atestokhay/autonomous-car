import os
import time


def try_realtime(priority=50):
    """Gerçek zamanlı zamanlayıcıyı dener (sudo gerekir). Başarısızsa False."""
    try:
        os.sched_setscheduler(0, os.SCHED_FIFO, os.sched_param(priority))
        return True
    except (PermissionError, AttributeError, OSError):
        return False


class RateLoop:
    """Sabit frekanslı döngü (mutlak zaman damgalı, kayma yok). wait() gerçek dt'yi döner."""

    def __init__(self, hz):
        self._period_ns = int(1e9 / hz)
        now = time.monotonic_ns()
        self._last = now
        self._next = now + self._period_ns
        self.n = self.overruns = 0
        self.dt_min, self.dt_max, self._sum = float("inf"), 0.0, 0.0

    def wait(self):
        rem = (self._next - time.monotonic_ns()) / 1e9
        if rem > 0:
            time.sleep(rem)
        now = time.monotonic_ns()
        dt = (now - self._last) / 1e9
        self._last = now
        self._next += self._period_ns
        if now > self._next:  # bir periyottan fazla geciktik
            self.overruns += 1
            self._next = now + self._period_ns
        self.n += 1
        self._sum += dt
        self.dt_min, self.dt_max = min(self.dt_min, dt), max(self.dt_max, dt)
        return dt

    def stats(self):
        mean = self._sum / self.n if self.n else 0.0
        return {"n": self.n, "dt_mean_ms": mean * 1e3, "dt_min_ms": self.dt_min * 1e3,
                "dt_max_ms": self.dt_max * 1e3, "overruns": self.overruns}
