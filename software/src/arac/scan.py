"""LiDAR taramasını (LaserScan benzeri dizi) araç gövdesi (base_link) çerçevesinde işler.
Saf Python; ROS gerektirmez."""
import math


def _wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


class ScanView:
    def __init__(self, ranges, angle_min, angle_inc, range_min=0.05, range_max=12.0,
                 lidar_x=0.0, lidar_y=0.0, lidar_yaw=0.0, inverted=False, max_use=12.0):
        self.xs, self.ys, self.angs, self.rs = [], [], [], []
        hi = min(range_max, max_use)
        cy, sy = math.cos(lidar_yaw), math.sin(lidar_yaw)
        for i, r in enumerate(ranges):
            if not (r == r) or r < range_min or r > hi:      # nan, inf, aralık dışı
                continue
            a = angle_min + i * angle_inc
            if inverted:
                a = -a
            lx, ly = r * math.cos(a), r * math.sin(a)         # LiDAR çerçevesi
            bx = lidar_x + cy * lx - sy * ly                  # base_link çerçevesi
            by = lidar_y + sy * lx + cy * ly
            self.xs.append(bx)
            self.ys.append(by)
            self.angs.append(math.atan2(by, bx))
            self.rs.append(math.hypot(bx, by))

    @classmethod
    def from_laserscan(cls, msg, robot_cfg, max_use=12.0):
        return cls(list(msg.ranges), msg.angle_min, msg.angle_increment, msg.range_min, msg.range_max,
                   robot_cfg.get("lidar_x_m") or 0.0, robot_cfg.get("lidar_y_m") or 0.0,
                   math.radians(robot_cfg.get("lidar_yaw_deg") or 0.0),
                   bool(robot_cfg.get("lidar_inverted")), max_use)

    def __len__(self):
        return len(self.rs)

    def sector_min(self, center, half_width):
        """Sektördeki en yakın nokta (araç merkezinden). Yoksa inf."""
        best = math.inf
        for a, r in zip(self.angs, self.rs):
            if abs(_wrap(a - center)) <= half_width and r < best:
                best = r
        return best

    def sector_points(self, center, half_width, max_dist=math.inf):
        return [(x, y) for x, y, a, r in zip(self.xs, self.ys, self.angs, self.rs)
                if abs(_wrap(a - center)) <= half_width and r <= max_dist]


def fit_line(points, trim=0.05):
    """Toplam en küçük kareler doğru uydurma (iki geçiş, aykırı değer atma).
    Döner: (dik uzaklık d [m], doğru yönü açısı alpha (-pi/2, pi/2] [rad], rms) veya None."""
    pts = points
    for _ in range(2):
        n = len(pts)
        if n < 3:
            return None
        cx = sum(p[0] for p in pts) / n
        cy = sum(p[1] for p in pts) / n
        sxx = sum((p[0] - cx) ** 2 for p in pts)
        syy = sum((p[1] - cy) ** 2 for p in pts)
        sxy = sum((p[0] - cx) * (p[1] - cy) for p in pts)
        phi = 0.5 * math.atan2(2 * sxy, sxx - syy)            # doğru yönü
        nx, ny = -math.sin(phi), math.cos(phi)                # birim normal
        res = [abs((p[0] - cx) * nx + (p[1] - cy) * ny) for p in pts]
        pts = [p for p, e in zip(pts, res) if e <= trim] or pts
    n = len(pts)
    if n < 3:
        return None
    rms = math.sqrt(sum(((p[0] - cx) * nx + (p[1] - cy) * ny) ** 2 for p in pts) / n)
    d = abs(cx * nx + cy * ny)
    alpha = phi
    if alpha > math.pi / 2:
        alpha -= math.pi
    elif alpha <= -math.pi / 2:
        alpha += math.pi
    return d, alpha, rms
