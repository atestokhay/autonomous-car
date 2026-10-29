"""GPIO soyutlaması: gerçek Pi 5 (lgpio) ve donanımsız test (mock)."""
import re
import subprocess
import time


def parse_gpiodetect(text):
    """`gpiodetect` çıktısından RP1 (Pi 5 40 pinli başlık) çipinin numarasını bulur."""
    for line in text.splitlines():
        m = re.match(r"gpiochip(\d+)\s+\[([^\]]+)\]", line.strip())
        if m and "rp1" in m.group(2).lower():
            return int(m.group(1))
    return None


def resolve_gpiochip(value):
    """pins.yaml `gpiochip`: sayı ya da "auto" (gpiodetect ile bulur)."""
    if isinstance(value, int):
        return value
    out = subprocess.run(["gpiodetect"], capture_output=True, text=True, timeout=5).stdout
    chip = parse_gpiodetect(out)
    if chip is None:
        raise RuntimeError("gpiodetect çıktısında pinctrl-rp1 yok. `sudo apt install gpiod` kurulu mu? "
                           "Elle ayarlamak için pins.yaml → gpiochip: <sayı>")
    return chip


class LgpioBackend:
    def __init__(self, chip):
        import lgpio  # sadece Pi'de gerekli

        self._l = lgpio
        self._h = lgpio.gpiochip_open(chip)
        self._cbs = []
        self._pins = []

    def output(self, gpio, level=0):
        self._l.gpio_claim_output(self._h, gpio, level)
        self._pins.append(gpio)

    def write(self, gpio, level):
        self._l.gpio_write(self._h, gpio, level)

    def pwm(self, gpio, hz, duty_pct):
        # lgpio PWM yazılım zamanlamalıdır (jitter görürsen donanım PWM'ine geçilir)
        self._l.tx_pwm(self._h, gpio, hz, duty_pct)

    def watch(self, gpio, fn, pull_up=True):
        l = self._l
        l.gpio_claim_alert(self._h, gpio, l.BOTH_EDGES, l.SET_PULL_UP if pull_up else 0)
        self._pins.append(gpio)
        self._cbs.append(
            l.callback(self._h, gpio, l.BOTH_EDGES, lambda chip, g, level, ts: fn(g, level, ts))
        )

    def read(self, gpio):
        return self._l.gpio_read(self._h, gpio)

    def close(self):
        for cb in self._cbs:
            cb.cancel()
        for p in self._pins:
            try:
                self._l.gpio_free(self._h, p)
            except Exception:
                pass
        self._l.gpiochip_close(self._h)


class MockBackend:
    """Donanımsız test: yazılanları saklar, emit() ile kenar üretir."""

    def __init__(self):
        self.levels, self.pwm_duty, self.watchers = {}, {}, {}

    def output(self, gpio, level=0):
        self.levels[gpio] = level

    def write(self, gpio, level):
        self.levels[gpio] = level

    def pwm(self, gpio, hz, duty_pct):
        self.pwm_duty[gpio] = duty_pct

    def watch(self, gpio, fn, pull_up=True):
        self.watchers[gpio] = fn
        self.levels.setdefault(gpio, 0)

    def read(self, gpio):
        return self.levels.get(gpio, 0)

    def emit(self, gpio, level):
        self.levels[gpio] = level
        self.watchers[gpio](gpio, level, time.monotonic_ns())

    def close(self):
        pass
