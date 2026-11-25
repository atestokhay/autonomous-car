#!/usr/bin/env python3
"""`arac` — soru sormadan robotu hazırlar ve duvar takibine çıkarır.

İlk çalıştırmada (ölçülmemiş değerler varsa) sırayla:
  1) enkoder yönleri      : her motor kısa süre döner, sayım yönü motora uydurulur (pins.yaml)
  2) tur başına sayım/hız : robot yerinde tam hızla döner; ticks_per_rev ve azami hız hesaplanır
  3) PID ayarı            : otomatik ayar (robot yerinde kısa dönüşler yapar)
  4) LiDAR yönü           : robot kısa süre ileri gider, taramalardan "ön" bulunur
  5) duvar takibi         : tam hızla, Ctrl+C'ye kadar
Ölçülen değerler config/robot_cal.yaml, config/oto.yaml, config/tuned.yaml dosyalarına yazılır;
sonraki çalıştırmalarda doğrudan 5. adım başlar.  Baştan ölçmek için:  arac sifirla
Deneme (donanımsız):  python3 otomatik.py --mock"""
import math
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
if "--mock" in sys.argv and not os.environ.get("ARAC_CONFIG_DIR"):
    # deneme modu gerçek ayar dosyalarını bozmasın: config'in geçici kopyasıyla çalışır
    import tempfile
    _tmp = Path(tempfile.mkdtemp(prefix="arac_deneme_"))
    shutil.copytree(ROOT / "config", _tmp, dirs_exist_ok=True)
    for _f in ("robot_cal.yaml", "oto.yaml", "tuned.yaml"):
        (_tmp / _f).unlink(missing_ok=True)
    os.environ["ARAC_CONFIG_DIR"] = str(_tmp)
import yaml  # noqa: E402

from arac.config import CONFIG_DIR, load_config  # noqa: E402
from arac.factory import close_hardware, make_hardware  # noqa: E402

MOCK = "--mock" in sys.argv
PY = sys.executable
ROS_ENV = ("source /opt/ros/jazzy/setup.bash; "
           "[ -f ~/ros2_ws/install/setup.bash ] && source ~/ros2_ws/install/setup.bash; ")
CAL, OTO, TUNED = CONFIG_DIR / "robot_cal.yaml", CONFIG_DIR / "oto.yaml", CONFIG_DIR / "tuned.yaml"
ENKODER_TICK = 28   # N20 manyetik enkoder: 7 darbe/kanal × 4 kenar = motor turu başına 28


def say(msg, c=None):
    cols = {"g": 32, "r": 31, "y": 33, "b": 1}
    print(f"\033[{cols[c]}m{msg}\033[0m" if c else msg, flush=True)


def oku(p):
    return (yaml.safe_load(p.read_text(encoding="utf-8")) if p.exists() else None) or {}


def yaz(p, d):
    p.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True), encoding="utf-8")


def cal_yaz(**kv):
    d = oku(CAL)
    d.update(kv)
    yaz(CAL, d)


def invert_cevir(section, side):
    """pins.yaml: section (motors|encoders) altındaki side satırının invert değerini tersine çevirir."""
    f = CONFIG_DIR / "pins.yaml"
    lines, cur = f.read_text(encoding="utf-8").splitlines(keepends=True), None
    for i, ln in enumerate(lines):
        m = re.match(r"^(\w+):", ln)
        if m:
            cur = m.group(1)
        if cur == section and re.match(rf"^\s+{side}:", ln):
            lines[i] = re.sub(r"invert:\s*(true|false)",
                              lambda m: "invert: " + ("false" if m.group(1) == "true" else "true"), ln)
    f.write_text("".join(lines), encoding="utf-8")


# ---------- motor/enkoder ölçümü ----------
def olc(duties, sure, isinma=0.4):
    """duties: {side: duty}. Isınmadan sonra `sure` boyunca tick/sn döner."""
    cfg = load_config()
    gpio, parts = make_hardware(cfg, list(duties), MOCK)

    def bekle(sn):
        if MOCK:
            for _ in range(int(sn / 0.01)):
                for p in parts.values():
                    p["plant"].step(0.01)
        else:
            time.sleep(sn)
    try:
        for s, d in duties.items():
            parts[s]["motor"].set(d)
        bekle(isinma)
        c0 = {s: parts[s]["encoder"].count for s in duties}
        bekle(sure)
        out = {s: (parts[s]["encoder"].count - c0[s]) / sure for s in duties}
        kacan = {s: getattr(parts[s]["encoder"], "missed", 0) for s in duties}
    finally:
        close_hardware(gpio, parts)
    if any(kacan.values()):
        say(f"   ! enkoder kaçan kenar: {kacan}", "y")
    return out


def adim_enkoder():
    say("\n[1/5] Enkoder yönleri", "b")
    for s in ("left", "right"):
        tps = olc({s: 0.6}, 0.5)[s]
        ad = "SOL" if s == "left" else "SAĞ"
        if abs(tps) < 30:
            raise SystemExit(f"{ad} motor dönmüyor ya da enkoderi saymıyor (ölçülen {tps:.0f} tick/sn). "
                             f"Kablolar: kablolama şeması (hardware/wiring/schematic.png).")
        if tps < 0:
            invert_cevir("encoders", s)
            say(f"   {ad} enkoder yönü düzeltildi", "y")
        else:
            say(f"   {ad} enkoder doğru", "g")


