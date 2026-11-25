"""Aşama 9: şerit ortalama denetleyicisini (src/arac/lane_follow.py) yarışma pistinde robotsuz dene.
Pist: Fibonacci Autonomous Car şartnamesi Şekil AC-2 (2100 x 2490 mm, şerit ~600 mm, saat yönünün tersine).
Parametreler config/nav.yaml -> lane_follow. Örnek:
    python stages/09-serit-ortalama/sim_pist.py --robots 3 --out ."""
import argparse
import math
import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))
from arac.config import load_config  # noqa: E402
from arac.lane_follow import LaneFollower  # noqa: E402
from arac.scan import ScanView  # noqa: E402
from arac.sim_world import SimRobot, World  # noqa: E402

W, H = 2.10, 2.49
WALLS = World.rect(0, 0, W, H) + [(0.60, 0.60, 0.60, 1.89), (0.60, 1.89, 1.446, 1.89),
                                  (0.60, 0.60, 1.446, 0.60), (1.254, 1.245, W, 1.245)]
START_Y = 1.245


def box(x, y, th, L=0.20, Wd=0.15):
    c, s = math.cos(th), math.sin(th)
    pts = [(x + c * dx - s * dy, y + s * dx + c * dy) for dx, dy in
           [(L/2, Wd/2), (-L/2, Wd/2), (-L/2, -Wd/2), (L/2, -Wd/2)]]
    return [(*pts[i], *pts[(i + 1) % 4]) for i in range(4)]


def _corners(r, L=0.20, Wd=0.15):
    c, s = math.cos(r.th), math.sin(r.th)
    return [(r.x + c * dx - s * dy, r.y + s * dx + c * dy) for dx, dy in
            [(L/2, Wd/2), (-L/2, Wd/2), (-L/2, -Wd/2), (L/2, -Wd/2)]]


def boxes_touch(a, b):
    """İki 20x15 cm gövde temas ediyor mu (ayırıcı eksen testi)."""
    pa, pb = _corners(a), _corners(b)
    for poly in (pa, pb):
        for i in range(4):
            x1, y1 = poly[i]; x2, y2 = poly[(i + 1) % 4]
            nx, ny = y1 - y2, x2 - x1
            A = [nx * x + ny * y for x, y in pa]; B = [nx * x + ny * y for x, y in pb]
            if max(A) < min(B) or max(B) < min(A):
                return False
    return True


def sim(name, starts, seconds=180.0, rr=0.125, v_max=None, seed=1, out=None, params=None):
    """params: robot başına nav.yaml lane_follow üzerine yazılacak ayarlar listesi (ör. rakibe düşük hız)."""
    rng = random.Random(seed)
    cfg = load_config()
    p = dict(cfg["nav"]["lane_follow"])
    if v_max:
        p["v_max"] = v_max
    bots = []
    for k, st in enumerate(starts):
        pk = dict(p)
        if params and k < len(params) and params[k]:
            pk.update(params[k])
        bots.append((SimRobot(*st), LaneFollower(pk, rr)))
    contact = 0
    cmds = [(0.0, 0.0)] * len(bots)
    traces = [[] for _ in bots]; laps = [0] * len(bots); back = [0] * len(bots)
    min_clear = [math.inf] * len(bots); bump = [0] * len(bots); prev = [None] * len(bots)
    dt, t = 0.01, 0.0
    rr_min = math.inf
    for i in range(int(seconds / dt)):
        if t >= 5.0 and i % 10 == 0:             # 5 sn bekleme (AC-3.2), 10 Hz LiDAR
            for k, (rob, f) in enumerate(bots):
                others = sum((box(o.x, o.y, o.th) for j, (o, _) in enumerate(bots) if j != k), [])
                world = World(WALLS + others)
                r, amin, inc = world.scan(rob.x, rob.y, rob.th, n=720, noise=0.01, dropout=0.03, rng=rng)
                cmds[k] = f.step(ScanView(r, amin, inc), 0.1)
        for k, (rob, f) in enumerate(bots):
            rob.step(*cmds[k], dt)
            c = World(WALLS).clearance(rob.x, rob.y)
            min_clear[k] = min(min_clear[k], c)
            if c < rr:
                bump[k] += 1
            if prev[k] and rob.x < 0.6:
                if prev[k][1] >= START_Y > rob.y:
                    laps[k] += 1
                elif prev[k][1] < START_Y <= rob.y:
                    back[k] += 1
            prev[k] = (rob.x, rob.y)
            if i % 10 == 0:
                traces[k].append((rob.x, rob.y))
        for a in range(len(bots)):
            for b in range(a + 1, len(bots)):
                ra, rb = bots[a][0], bots[b][0]
                rr_min = min(rr_min, math.hypot(ra.x - rb.x, ra.y - rb.y))
                if boxes_touch(ra, rb):
                    contact += 1
        t += dt
    res = {"laps": laps, "back": back, "min_clear": min_clear, "bump_s": [b * dt for b in bump], "rr_min": rr_min,
           "contact_s": contact * dt}
    for k in range(len(bots)):
        print(f"{name} robot{k+1}: lap={laps[k]}  ters_gecis={back[k]}  en_yakin_duvar={min_clear[k]*100:.1f} cm "
              f"(govde {rr*100:.1f} cm)  duvar_temas_suresi={bump[k]*dt:.1f} s")
    if len(bots) > 1:
        print(f"{name}: robotlar arasi en kucuk merkez mesafesi={rr_min*100:.1f} cm, robot-robot temas suresi={contact*dt:.1f} s")
    if out is None:                      # testlerde grafik yazma
        return res
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return res
    fig, ax = plt.subplots(figsize=(6, 7))
    for x1, y1, x2, y2 in WALLS:
        ax.plot([x1, x2], [y1, y2], "k-", lw=2)
    ax.plot([0, 0.6], [START_Y, START_Y], "r-", lw=2, label="lap cizgisi")
    for k, tr in enumerate(traces):
        ax.plot([q[0] for q in tr], [q[1] for q in tr], "-", lw=0.8, label=f"robot{k+1}: {laps[k]} lap")
    ax.set_aspect("equal"); ax.legend(loc="upper right", fontsize=7)
    ax.set_title(f"Serit ortalama - {name} (3 dk)")
    fig.savefig(pathlib.Path(out or ".") / f"serit-{name}.png", dpi=100, bbox_inches="tight"); plt.close(fig)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--robots", type=int, choices=[1, 2, 3], default=1, help="pistte kaç robot")
    ap.add_argument("--seconds", type=float, default=180.0)
    ap.add_argument("--out", default=".", help="grafiğin kaydedileceği klasör")
    a = ap.parse_args()
    down = -math.pi / 2
    starts = [(0.30, 1.35, down), (0.15, 1.60, down), (0.45, 1.60, down)][:a.robots]
    r = sim(f"{a.robots}-robot", starts, a.seconds, out=a.out)
    print("Not: ilk çizgi geçişi başlangıçtır; gerçek lap sayısı = lap - 1.")
    return r


if __name__ == "__main__":
    main()
