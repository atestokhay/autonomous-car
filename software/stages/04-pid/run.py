"""Aşama 4: kapalı çevrim hız PID adım testi + CSV log. TEKERLEKLER HAVADA başla."""
import argparse
import csv
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))
from arac.config import load_config, require_ticks  # noqa: E402
from arac.factory import close_hardware, make_hardware  # noqa: E402
from arac.loop import RateLoop, try_realtime  # noqa: E402
from arac.pid import PID  # noqa: E402
from arac.wheel import WheelSpeedController  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--side", choices=["left", "right", "both"], default="left")
    ap.add_argument("--targets", default="0,10,20,10,0", help="rad/s, virgülle")
    ap.add_argument("--hold", type=float, default=3.0)
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--out", default="logs")
    a = ap.parse_args()

    cfg = load_config()
    pc = cfg["pid"]
    targets = [float(x) for x in a.targets.split(",")]
    if any(abs(t) > pc["max_speed_rad_s"] for t in targets):
        sys.exit(f"Güvenlik: hedef |{pc['max_speed_rad_s']}| rad/s sınırını aşıyor (pid.yaml)")
    ticks = require_ticks(cfg) if not a.mock else (cfg["robot"].get("ticks_per_rev") or 1000)

    sides = ["left", "right"] if a.side == "both" else [a.side]
    gpio, parts = make_hardware(cfg, sides, a.mock)
    ctrls = {s: WheelSpeedController(parts[s]["motor"], parts[s]["encoder"], PID(**pc[s]),
                                     ticks, pc["speed_alpha"], pc["max_accel_rad_s2"],
                                     pc.get("speed_window", 4)) for s in sides}
    print("Gerçek zamanlı öncelik:", "evet" if try_realtime() else "hayır (sudo ile çalıştırınca açılır)")

    rows = []
    for c in ctrls.values():
        c.reset()
    loop = RateLoop(pc["loop_hz"])
    t0 = time.monotonic()
    try:
        for tgt in targets:
            for c in ctrls.values():
                c.set_target(tgt)
            t_end = time.monotonic() + a.hold
            while time.monotonic() < t_end:
                dt = loop.wait()
                for s, c in ctrls.items():
                    sp, w, duty = c.update(dt)
                    if parts[s]["plant"]:
                        parts[s]["plant"].step(dt)
                    rows.append([round(time.monotonic() - t0, 4), s, tgt, round(sp, 3),
                                 round(w, 3), round(duty, 4), round(dt * 1e3, 3)])
    except (KeyboardInterrupt, RuntimeError) as e:
        print("\nDURDU:", e or "iptal")
    finally:
        for c in ctrls.values():
            c.stop()
        close_hardware(gpio, parts)

    out = pathlib.Path(a.out)
    out.mkdir(exist_ok=True)
    f = out / f"pid_{time.strftime('%Y%m%d_%H%M%S')}.csv"
    with open(f, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["t", "side", "target", "setpoint", "speed", "duty", "dt_ms"])
        w.writerows(rows)
    print("Log:", f)
    print("Döngü:", loop.stats())
    print("Grafik: python tools/plot_log.py", f)


if __name__ == "__main__":
    main()
