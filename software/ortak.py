"""Ortak yardımcılar (sihirbazın bütün bölümleri kullanır)."""
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable
STATE = Path.home() / ".arac_ilerleme.json"
MOCK = "--mock" in sys.argv
ROS_ENV = ("source /opt/ros/jazzy/setup.bash; "
           "[ -f ~/ros2_ws/install/setup.bash ] && source ~/ros2_ws/install/setup.bash; ")


# ---------- yardımcılar ----------
def say(msg="", c=None):
    cols = {"g": 32, "r": 31, "y": 33, "c": 36, "b": 1}
    print(f"\033[{cols[c]}m{msg}\033[0m" if c else msg)


def baslik(t):
    say("\n" + "=" * 64, "c")
    say(" " + t, "c")
    say("=" * 64, "c")


def ask_yn(q, default=None):
    d = {"e": " [E/h]", "h": " [e/H]", None: " [e/h]"}[default]
    while True:
        a = input(f"\n{q}{d}: ").strip().lower()
        if not a and default:
            return default == "e"
        if a in ("e", "evet"):
            return True
        if a in ("h", "hayır", "hayir"):
            return False
        print("Lütfen 'e' (evet) ya da 'h' (hayır) yaz.")


def guvenlik(soru):
    say("\n⚠️  GÜVENLİK", "y")
    return ask_yn(soru + "\n   (Hazır değilsen 'h' de, hiçbir şey çalışmaz.)")


def run(cmd, shell=False):
    """Komutu çalıştırır, çıkış kodu 0 ise True."""
    try:
        return subprocess.run(cmd, cwd=ROOT, shell=shell,
                              executable="/bin/bash" if shell else None).returncode == 0
    except KeyboardInterrupt:
        say("\nDurduruldu (Ctrl+C).", "y")
        return False


def script(*args):
    return run([PY, *map(str, args)])


def mock_arg():
    return ["--mock"] if MOCK else []


def edit_yaml_invert(section, side, value):
    """pins.yaml içinde section (motors|encoders) altındaki side satırının invert değerini ayarlar."""
    f = ROOT / "config" / "pins.yaml"
    lines = f.read_text(encoding="utf-8").splitlines(keepends=True)
    cur = None
    for i, ln in enumerate(lines):
        m = re.match(r"^(\w+):", ln)
        if m:
            cur = m.group(1)
        if cur == section and re.match(rf"^\s+{side}:", ln):
            lines[i] = re.sub(r"invert:\s*(true|false)", f"invert: {'true' if value else 'false'}", ln)
            f.write_text("".join(lines), encoding="utf-8")
            return True
    return False


def get_invert(section, side):
    cur = None
    for ln in (ROOT / "config" / "pins.yaml").read_text(encoding="utf-8").splitlines():
        m = re.match(r"^(\w+):", ln)
        if m:
            cur = m.group(1)
        if cur == section and re.match(rf"^\s+{side}:", ln):
            return "invert: true" in ln
    return False


def set_robot_yaw(deg):
    f = ROOT / "config" / "robot.yaml"
    t = f.read_text(encoding="utf-8")
    f.write_text(re.sub(r"lidar_yaw_deg:\s*[-\d.]+", f"lidar_yaw_deg: {deg}", t), encoding="utf-8")


def load_state():
    try:
        return json.loads(STATE.read_text())
    except Exception:  # noqa: BLE001
        return {"done": []}


def save_state(s):
    try:
        STATE.write_text(json.dumps(s))
    except OSError:
        pass


def tak(basari):
    if basari:
        say("   ✓ Tamam", "g")
    return basari


def sorun(ne):
    say(f"\n✗ {ne}", "r")
    say("   Ne yapmalı:", "b")
    say("   1) Yukarıdaki hata satırlarını oku; çoğu ne yapılacağını söyler.")
    say("   2) Düzelttiysen aynı komutu yeniden çalıştır:  arac  (kaldığın adımdan devam eder)")
    say("   3) Çözemezsen:  python3 tools/diag.py  → diag_rapor.txt dosyasını öğretmene gönder.")
    say("      (Ayrıntılı kontrol listesi: arac acil → Bölüm B)")
    return False




# ---------- ölçüm kaydı ----------
OLCUM = Path.home() / ".arac_olcumler.json"


def olcum_kaydet(ad, deger):
    try:
        d = json.loads(OLCUM.read_text())
    except Exception:  # noqa: BLE001
        d = {}
    d[ad] = deger
    try:
        OLCUM.write_text(json.dumps(d, ensure_ascii=False, indent=1))
    except OSError:
        pass


def ask_float(soru, lo, hi, ad, ipucu):
    """Sayı sorar; aralık dışıysa ne yapılacağını söyler ve tekrar sorar. Değeri deftere kaydeder."""
    while True:
        a = input(f"\n{soru} (sayı yaz, örn. 5,02): ").strip().replace(",", ".")
        try:
            v = float(a)
        except ValueError:
            print("Lütfen sadece sayı yaz (virgül ya da nokta olur).")
            continue
        if lo <= v <= hi:
            olcum_kaydet(ad, v)
            say(f"   ✓ {v} V uygun ({lo}–{hi} V)", "g")
            return v
        say(f"   ✗ {v} V uygun DEĞİL (olması gereken {lo}–{hi} V). {ipucu}", "r")
        if ask_yn("Ayarladın, yeniden ölçelim mi? ('h' = bu adımı durdur)", "e"):
            continue
        return None
