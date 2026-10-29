from pathlib import Path

import yaml

SOFTWARE_DIR = Path(__file__).resolve().parents[2]
CONFIG_DIR = SOFTWARE_DIR / "config"


def load_config():
    cfg = {}
    for name in ("pins", "robot", "pid", "nav"):
        with open(CONFIG_DIR / f"{name}.yaml", encoding="utf-8") as f:
            cfg[name] = yaml.safe_load(f)
    cal = CONFIG_DIR / "robot_cal.yaml"        # stage 06 kalibrasyon çıktısı robot.yaml'ın üstüne biner
    if cal.exists():
        with open(cal, encoding="utf-8") as f:
            cfg["robot"].update({k: v for k, v in (yaml.safe_load(f) or {}).items() if not k.startswith("_")})
    tuned = CONFIG_DIR / "tuned.yaml"          # autotune çıktısı pid.yaml'ın üstüne biner
    if tuned.exists():
        with open(tuned, encoding="utf-8") as f:
            t = yaml.safe_load(f) or {}
        for side in ("left", "right"):
            if side in t:
                cfg["pid"][side].update(t[side])
    return cfg


def require_ticks(cfg):
    ticks = cfg["robot"].get("ticks_per_rev")
    if not ticks:
        raise SystemExit(
            "config/robot.yaml: ticks_per_rev boş. Önce şunu çalıştır:\n"
            "  python stages/03-enkoder/run.py calibrate"
        )
    return ticks


def require_geometry(cfg):
    r, b = cfg["robot"].get("wheel_radius_m"), cfg["robot"].get("wheel_base_m")
    if not r or not b:
        raise SystemExit(
            "config/robot.yaml: wheel_radius_m ve wheel_base_m boş. Cetvelle ölçüp yaz "
            "(tekerlek yarıçapı ve sol-sağ tekerlek temas noktaları arası, METRE).")
    return r, b
