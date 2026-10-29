"""Aşama 7: duvar takibini robotsuz, simülasyonda dene ve yolu PNG olarak kaydet.
nav.yaml parametrelerini değiştirip etkisini hemen görebilirsin."""
import argparse
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "tests"))
from arac.sim_world import World  # noqa: E402
from helpers import run_follow  # noqa: E402

WORLDS = {
    "oda": (World.rect(0, 0, 5, 4), {"right": (1.0, 0.8, 0.0), "left": (1.0, 3.2, 0.0)}),
    "blok": (World.rect(0, 0, 8, 6) + World.rect(3, 2, 5, 4), {"left": (3.5, 1.6, 0.0), "right": (2.5, 2.6, math.pi / 2)}),
    "koridor": ([(0, 0, 10, 0), (0, 1.4, 10, 1.4), (0, 0, 0, 1.4), (10, 0, 10, 1.4)], {"right": (1.0, 0.7, 0.0), "left": (1.0, 0.7, 0.0)}),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--world", choices=WORLDS, default="oda")
    ap.add_argument("--side", choices=["right", "left"], default="right")
    ap.add_argument("--seconds", type=float, default=80.0)
    ap.add_argument("--out", default="wall_follow_sim.png")
    a = ap.parse_args()

    segs, starts = WORLDS[a.world]
    if a.side not in starts:
        sys.exit(f"'{a.world}' dünyası için --side {' / '.join(starts)} kullan")
    world = World(segs)
    r = run_follow(world, starts[a.side], a.seconds, side=a.side)
    print(f"En yakın duvar mesafesi: {r['min_clear'] * 100:.1f} cm (gövde yarıçapı {r['rr'] * 100:.0f} cm) →",
          "ÇARPMA YOK" if r["min_clear"] > r["rr"] else "ÇARPTI!")
    print("Görülen durumlar:", ", ".join(sorted(r["states"])))
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    fig, ax = plt.subplots(figsize=(7, 6))
    for x1, y1, x2, y2 in segs:
        ax.plot([x1, x2], [y1, y2], "k-", lw=2)
    ax.plot([t[1] for t in r["trace"]], [t[2] for t in r["trace"]], "-", color="tab:blue", lw=1.5, label="robot yolu")
    ax.plot(*starts[a.side][:2], "go", label="başlangıç")
    ax.set_aspect("equal")
    ax.set_title(f"Duvar takibi ({a.side}) — {a.world}")
    ax.legend()
    fig.savefig(a.out, dpi=110, bbox_inches="tight")
    print("Kaydedildi:", a.out)


if __name__ == "__main__":
    main()