def adim_hiz():
    say("\n[2/5] Tur başına sayım ve azami hız (robot yerinde döner)", "b")
    cfg = load_config()
    rob = cfg["robot"]
    tps = olc({"left": 1.0, "right": -1.0}, 1.5)
    tps = {s: abs(v) for s, v in tps.items()}
    if min(tps.values()) < 30:
        raise SystemExit(f"Tam hızda sayım çok düşük: {tps}. Motor beslemesini (6 V) kontrol et.")
    ticks = rob.get("ticks_per_rev") if CAL.exists() and oku(CAL).get("ticks_per_rev") else None
    if not ticks:
        ham = (sum(tps.values()) / 2) * 60.0 / float(rob.get("nominal_rpm") or 300)
        ticks = ENKODER_TICK * max(1, round(ham / ENKODER_TICK))
        cal_yaz(ticks_per_rev=int(ticks))
        say(f"   ticks_per_rev = {ticks} (dişli ≈ 1:{ticks // ENKODER_TICK})", "g")
    w = {s: v * 2 * math.pi / ticks for s, v in tps.items()}
    wmax = round(0.9 * min(w.values()), 1)          # PID'in düzeltme payı için %90
    r = float(rob["wheel_radius_m"])
    v = round(wmax * r, 3)
    oto = oku(OTO)
    oto["pid"] = {"max_speed_rad_s": wmax}
    oto["nav"] = {"wall_follow": {"v_max": v, "v_min": round(0.5 * v, 3), "v_arc": round(0.9 * v, 3),
                                  "v_search": v}}
    yaz(OTO, oto)
    say(f"   tekerlek azami {min(w.values()):.1f} rad/s → sınır {wmax} rad/s, duvar takibi hızı {v} m/s", "g")


def adim_pid():
    say("\n[3/5] PID otomatik ayar (birkaç dakika, robot yerinde kısa dönüşler yapar)", "b")
    ok = subprocess.run([PY, "stages/04-pid/autotune.py", "--yes", *(["--mock"] if MOCK else [])],
                        cwd=ROOT).returncode == 0
    if not ok:
        say("   ! Otomatik ayar tam geçmedi; varsayılan PID değerleriyle devam ediliyor.", "y")


# ---------- ROS ----------
def ros_baslat(launch="bringup.launch.py", ek=""):
    return subprocess.Popen(["bash", "-c", ROS_ENV + f"exec ros2 launch ros/launch/{launch}" + ek],
                            cwd=ROOT, preexec_fn=os.setsid)


def ros_durdur(p):
    if p and p.poll() is None:
        try:
            os.killpg(os.getpgid(p.pid), signal.SIGINT)
            p.wait(timeout=8)
        except Exception:  # noqa: BLE001
            try:
                os.killpg(os.getpgid(p.pid), signal.SIGKILL)
            except Exception:  # noqa: BLE001
                pass


def ros_var():
    return not MOCK and shutil.which("bash") and Path("/opt/ros/jazzy/setup.bash").exists()


def adim_lidar():
    say("\n[4/5] LiDAR yönü (robot kısa süre ileri gider)", "b")
    if not ros_var():
        say("   (ROS yok ya da deneme modu: atlandı)", "y")
        return
    for deneme in range(2):
        p = ros_baslat()
        try:
            time.sleep(6)
            kod = subprocess.run(["bash", "-c", ROS_ENV + f"exec {PY} ros/lidar_yon_node.py"], cwd=ROOT).returncode
        finally:
            ros_durdur(p)
        if kod == 0:
            return
        if kod == 3 and deneme == 0:
            say("   Sağ motor ters dönüyor: yönü çevrilip tekrar deneniyor.", "y")
            invert_cevir("motors", "right")
            invert_cevir("encoders", "right")
            continue
        raise SystemExit("LiDAR yönü bulunamadı: LiDAR çalışıyor mu, robotun önünde 1–2 m boş yer var mı?")
    raise SystemExit("Robot ileri komutta düz gitmiyor: motor kablolarını şemaya göre kontrol et.")


def duvar_takibi():
    say("\n[5/5] Duvar takibi (tam hız). Durdurmak için Ctrl+C.", "b")
    if not ros_var():
        say("   (ROS yok ya da deneme modu: duvar takibi çalıştırılamaz)", "y")
        return
    p = ros_baslat()
    try:
        time.sleep(6)
        subprocess.run(["bash", "-c", ROS_ENV + f"exec {PY} ros/wall_follow_node.py --side right "
                                                 "--v-scale 1.0 --countdown 3"], cwd=ROOT)
    except KeyboardInterrupt:
        pass
    finally:
        ros_durdur(p)


def sifirla():
    for f in (CAL, OTO, TUNED):
        if f.exists():
            f.unlink()
    say("Ölçümler silindi; bir sonraki `arac` her şeyi baştan ölçer.", "g")


def main():
    if "sifirla" in sys.argv:
        return sifirla()
    say("ARAÇ başlıyor" + (" (deneme modu)" if MOCK else ""), "b")
    o = oku(OTO)
    if not o.get("enkoder_ok"):
        adim_enkoder()
        o = oku(OTO)
        o["enkoder_ok"] = True
        yaz(OTO, o)
    if not (oku(OTO).get("pid") and oku(CAL).get("ticks_per_rev")):
        adim_hiz()
    if not TUNED.exists():
        adim_pid()
    if "lidar_yaw_deg" not in oku(CAL):
        adim_lidar()
    duvar_takibi()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        say("\nDurduruldu.", "y")
