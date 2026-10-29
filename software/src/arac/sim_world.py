"""Duvar takibi/odometri testleri için 2D dünya + ışın izleme LiDAR + birinci derece gecikmeli robot."""
import math
import random


class World:
    def __init__(self, segments):
        self.segments = list(segments)

    @staticmethod
    def rect(x0, y0, x1, y1):
        return [(x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0)]

    def raycast(self, ox, oy, ang, rmax):
        dx, dy = math.cos(ang), math.sin(ang)
        best = math.inf
        for x1, y1, x2, y2 in self.segments:
            sx, sy = x2 - x1, y2 - y1
            den = dx * sy - dy * sx
            if abs(den) < 1e-12:
                continue
            t = ((x1 - ox) * sy - (y1 - oy) * sx) / den
            u = ((x1 - ox) * dy - (y1 - oy) * dx) / den
            if t >= 0.0 and 0.0 <= u <= 1.0 and t < best:
                best = t
        return best if best <= rmax else math.inf

    def scan(self, x, y, th, n=720, rmax=12.0, noise=0.0, dropout=0.0, rng=None):
        rng = rng or random
        inc = 2 * math.pi / n
        out = []
        for i in range(n):
            r = self.raycast(x, y, th - math.pi + i * inc, rmax)
            if r != math.inf:
                if noise:
                    r += rng.gauss(0, noise)
                if dropout and rng.random() < dropout:
                    r = math.inf
            out.append(r)
        return out, -math.pi, inc

    def clearance(self, x, y):
        best = math.inf
        for x1, y1, x2, y2 in self.segments:
            sx, sy = x2 - x1, y2 - y1
            t = max(0.0, min(1.0, ((x - x1) * sx + (y - y1) * sy) / (sx * sx + sy * sy)))
            best = min(best, math.hypot(x - (x1 + t * sx), y - (y1 + t * sy)))
        return best


class SimRobot:
    def __init__(self, x=0.0, y=0.0, th=0.0, tau_v=0.2, tau_w=0.15):
        self.x, self.y, self.th, self.v, self.w = x, y, th, 0.0, 0.0
        self.tau_v, self.tau_w = tau_v, tau_w

    def step(self, cmd_v, cmd_w, dt):
        self.v += (cmd_v - self.v) * dt / self.tau_v
        self.w += (cmd_w - self.w) * dt / self.tau_w
        self.th += self.w * dt
        self.x += self.v * math.cos(self.th) * dt
        self.y += self.v * math.sin(self.th) * dt
