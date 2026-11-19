class Motor:
    """TB6612FNG, tek kanal (A ya da B). duty: -1..+1 (pozitif = ileri).

    IN1/IN2 yönü, PWM hızı belirler. Sürücünün STBY pini ayrıca HIGH olmalıdır (bkz. Standby).
    """

    def __init__(self, gpio, pwm, in1, in2, pwm_hz=2000, invert=False):
        self._g, self.pwm, self.in1, self.in2 = gpio, pwm, in1, in2
        self.pwm_hz, self.invert, self.duty = pwm_hz, invert, 0.0
        for p in (pwm, in1, in2):
            gpio.output(p, 0)

    def set(self, duty):
        duty = max(-1.0, min(1.0, float(duty)))
        self.duty = duty
        d = -duty if self.invert else duty
        a, b = (1, 0) if d > 0 else (0, 1) if d < 0 else (0, 0)
        self._g.write(self.in1, a)  # önce yön, sonra PWM
        self._g.write(self.in2, b)
        self._g.pwm(self.pwm, self.pwm_hz, abs(d) * 100.0)

    def stop(self):
        self.set(0.0)


class Standby:
    """TB6612FNG STBY pini. LOW iken iki kanal da kapalıdır; motorlar ancak enable() sonrası döner."""

    def __init__(self, gpio, pin):
        self._g, self.pin = gpio, pin
        gpio.output(pin, 0)

    def enable(self):
        self._g.write(self.pin, 1)

    def disable(self):
        self._g.write(self.pin, 0)
