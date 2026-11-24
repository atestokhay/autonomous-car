#!/usr/bin/env python3
"""Aşama 6: BNO055 gyro kontrolü. MOTORLAR ÇALIŞMAZ.
  python3 stages/06-odometri/check_imu.py        -> canlı açı ve kalibrasyon durumu (Ctrl+C ile çık)
  python3 stages/06-odometri/check_imu.py yon    -> aracı elle 90° SOLA çevir; ters ölçerse pins.yaml'ı düzeltir
Çıkış kodu: 0 = tamam, 1 = BNO055 bulunamadı/okunamadı (odometri yine enkoderle çalışır), 2 = yön/açı yanlış."""
import argparse
import math
import pathlib
import re
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))
from arac.config import CONFIG_DIR, load_config  # noqa: E402
from arac.imu import open_imu  # noqa: E402

PINS = CONFIG_DIR / "pins.yaml"


def set_yaw_invert(value):
    t = PINS.read_text(encoding="utf-8")
    t2, n = re.subn(r"^(\s+yaw_invert:\s*)(true|false)", rf"\g<1>{'true' if value else 'false'}", t, flags=re.M)
    if n != 1:
        return False
    PINS.write_text(t2, encoding="utf-8")
    return True


def live(imu):
    print("Aracı elle çevir; açı değişmeli. Çıkmak için Ctrl+C.\n(gyro kalibrasyonu 3 olmalı: aracı 2-3 sn kıpırdatmadan bekletince olur)")
    try:
        while True:
            s, g, a, m = imu.calibration()
            print(f"\r  açı: {math.degrees(imu.yaw()):7.1f}°   kalibrasyon sistem/gyro/ivme: {s}/{g}/{a}   ", end="", flush=True)
            time.sleep(0.1)
    except KeyboardInterrupt:
        print()
    return 0


def yon(imu, invert_now):
    input("Aracı yere koy, KIPIRDATMADAN [Enter]'a bas (gyro 2 sn kendini sıfırlar) ")
    time.sleep(2.0)
    a0 = imu.yaw()
    input("Şimdi aracı yerinde elle yaklaşık 90° SOLA (saat yönünün TERSİNE) çevir, durunca [Enter] ")
    d = math.degrees((imu.yaw() - a0 + math.pi) % (2 * math.pi) - math.pi)
    print(f"Ölçülen dönüş: {d:+.1f}°  (yaklaşık +90 beklenir)")
    if 45.0 <= d <= 135.0:
        print("✓ BNO055 yönü doğru.")
        return 0
    if -135.0 <= d <= -45.0:
        if set_yaw_invert(not invert_now):
            print(f"Yön ters çıktı → pins.yaml: imu.yaw_invert: {'true' if not invert_now else 'false'} yazıldı. "
                  "Testi bir kez daha çalıştır.")
        else:
            print("Yön ters çıktı: pins.yaml'da imu.yaw_invert değerini elle çevir.")
        return 2
    print("Açı ±90°'ye yakın değil: aracı gerçekten ~90° çevirdin mi? BNO055 sıkı sabit mi? Tekrar dene.")
    return 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", nargs="?", default="live", choices=["live", "yon"])
    ap.add_argument("--mock", action="store_true")
    a = ap.parse_args()
    if a.mock:
        print("(deneme modu: BNO055 yok, kontrol atlandı)")
        return 0
    cfg = load_config()
    cfg["pins"].setdefault("imu", {})["use_for_heading"] = True   # kontrol için IMU'yu her durumda aç
    imu, msg = open_imu(cfg)
    print(msg)
    if imu is None:
        print("Kontrol et: SDA pin 3, SCL pin 5, VIN 3,3 V, GND; `i2cdetect -y 1` çıktısında 28 görünmeli.\n"
              "IMU olmadan da odometri çalışır (açı enkoderden).")
        return 1
    try:
        return live(imu) if a.mode == "live" else yon(imu, bool(cfg["pins"]["imu"].get("yaw_invert", False)))
    except Exception as e:  # noqa: BLE001  (lgpio.error OSError değildir)
        print(f"BNO055 okuma hatası: {e}  (kablolar gevşek mi? notes/sorun-giderme.md → Aşama 6)")
        return 1
    finally:
        imu.close()


if __name__ == "__main__":
    sys.exit(main())
