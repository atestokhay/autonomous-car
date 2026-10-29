"""Donanımsız test için basit DC motor modeli (1. derece + ölü bölge)."""
import math


class SimPlant:
    def __init__(self, ticks_per_rev=1000, k=37.0, tau=0.08, deadband=0.10):
        self.tpr, self.k, self.tau, self.deadband = ticks_per_rev, k, tau, deadband
        self.duty = 0.0
        self.omega = 0.0   # rad/s
        self.pos_ticks = 0.0

    def step(self, dt):
        eff = max(abs(self.duty) - self.deadband, 0.0) * (1 if self.duty >= 0 else -1)
        self.omega += (self.k * eff - self.omega) * dt / self.tau
        self.pos_ticks += self.omega * dt * self.tpr / (2 * math.pi)


class SimMotor:
    def __init__(self, plant):
        self.plant = plant
        self.duty = 0.0

    def set(self, duty):
        self.duty = self.plant.duty = max(-1.0, min(1.0, duty))

    def stop(self):
        self.set(0.0)


class SimEncoder:
    missed = 0

    def __init__(self, plant):
        self.plant = plant

    @property
    def count(self):
        return int(self.plant.pos_ticks)

    def reset(self):
        self.plant.pos_ticks = 0.0
