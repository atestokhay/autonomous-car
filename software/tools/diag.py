#!/usr/bin/env python3
"""Teşhis raporu: motoru HAREKET ETTİRMEZ, sadece sistem durumunu toplar.
  python3 tools/diag.py            -> ekrana yazar ve diag_rapor.txt dosyasına kaydeder
Çıktıyı öğretmene gönder."""
import datetime
import importlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
out = []


def say(s=""):
    print(s)
    out.append(s)


def run(cmd, title=None, tail=None):
    say(f"\n=== {title or cmd} ===")
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        txt = (r.stdout + r.stderr).strip() or "(çıktı yok)"
        if tail:
            txt = "\n".join(txt.splitlines()[-tail:])
        say(txt)
    except Exception as e:  # noqa: BLE001
        say(f"HATA: {e}")


say(f"Teşhis raporu {datetime.datetime.now():%Y-%m-%d %H:%M:%S}")
run("uname -a", "Çekirdek")
run("grep PRETTY_NAME /etc/os-release", "İşletim sistemi (Ubuntu 24.04 olmalı)")
run("cat /proc/device-tree/model; echo", "Cihaz (Raspberry Pi 5 olmalı)")
run("id", "Kullanıcı ve gruplar (dialout ve gpio olmalı)")
run("vcgencmd get_throttled", "Güç (0x0 olmalı)")
run("dmesg 2>&1 | grep -i -E 'under-?volt|throttl|usb.*(disconnect|reset)|ttyUSB' | tail -15",
    "Çekirdek uyarıları (voltaj/USB)")
run("gpiodetect", "GPIO çipleri (pinctrl-rp1 olmalı)")
run("ls -l /dev/gpiochip*", "GPIO aygıt izinleri")
run("ls -l /dev/ttyUSB* /dev/ttyACM* 2>&1; lsusb", "USB / seri aygıtlar (LiDAR adaptörü)")

say("\n=== Python modülleri ===")
for m in ("yaml", "numpy", "serial", "lgpio", "matplotlib"):
    try:
        importlib.import_module(m)
        say(f"  {m}: var")
    except Exception as e:  # noqa: BLE001
        say(f"  {m}: YOK ({e.__class__.__name__})")

say("\n=== ROS 2 ===")
say(f"  ros2 komutu: {'var' if shutil.which('ros2') else 'YOK (source /opt/ros/jazzy/setup.bash?)'}")
say(f"  ROS_DISTRO={os.environ.get('ROS_DISTRO')} ROS_DOMAIN_ID={os.environ.get('ROS_DOMAIN_ID')}")
if shutil.which("ros2"):
    run("ros2 pkg executables sllidar_ros2", "sllidar_ros2 (sllidar_node görünmeli)")
    run("ros2 topic list", "Topic'ler")

say("\n=== Yapılandırma dosyaları ===")
for name in ("pins", "robot", "robot_cal", "pid", "tuned", "nav"):
    f = ROOT / "config" / f"{name}.yaml"
    say(f"\n--- {name}.yaml {'(VAR)' if f.exists() else '(yok)'} ---")
    if f.exists() and name in ("pins", "robot", "robot_cal", "tuned"):
        say(f.read_text(encoding="utf-8"))

say("\n=== Testler ===")
r = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=ROOT,
                   capture_output=True, text=True, timeout=300)
say("\n".join((r.stdout + r.stderr).strip().splitlines()[-8:]))

(ROOT / "diag_rapor.txt").write_text("\n".join(out), encoding="utf-8")
print(f"\nKaydedildi: {ROOT / 'diag_rapor.txt'}  <- bu dosyayı gönder")
