#!/usr/bin/env python3
"""Başlat butonu: butona basılınca 5 sn (pins.yaml → start_button.delay_s) sonra duvar takibini başlatır.
  Geri sayımda tekrar basılırsa İPTAL; program çalışırken basılırsa program DURUR (araç durur).
Buton: GPIO16 (pin 36) ile GND (pin 34) arasına, ikinci kablo/direnç yok (Pi dahili pull-up).

  python3 tools/baslat_butonu.py          -> butonu bekler (Pi açılınca otomatik için: tools/buton_servis_kur.sh)
  python3 tools/baslat_butonu.py test     -> kablolama testi: sadece basışları gösterir, hiçbir şey başlatmaz
  python3 tools/baslat_butonu.py --mock   -> donanımsız deneme: [Enter] = butona bas, sahte program başlar
Bu betik sadece buton pinini kullanır; motor/enkoder pinlerine dokunmaz."""
import argparse
import os
import pathlib
import signal
import subprocess
import sys
import threading
import time

SOFTWARE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOFTWARE / "src"))
from arac.config import load_config  # noqa: E402
from arac.gpio_backend import LgpioBackend, MockBackend, resolve_gpiochip  # noqa: E402
from arac.start_button import Debouncer, StartController  # noqa: E402

ROS_ENV = ("source /opt/ros/jazzy/setup.bash; "
           "[ -f ~/ros2_ws/install/setup.bash ] && source ~/ros2_ws/install/setup.bash; ")
POLL_S = 0.01


def log(text):
    print(time.strftime("%H:%M:%S ") + text, flush=True)


class Program:
    """ros2 launch sürecini kendi süreç grubunda başlatır/durdurur (Ctrl+C gibi: motorlar güvenle durur)."""

    def __init__(self, cmd):
        self.cmd, self.p = cmd, None

    def start(self):
        self.p = subprocess.Popen(["bash", "-c", self.cmd], cwd=SOFTWARE, start_new_session=True)

    def running(self):
        return self.p is not None and self.p.poll() is None

    def stop(self):
        if not self.running():
            return
        for sig, wait_s in ((signal.SIGINT, 15), (signal.SIGTERM, 5), (signal.SIGKILL, 5)):
            try:
                os.killpg(self.p.pid, sig)
            except ProcessLookupError:
                return
            try:
                self.p.wait(timeout=wait_s)
                return
            except subprocess.TimeoutExpired:
                log(f"Program {wait_s} sn'de kapanmadı, daha sert durduruluyor...")


def build_command(sb, mock):
    if mock:
        return ("exec python3 -c \"import time; print('(deneme) program çalışıyor', flush=True); "
                "time.sleep(3600)\"")
    side = sb.get("side") or "right"
    v_scale = float(sb.get("v_scale", 0.5))
    # Geri sayım bu betikte yapıldı: düğümün kendi geri sayımı 0.
    return (ROS_ENV + "exec ros2 launch ros/launch/wall_follow.launch.py "
            f"side:={side} v_scale:={v_scale} countdown:=0")


def mock_keyboard(gpio, pin):
    def loop():
        for _ in sys.stdin:
            gpio.levels[pin] = 0          # basılı
            time.sleep(0.15)
            gpio.levels[pin] = 1          # bırakıldı
    threading.Thread(target=loop, daemon=True).start()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", nargs="?", default="run", choices=["run", "test"])
    ap.add_argument("--mock", action="store_true")
    a = ap.parse_args()

    sb = load_config()["pins"].get("start_button") or {}
    pin = int(sb.get("gpio", 16))
    delay_s = float(sb.get("delay_s", 5))
    gpio = MockBackend() if a.mock else LgpioBackend(resolve_gpiochip(load_config()["pins"].get("gpiochip", "auto")))
    gpio.input(pin, pull_up=True)
    if a.mock:
        mock_keyboard(gpio, pin)
        log("(deneme modu) [Enter] = butona bas")

    deb = Debouncer(stable_s=0.05)
    prog = Program(build_command(sb, a.mock))

    def on_term(*_):
        raise SystemExit(0)
    signal.signal(signal.SIGTERM, on_term)       # systemctl stop / Pi kapanırken program güvenle durur

    try:
        if a.mode == "test":
            log(f"Buton testi: GPIO{pin}. Butona bas; her basışta bir satır görmelisin. Çıkmak için Ctrl+C.")
            n = 0
            while True:
                if deb.update(time.monotonic(), gpio.read(pin)):
                    n += 1
                    log(f"  ✓ basıldı ({n})")
                time.sleep(POLL_S)
        ctl = StartController(delay_s, prog.start, prog.stop, prog.running, log)
        log(f"Hazır: başlat butonunu bekliyorum (GPIO{pin}). Basınca {delay_s:.0f} sn sonra program başlar.")
        while True:
            now = time.monotonic()
            ctl.update(now, deb.update(now, gpio.read(pin)))
            time.sleep(POLL_S)
    except KeyboardInterrupt:
        pass
    finally:
        prog.stop()
        gpio.close()


if __name__ == "__main__":
    main()
