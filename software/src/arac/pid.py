def _clamp(x, lo, hi):
    return lo if x < lo else hi if x > hi else x


class SlewLimiter:
    """Hedef hızı ani sıçratmadan rampalar (max_rate birim/sn)."""

    def __init__(self, max_rate, value=0.0):
        self.max_rate, self.value = max_rate, value

    def step(self, target, dt):
        d = self.max_rate * dt
        self.value += _clamp(target - self.value, -d, d)
        return self.value


class PID:
    """Hız PID'i: feedforward (+ rampa için ileri besleme "lead"), deadband telafisi,
    ölçüm üzerinden filtreli D, koşullu integral (anti-windup). Çıkış: duty (-1..+1).
    ff_lead (sn): motor zaman sabiti; rampalı hedefte gecikmeyi önceden telafi eder."""

    def __init__(self, kp, ki, kd=0.0, kff=0.0, deadband=0.0, i_limit=0.5,
                 d_alpha=0.2, out_min=-1.0, out_max=1.0, stop_eps=0.5, ff_lead=0.0):
        self.kp, self.ki, self.kd, self.kff, self.ff_lead = kp, ki, kd, kff, ff_lead
        self.deadband, self.i_limit, self.d_alpha = deadband, i_limit, d_alpha
        self.out_min, self.out_max, self.stop_eps = out_min, out_max, stop_eps
        self.reset()

    def reset(self):
        self._i = 0.0
        self._d = 0.0
        self._prev = None
        self._prev_sp = None

    def update(self, setpoint, measurement, dt):
        if self._prev is None:
            self._prev = measurement  # ilk adımda D sıçraması olmasın
        sp_dot = 0.0 if self._prev_sp is None else (setpoint - self._prev_sp) / dt
        self._prev_sp = setpoint
        # Dur komutu: integrali sıfırla, motoru bırak
        if setpoint == 0.0 and abs(measurement) < self.stop_eps:
            self._i = 0.0
            self._prev = measurement
            return 0.0

        err = setpoint - measurement
        p = self.kp * err

        raw_d = -(measurement - self._prev) / dt  # ölçüm üzerinden: hedef değişince sıçrama yok
        self._prev = measurement
        self._d = self.d_alpha * raw_d + (1.0 - self.d_alpha) * self._d
        d = self.kd * self._d

        ff = self.kff * (setpoint + self.ff_lead * sp_dot)
        if setpoint > 0:
            ff += self.deadband
        elif setpoint < 0:
            ff -= self.deadband

        i_new = _clamp(self._i + self.ki * err * dt, -self.i_limit, self.i_limit)
        unsat = ff + p + i_new + d
        sat = _clamp(unsat, self.out_min, self.out_max)
        # Koşullu integral: doyumdayken sadece doymadan uzaklaştıran yönde biriktir
        if sat == unsat or (unsat > sat and err < 0) or (unsat < sat and err > 0):
            self._i = i_new
        return _clamp(ff + p + self._i + d, self.out_min, self.out_max)
