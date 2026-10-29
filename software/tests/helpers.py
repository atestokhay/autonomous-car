import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from arac.config import load_config  # noqa: E402
from arac.scan import ScanView  # noqa: E402
from arac.sim_world import SimRobot  # noqa: E402
from arac.wall_follow import WallFollower  # noqa: E402


def run_follow(world, pose0, seconds, side="right", overrides=None, noise=0.01, dropout=0.03,
               scan_hz=10, seed=1, lidar=(0.0, 0.0, 0.0), n=720):
    import random
    cfg = load_config()
    p = dict(cfg["nav"]["wall_follow"])
    p["side"] = side
    p.update(overrides or {})
    rr = cfg["robot"]["robot_radius_m"]
    f = WallFollower(p, rr)
    rob = SimRobot(*pose0)
    rng = random.Random(seed)
    dt_sim, trace = 0.01, []
    steps_per_scan = int(round(1.0 / scan_hz / dt_sim))
    cmd = (0.0, 0.0)
    t, min_clear, states = 0.0, math.inf, set()
    for i in range(int(seconds / dt_sim)):
        if i % steps_per_scan == 0:
            lx = rob.x + math.cos(rob.th) * lidar[0] - math.sin(rob.th) * lidar[1]
            ly = rob.y + math.sin(rob.th) * lidar[0] + math.cos(rob.th) * lidar[1]
            ranges, amin, inc = world.scan(lx, ly, rob.th + lidar[2], n=n, noise=noise, dropout=dropout, rng=rng)
            view = ScanView(ranges, amin, inc, 0.05, 12.0, *lidar)
            cmd = f.step(view, 1.0 / scan_hz)
            states.add(f.state)
        rob.step(cmd[0], cmd[1], dt_sim)
        t += dt_sim
        min_clear = min(min_clear, world.clearance(rob.x, rob.y))
        if i % 10 == 0:
            trace.append((t, rob.x, rob.y, rob.th, f.state, dict(f.info)))
    return {"robot": rob, "trace": trace, "min_clear": min_clear, "states": states, "rr": rr, "follower": f}
