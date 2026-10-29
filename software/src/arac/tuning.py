"""Otomatik ayar için saf (donanımsız) fonksiyonlar."""


def fit_line(points):
    n = len(points)
    sx, sy = sum(d for d, _ in points), sum(w for _, w in points)
    sxx, sxy = sum(d * d for d, _ in points), sum(d * w for d, w in points)
    k = (n * sxy - sx * sy) / (n * sxx - sx * sx)
    return k, (sy - k * sx) / n


def model_from_sweep(points, min_speed=1.0):
    """points: [(duty, rad/s)]. Model: hız = K*(duty - deadband). Başarısızsa None."""
    moving = [(d, w) for d, w in points if w > min_speed]
    if len(moving) < 3:
        return None
    k, b = fit_line(moving)
    if k <= 0:
        return None
    return {"K": k, "kff": 1.0 / k, "deadband": max(0.0, -b / k)}


def estimate_tau(t, w, w_ss):
    """Basamak cevabında %63'e erişme süresi (lineer interpolasyonlu). Bulunamazsa None."""
    target = 0.632 * w_ss
    for i in range(1, len(t)):
        if w[i] >= target:
            if w[i] == w[i - 1]:
                return t[i]
            return t[i - 1] + (target - w[i - 1]) * (t[i] - t[i - 1]) / (w[i] - w[i - 1])
    return None


def lambda_gains(K, tau, lam):
    """1. derece sistem için PI (sıfır-kutup sadeleştirme): kapalı çevrim zaman sabiti = lam."""
    return tau / (K * lam), 1.0 / (K * lam)


def moving_average(x, n):
    out = []
    for i in range(len(x)):
        seg = x[max(0, i - n + 1): i + 1]
        out.append(sum(seg) / len(seg))
    return out


def step_metrics(t, w, target, band=0.05):
    w = moving_average(w, 5)
    overshoot = max(0.0, (max(w) / target - 1.0) * 100.0)
    settle = t[0]
    for i in range(len(w) - 1, -1, -1):
        if abs(w[i] - target) > band * target:
            settle = t[min(i + 1, len(t) - 1)]
            break
    tail = w[int(len(w) * 0.75):]
    ss_err = abs(sum(tail) / len(tail) - target) / target * 100.0
    return {"overshoot_pct": overshoot, "settle_s": settle, "ss_err_pct": ss_err}
