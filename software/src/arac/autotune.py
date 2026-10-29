"""Otomatik ayar: açık çevrim süpürme (kff, deadband) + basamak cevabı (zaman sabiti)
+ model tabanlı PI hesabı + kapalı çevrim doğrulama. Kullanıcıdan ölçüm girişi gerektirmez."""
import math
import time

from . import tuning
from .loop import RateLoop
from .pid import PID
from .wheel import WheelSpeedController

SWEEP = (0.25, 0.40, 0.55, 0.70, 0.85)
TWO_PI = 2.0 * math.pi


class Rig:
    """Zamanı ve (varsa) simülasyon modelini ilerleten düzenek. virtual=True: uyumadan hızlı sim."""

    def __init__(self, motor, encoder, plant=None, hz=100, virtual=False):
        self.motor, self.encoder, self.plant = motor, encoder, plant
        self.virtual, self.dt0, self.hz, self.t = virtual, 1.0 / hz, hz, 0.0
        self.loop = None if virtual else RateLoop(hz)

    def resync(self):
        if not self.virtual:
            self.loop = RateLoop(self.hz)

    def tick(self):
        dt = self.dt0 if self.virtual else self.loop.wait()
        if self.plant:
            self.plant.step(dt)
        self.t += dt
        return dt

    def run(self, seconds):
        end = self.t + seconds
        while self.t < end:
            self.tick()


def sweep(rig, ticks, log):
    pts = []
    for d in SWEEP:
        rig.motor.set(d)
        rig.run(1.2)
        c0, t0 = rig.encoder.count, rig.t
        rig.run(0.8)
        w = (rig.encoder.count - c0) * TWO_PI / ticks / (rig.t - t0)
        log(f"  duty {d:.2f}: {w:6.1f} rad/s  ({w * 60 / TWO_PI:5.0f} RPM)")
        if w < -1.0:
            rig.motor.stop()
            raise RuntimeError("Hız NEGATİF: pins.yaml'da bu tarafın encoder (veya motor) invert değerini çevir")
        pts.append((d, w))
    rig.motor.stop()
    rig.run(1.0)
    return pts


def step_response(rig, ticks, duty, duration=1.5, win=3):
    rig.motor.stop()
    rig.run(1.0)
    rig.resync()
    t, pos, t0 = [], [], rig.t
    rig.motor.set(duty)
    while rig.t - t0 < duration:
        rig.tick()
        t.append(rig.t - t0)
        pos.append(rig.encoder.count)
    rig.motor.stop()
    ws, ts = [], []
    for i in range(win, len(t)):
        span = t[i] - t[i - win]
        ws.append((pos[i] - pos[i - win]) * TWO_PI / ticks / span)
        ts.append(t[i] - span / 2)       # pencere ortası
    tail = ws[int(len(ws) * 0.75):]
    w_ss = sum(tail) / len(tail)
    return tuning.estimate_tau(ts, ws, w_ss), w_ss


def validate(rig, ticks, params, pc, target, hold):
    ctrl = WheelSpeedController(rig.motor, rig.encoder, PID(**params), ticks,
                                pc["speed_alpha"], pc["max_accel_rad_s2"], pc.get("speed_window", 4))
    rig.motor.stop()
    rig.run(1.0)
    rig.resync()
    ctrl.reset()
    t, w, t0 = [], [], rig.t
    ctrl.set_target(target)
    try:
        while rig.t - t0 < hold:
            ctrl.update(rig.tick())
            t.append(rig.t - t0)
            w.append(ctrl.speed)
    finally:
        ctrl.stop()
    return tuning.step_metrics(t, w, target)


def passed(m, hold):
    return m["overshoot_pct"] <= 8.0 and m["ss_err_pct"] <= 3.0 and m["settle_s"] <= 0.6 * hold


def autotune_side(rig, ticks, pc, log=print, hold=2.5, lam_factor=2.5, lam_min=0.18, max_tries=3):
    log("1/3 Açık çevrim süpürme (kff, ölü bölge)")
    pts = sweep(rig, ticks, log)
    model = tuning.model_from_sweep(pts)
    if model is None:
        raise RuntimeError("Model çıkarılamadı: motor dönmüyor veya enkoder saymıyor (bağlantıyı kontrol et)")
    warnings = []
    rpm_hi = pts[-1][1] * 60 / TWO_PI
    if not 150 <= rpm_hi <= 450:
        warnings.append(f"duty 0.85'te {rpm_hi:.0f} RPM: beklenen ~250-380. "
                        "ticks_per_rev (robot.yaml) veya enkoder çözümü yanlış olabilir.")
    log("2/3 Basamak cevabı (zaman sabiti)")
    tau, w_ss = step_response(rig, ticks, 0.6)
    if tau is None:
        raise RuntimeError("Zaman sabiti ölçülemedi")
    tau = max(tau, 0.02)
    log(f"  K={model['K']:.1f} rad/s/duty, ölü bölge={model['deadband']:.3f}, tau={tau * 1e3:.0f} ms")

    log("3/3 PI hesabı ve kapalı çevrim doğrulama")
    target = min(15.0, 0.5 * pts[-1][1])
    lam = max(lam_factor * tau, lam_min)
    for attempt in range(1, max_tries + 1):
        kp, ki = tuning.lambda_gains(model["K"], tau, lam)
        params = dict(kp=kp, ki=ki, kd=0.0, kff=model["kff"], deadband=model["deadband"],
                      i_limit=0.5, d_alpha=0.2, ff_lead=tau)
        m = validate(rig, ticks, params, pc, target, hold)
        ok = passed(m, hold)
        log(f"  deneme {attempt}: kp={kp:.4f} ki={ki:.3f} → aşım %{m['overshoot_pct']:.1f}, "
            f"oturma {m['settle_s']:.2f}s, kalıcı hata %{m['ss_err_pct']:.1f} → {'GEÇTİ' if ok else 'kaldı'}")
        if ok:
            return {"params": {k: round(v, 5) for k, v in params.items()},
                    "metrics": {k: round(v, 3) for k, v in m.items()},
                    "model": {"K": round(model["K"], 2), "tau_s": round(tau, 4)},
                    "warnings": warnings}
        lam *= 1.6   # daha yavaş/yumuşak ayar dene
    raise RuntimeError("Doğrulama geçmedi: ayar yazılmadı, mevcut pid.yaml değerleri korunuyor")
