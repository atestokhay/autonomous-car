"""Odometri kalibrasyonu için saf hesaplar (donanımsız test edilir)."""
import math


def wheel_radius_from_push(dist_m, ticks_left, ticks_right, ticks_per_rev):
    """Araç elle DÜZ itildi, gerçek mesafe dist_m ölçüldü -> tekerlek yarıçapı (m)."""
    turns = (abs(ticks_left) + abs(ticks_right)) / 2.0 / ticks_per_rev
    if turns <= 0:
        raise ValueError("Enkoder saymadı")
    return dist_m / (2.0 * math.pi * turns)


def wheel_base_from_spin(angle_rad, ticks_left, ticks_right, ticks_per_rev, radius_m):
    """Araç elle YERİNDE döndürüldü (gerçek açı angle_rad) -> tekerlekler arası mesafe (m)."""
    dl = ticks_left * 2.0 * math.pi / ticks_per_rev
    dr = ticks_right * 2.0 * math.pi / ticks_per_rev
    if angle_rad == 0 or dr - dl == 0:
        raise ValueError("Dönüş yok")
    return radius_m * abs(dr - dl) / abs(angle_rad)
