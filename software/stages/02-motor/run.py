"""Aşama 2: motor yön ve PWM testi. TEKERLEKLER YERDEN KESİLMİŞ OLMALI."""
import argparse
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))
from arac.config import load_config  # noqa: E402
from arac.factory import close_hardware, make_hardware  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--side", choices=["left", "right", "both"], default="left")
    ap.add_argument("--duty", type=float, default=0.3, help="0..1 (düşük başla)")
    ap.add_argument("--seconds", type=float, default=2.0)
    ap.add_argument("--mock", action="store_true", help="donanımsız deneme")
    a = ap.parse_args()
    if not 0.0 < a.duty <= 0.6:
        sys.exit("Güvenlik: --duty 0 ile 0.6 arasında olmalı")

    sides = ["left", "right"] if a.side == "both" else [a.side]
    cfg = load_config()
    gpio, parts = make_hardware(cfg, sides, a.mock)
    try:
        for label, sign in (("İLERİ", 1), ("GERİ", -1)):
            input(f"\n[Enter] {label} {a.seconds:g} sn, duty={a.duty} ({', '.join(sides)}) ")
            for s in sides:
                parts[s]["motor"].set(sign * a.duty)
            t0 = time.monotonic()
            while time.monotonic() - t0 < a.seconds:
                time.sleep(0.01)
                for p in parts.values():
                    if p["plant"]:
                        p["plant"].step(0.01)
            for s in sides:
                parts[s]["motor"].stop()
            print("durdu")
        print("\nİLERİ komutunda tekerlek ileri dönmediyse config/pins.yaml'da o motorun invert değerini çevir.")
    except KeyboardInterrupt:
        print("\nİptal")
    finally:
        close_hardware(gpio, parts)


if __name__ == "__main__":
    main()
