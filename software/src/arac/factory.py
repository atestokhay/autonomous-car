from .encoder import Encoder
from .gpio_backend import LgpioBackend, resolve_gpiochip
from .motor import Motor
from .sim import SimEncoder, SimMotor, SimPlant


def make_hardware(cfg, sides, mock=False):
    """Döner: (gpio, parts). parts[side] = {motor, encoder, plant}. mock=True: donanımsız."""
    parts = {}
    if mock:
        tpr = cfg["robot"].get("ticks_per_rev") or 1000
        for s in sides:
            plant = SimPlant(tpr)
            parts[s] = {"motor": SimMotor(plant), "encoder": SimEncoder(plant), "plant": plant}
        return None, parts
    pins = cfg["pins"]
    gpio = LgpioBackend(resolve_gpiochip(pins["gpiochip"]))
    for s in sides:
        m, e = pins["motors"][s], pins["encoders"][s]
        parts[s] = {
            "motor": Motor(gpio, m["pwm"], m["in1"], m["in2"], pins["pwm_hz"], m["invert"]),
            "encoder": Encoder(gpio, e["a"], e["b"], e["invert"], pins["encoder_pull_up"]),
            "plant": None,
        }
    return gpio, parts


def close_hardware(gpio, parts):
    for p in parts.values():
        p["motor"].stop()
    if gpio is not None:
        gpio.close()


def build_drive(cfg, mock=False):
    """İki tekerlek hız kontrolcüsü + kinematik + odometri. Döner: (gpio, parts, DriveController)."""
    from .config import require_geometry, require_ticks
    from .drive import DriveController
    from .kinematics import Kinematics, Odometry
    from .pid import PID
    from .wheel import WheelSpeedController

    pc = cfg["pid"]
    ticks = (cfg["robot"].get("ticks_per_rev") or 392) if mock else require_ticks(cfg)
    r, b = require_geometry(cfg) if not mock else (cfg["robot"].get("wheel_radius_m") or 0.03,
                                                    cfg["robot"].get("wheel_base_m") or 0.16)
    gpio, parts = make_hardware(cfg, ["left", "right"], mock)
    wheels = {s: WheelSpeedController(parts[s]["motor"], parts[s]["encoder"], PID(**pc[s]), ticks,
                                      pc["speed_alpha"], pc["max_accel_rad_s2"], pc.get("speed_window", 4))
              for s in ("left", "right")}
    kin = Kinematics(r, b)
    odom = Odometry(kin, ticks)
    odom.reset_counts(parts["left"]["encoder"].count, parts["right"]["encoder"].count)
    drive = DriveController(wheels["left"], wheels["right"], kin, odom, pc["max_speed_rad_s"])
    return gpio, parts, drive
