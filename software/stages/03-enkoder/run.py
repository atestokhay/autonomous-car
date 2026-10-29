"""Aşama 3: enkoder okuma. Modlar: watch | calibrate | drive"""
import argparse
import math
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))
from arac.config import load_config  # noqa: E402
from arac.factory import close_hardware, make_hardware  # noqa: E402


def watch(parts, sides):
    print("Tekerleği ELLE İLERİ yönde çevir: sayı ARTMALI. Azalıyorsa pins.yaml'da encoder invert'i çevir.")
    print("'eksik' sürekli artıyorsa kenar kaçıyor demektir (kablo/gürültü). Çıkış: Ctrl+C\n")
    while True:
        print("  ".join(f"{s}: {parts[s]['encoder'].count:>8d} (eksik {parts[s]['encoder'].missed})"
                        for s in sides), end="\r")
        time.sleep(0.1)


def calibrate(parts, side, turns):
    enc = parts[side]["encoder"]
    input(f"Tekerleği bir işaretle. İşaret başlangıçta, [Enter]'a bas: ")
    c0 = enc.count
    input(f"Şimdi tekerleği TAM {turns} tur ileri çevir, işaret yine başlangıç konumunda, [Enter]'a bas: ")
    c1 = enc.count
    tpr = (c1 - c0) / turns
    print(f"\nÖlçülen: {c1 - c0} tick / {turns} tur = {tpr:.1f} tick/tur")
    print(f"config/robot.yaml → ticks_per_rev: {round(tpr)}")
    if tpr <= 0:
        print("UYARI: sayı negatif/sıfır; enkoder invert ayarını kontrol et.")


def drive(parts, sides, duty, seconds, ticks, mock):
    print(f"duty={duty}, tick hızı ve kaçan kenar izleniyor (tekerlekler havada!)\n")
    for s in sides:
        parts[s]["motor"].set(duty)
    last = {s: parts[s]["encoder"].count for s in sides}
    t_end = time.monotonic() + seconds
    while time.monotonic() < t_end:
        for _ in range(50):  # 0.5 sn, mock modelde 10 ms adımlarla
            time.sleep(0.01)
            for s in sides:
                if parts[s]["plant"]:
                    parts[s]["plant"].step(0.01)
        for s in sides:
            c = parts[s]["encoder"].count
            tps = (c - last[s]) / 0.5
            last[s] = c
            extra = f", {tps / ticks * 60:.0f} RPM" if ticks else ""
            print(f"{s}: {tps:9.0f} tick/s{extra}, eksik={parts[s]['encoder'].missed}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["watch", "calibrate", "drive"])
    ap.add_argument("--side", choices=["left", "right", "both"], default="both")
    ap.add_argument("--turns", type=int, default=10)
    ap.add_argument("--duty", type=float, default=0.5)
    ap.add_argument("--seconds", type=float, default=5.0)
    ap.add_argument("--mock", action="store_true")
    a = ap.parse_args()
    if a.mode == "calibrate" and a.side == "both":
        a.side = "left"
    if a.mode == "drive" and not 0.0 < a.duty <= 0.8:
        sys.exit("Güvenlik: --duty 0 ile 0.8 arasında olmalı")

    sides = ["left", "right"] if a.side == "both" else [a.side]
    cfg = load_config()
    gpio, parts = make_hardware(cfg, sides, a.mock)
    try:
        if a.mode == "watch":
            watch(parts, sides)
        elif a.mode == "calibrate":
            calibrate(parts, a.side, a.turns)
        else:
            drive(parts, sides, a.duty, a.seconds, cfg["robot"].get("ticks_per_rev"), a.mock)
    except KeyboardInterrupt:
        print("\nÇıkış")
    finally:
        close_hardware(gpio, parts)


if __name__ == "__main__":
    main()
