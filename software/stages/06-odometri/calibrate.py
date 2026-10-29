"""Aşama 6: odometri kalibrasyonu. MOTORLAR ÇALIŞMAZ: aracı ELLE itersin, enkoder sayımları okunur.
Modlar: live | radius | base"""
import argparse
import math
import pathlib
import sys
import time

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))
from arac import calibration  # noqa: E402
from arac.config import CONFIG_DIR, load_config, require_ticks  # noqa: E402
from arac.factory import close_hardware, make_hardware  # noqa: E402
from arac.kinematics import Kinematics, Odometry  # noqa: E402

CAL = CONFIG_DIR / "robot_cal.yaml"


def counts(parts):
    return parts["left"]["encoder"].count, parts["right"]["encoder"].count


def save(key, value):
    data = yaml.safe_load(open(CAL, encoding="utf-8")) if CAL.exists() else {}
    data = data or {}
    data[key] = round(float(value), 5)
    with open(CAL, "w", encoding="utf-8") as f:
        f.write("# stages/06-odometri/calibrate.py çıktısı; robot.yaml'ın üstüne biner. Silersen robot.yaml değerleri kalır.\n")
        yaml.safe_dump(data, f, sort_keys=False)
    print(f"Yazıldı: {CAL}  ({key}: {data[key]})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["live", "radius", "base"])
    ap.add_argument("--distance", type=float, default=1.0, help="radius: itilen gerçek mesafe (m)")
    ap.add_argument("--turns", type=float, default=3.0, help="base: yerinde çevrilen tam tur sayısı")
    ap.add_argument("--mock", action="store_true")
    a = ap.parse_args()

    cfg = load_config()
    ticks = (cfg["robot"].get("ticks_per_rev") or 392) if a.mock else require_ticks(cfg)
    gpio, parts = make_hardware(cfg, ["left", "right"], a.mock)
    try:
        if a.mode == "radius":
            input(f"Aracı düz bir çizgi başına koy, [Enter]'a bas ve tam {a.distance} m ELLE DÜZ it ")
            c0 = counts(parts)
            input(f"Şimdi aracı {a.distance} m düz it (cetvel/şerit metre), durunca [Enter] ")
            c1 = counts(parts)
            dl, dr = c1[0] - c0[0], c1[1] - c0[1]
            print(f"Sayım: sol {dl}, sağ {dr}")
            if min(dl, dr) <= 0:
                sys.exit("Sayımlardan biri ≤ 0: ileri itince sayı artmalı (pins.yaml encoder invert) ya da araç düz gitmedi.")
            if abs(dl - dr) > 0.05 * max(dl, dr):
                print("UYARI: iki tekerlek %5'ten fazla farklı sayıyor: araç yan kaydı ya da enkoderlerden biri sorunlu.")
            r = calibration.wheel_radius_from_push(a.distance, dl, dr, ticks)
            print(f"Tekerlek yarıçapı ≈ {r * 1000:.1f} mm")
            if input("robot_cal.yaml'a yazılsın mı? [e/H] ").lower() == "e":
                save("wheel_radius_m", r)
        elif a.mode == "base":
            r = cfg["robot"].get("wheel_radius_m")
            if not r:
                sys.exit("Önce `radius` modunu çalıştır ya da robot.yaml'a wheel_radius_m yaz.")
            input(f"Aracı zemine bir işaretle hizala, [Enter]. Sonra aracı YERİNDE tam {a.turns:g} tur çevir ")
            c0 = counts(parts)
            input(f"Aracı {a.turns:g} tur (işaret yine aynı yönde) çevirince [Enter] ")
            c1 = counts(parts)
            dl, dr = c1[0] - c0[0], c1[1] - c0[1]
            print(f"Sayım: sol {dl}, sağ {dr}  (yerinde dönüşte biri artı, diğeri eksi olmalı)")
            if dl * dr >= 0:
                sys.exit("Tekerlekler zıt yönde saymadı: araç yerinde dönmedi ya da enkoder yönü yanlış.")
            b = calibration.wheel_base_from_spin(a.turns * 2 * math.pi, dl, dr, ticks, r)
            print(f"Tekerlekler arası mesafe ≈ {b * 1000:.1f} mm")
            if input("robot_cal.yaml'a yazılsın mı? [e/H] ").lower() == "e":
                save("wheel_base_m", b)
        else:
            r, b = cfg["robot"].get("wheel_radius_m"), cfg["robot"].get("wheel_base_m")
            if not r or not b:
                sys.exit("robot.yaml'da wheel_radius_m / wheel_base_m boş. Önce `radius` ve `base` modları.")
            odom = Odometry(Kinematics(r, b), ticks)
            odom.reset_counts(*counts(parts))
            print("Aracı elle it/çevir; x,y (m) ve açı (derece) canlı. Çıkış: Ctrl+C\n")
            th_total, last_th = 0.0, 0.0
            while True:
                x, y, th = odom.update(*counts(parts))
                d = (th - last_th + math.pi) % (2 * math.pi) - math.pi
                th_total, last_th = th_total + d, th
                print(f"x={x:7.3f}  y={y:7.3f}  açı={math.degrees(th_total):8.1f}°", end="\r")
                time.sleep(0.05)
    except KeyboardInterrupt:
        print("\nÇıkış")
    finally:
        close_hardware(gpio, parts)


if __name__ == "__main__":
    main()
