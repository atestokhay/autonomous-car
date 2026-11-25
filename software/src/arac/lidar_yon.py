"""LiDAR'ın araca göre yönünü, kısa bir İLERİ hareketten önce/sonra alınan iki taramadan bulur.
Saf Python; ROS gerektirmez.

Fikir: araç d metre ileri gidince aracın ÖNÜNDEKİ noktalar d kadar yaklaşır, ARKASINDAKİLER d kadar uzaklaşır.
LiDAR çerçevesinde bu farkın en negatif olduğu yön = aracın önü. Ayrıca iki tarama arasındaki açısal kayma,
aracın düz gitmek yerine döndüğünü (bir motorun ters bağlı olduğunu) gösterir.
"""
import math


def _bins(ranges, angle_min, angle_inc, n=360, rmin=0.05, rmax=12.0):
    """Taramayı 1°'lik kutulara böler; her kutu geçerli mesafelerin medyanı (yoksa None)."""
    buckets = [[] for _ in range(n)]
    for i, r in enumerate(ranges):
        if not (r == r) or r < rmin or r > rmax:
            continue
        a = math.degrees(angle_min + i * angle_inc) % 360.0
        buckets[int(a) % n].append(r)
    out = []
    for b in buckets:
        b.sort()
        out.append(b[len(b) // 2] if b else None)
    return out


def _window(prof, center, half):
    vals = [prof[(center + k) % len(prof)] for k in range(-half, half + 1)]
    vals = sorted(v for v in vals if v is not None)
    return vals[len(vals) // 2] if vals else None


def rotation_deg(before, after, max_shift=60):
    """after taramasının before'a göre açısal kayması (derece) ve uyum hatası (m)."""
    best = (0, math.inf)
    for s in range(-max_shift, max_shift + 1):
        diffs = [abs(after[(i + s) % 360] - before[i]) for i in range(360)
                 if before[i] is not None and after[(i + s) % 360] is not None]
        if len(diffs) < 60:
            continue
        diffs.sort()
        err = diffs[len(diffs) // 2]
        if err < best[1]:
            best = (s, err)
    return best


def find_front(before_scan, after_scan, half=15):
    """before/after_scan: (ranges, angle_min, angle_inc).
    Döner: dict(front_deg, yaw_deg, move_m, rot_deg). yaw_deg = robot.yaml lidar_yaw_deg değeri.
    """
    a, b = _bins(*before_scan), _bins(*after_scan)
    rot, _ = rotation_deg(a, b)
    scores = []
    for c in range(0, 360, 5):
        f0, f1 = _window(a, c, half), _window(b, c, half)
        r0, r1 = _window(a, c + 180, half), _window(b, c + 180, half)
        if None in (f0, f1, r0, r1):
            continue
        # önde yaklaşma (negatif) ve arkada uzaklaşma (pozitif) birlikte en büyükse o yön ön
        scores.append(((f1 - f0) - (r1 - r0), c, (f0 - f1 + r1 - r0) / 2))
    if not scores:
        raise RuntimeError("Taramada yeterli nokta yok (LiDAR çevreyi görmüyor).")
    score, front, move = min(scores)
    yaw = -front if front <= 180 else 360 - front
    return {"front_deg": front, "yaw_deg": float(round(yaw / 5) * 5), "move_m": move, "rot_deg": rot}
