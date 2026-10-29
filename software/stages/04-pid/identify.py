"""Açık çevrim duty basamakları: kff (hız/duty eğimi) ve deadband'i ölçer.
TEKERLEKLER YERDEN KESİLMİŞ OLMALI."""
import argparse
import math
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))
from arac.config import load_config, require_ticks  # noqa: E402
from arac.factory import close_hardware, make_hardware  # noqa: E402

DUTIES = [0.20, 0.30, 0.40, 0.55, 0.70, 0.85]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--side", choices=["left", "right"], required=True)
    ap.add_argument("--settle", type=float, default=1.5)
    ap.add_argument("--measure", type=float, default=1.0)
    ap.add_argument("--mock", action="store_true")
    a = ap.parse_args()

    cfg = load_config()
    ticks = require_ticks(cfg) if not a.mock else (cfg["robot"].get("ticks_per_rev") or 1000)
    gpio, parts = make_hardware(cfg, [a.side], a.mock)
    p = parts[a.side]

    def wait(sec):
        end = time.monotonic() + sec
        while time.monotonic() < end:
            time.sleep(0.01)
            if p["plant"]:
                p["plant"].step(0.01)

    pts = []
    try:
        print("duty   hız(rad/s)   RPM")
        for d in DUTIES:
            p["motor"].set(d)
            wait(a.settle)
            c0, t0 = p["encoder"].count, time.monotonic()
            wait(a.measure)
            c1, t1 = p["encoder"].count, time.monotonic()
            w = (c1 - c0) * 2 * math.pi / ticks / (t1 - t0)
            print(f"{d:.2f}   {w:9.2f}   {w * 60 / (2 * math.pi):6.0f}")
            if w < 0:
                print("Hız NEGATİF: enkoder (veya motor) invert ayarı ters. pins.yaml'ı düzelt.")
                return
            pts.append((d, w))
    finally:
        p["motor"].stop()
        close_hardware(gpio, parts)

    moving = [(d, w) for d, w in pts if w > 1.0]
    if len(moving) < 3:
        print("Yeterli hareket yok; motor/enkoder bağlantısını kontrol et.")
        return
    n = len(moving)
    sx, sy = sum(d for d, _ in moving), sum(w for _, w in moving)
    sxx, sxy = sum(d * d for d, _ in moving), sum(d * w for d, w in moving)
    k = (n * sxy - sx * sy) / (n * sxx - sx * sx)       # rad/s per duty
    b = (sy - k * sx) / n
    print(f"\nModel: hız = {k:.1f} * duty + {b:.1f}")
    print(f"Öneri → config/pid.yaml ({a.side}):  kff: {1 / k:.4f}, deadband: {-b / k:.3f}")


if __name__ == "__main__":
    main()
