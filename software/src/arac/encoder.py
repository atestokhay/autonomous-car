import threading

# Kuadratür x4 çözümü: index = (önceki_durum << 2) | yeni_durum, durum = A<<1 | B
_DELTA = (0, 1, -1, 0,
          -1, 0, 0, 1,
          1, 0, 0, -1,
          0, -1, 1, 0)


class Encoder:
    """x4 kuadratür enkoder. `missed` > 0 ise kenar kaçırılıyor demektir."""

    def __init__(self, gpio, a, b, invert=False, pull_up=True):
        self._a, self._b = a, b
        self._sign = -1 if invert else 1
        self._lock = threading.Lock()
        self._count = 0
        self.missed = 0
        self._A = self._B = 0
        gpio.watch(a, self._on_edge, pull_up)
        gpio.watch(b, self._on_edge, pull_up)
        try:
            self._A, self._B = gpio.read(a), gpio.read(b)
        except Exception:
            pass
        self._state = (self._A << 1) | self._B

    def _on_edge(self, gpio, level, ts):
        if level > 1:  # watchdog
            return
        with self._lock:
            if gpio == self._a:
                self._A = level
            else:
                self._B = level
            new = (self._A << 1) | self._B
            d = _DELTA[(self._state << 2) | new]
            if d == 0 and new != self._state:
                self.missed += 1  # iki bit birden değişti: kenar kaçtı
            self._state = new
            self._count += d * self._sign

    @property
    def count(self):
        with self._lock:
            return self._count

    def reset(self):
        with self._lock:
            self._count = 0
            self.missed = 0
