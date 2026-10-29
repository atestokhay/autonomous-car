import math
import unittest

from helpers import run_follow
from arac.sim_world import World


class WallFollowTest(unittest.TestCase):
    def test_straight_wall_converges(self):
        # Sağda y=-1 duvarı; robot duvardan 0.9 m uzakta ve 25° yanlış yönde başlıyor.
        w = World([(-1, -1.0, 12, -1.0), (-1, 4.0, 12, 4.0), (12, -1.0, 12, 4.0)])
        r = run_follow(w, (0.0, -0.1, math.radians(25)), 16.0)
        late = [tr for tr in r["trace"] if tr[0] > 10.0 and tr[1] < 10.5]
        self.assertTrue(late)
        for t, x, y, th, st, info in late:
            self.assertAlmostEqual(y + 1.0, 0.40, delta=0.04)       # duvara 0.40 m
        self.assertGreater(r["min_clear"], r["rr"])

    def test_left_wall_mirror(self):
        w = World([(-1, 1.0, 12, 1.0), (-1, -4.0, 12, -4.0), (12, -4.0, 12, 1.0)])
        r = run_follow(w, (0.0, 0.1, math.radians(-25)), 16.0, side="left")
        late = [tr for tr in r["trace"] if tr[0] > 10.0 and tr[1] < 10.5]
        self.assertTrue(late)
        for t, x, y, th, st, info in late:
            self.assertAlmostEqual(1.0 - y, 0.40, delta=0.04)
        self.assertGreater(r["min_clear"], r["rr"])

    def _room_lap(self, side, world, pose0, seconds=90.0, **kw):
        r = run_follow(world, pose0, seconds, side=side, **kw)
        self.assertGreater(r["min_clear"], r["rr"], f"çarpma! min={r['min_clear']:.3f}")
        return r

    def test_rectangular_room_right_wall(self):
        w = World(World.rect(0, 0, 5, 4))
        r = self._room_lap("right", w, (1.0, 0.8, 0.0))
        # Odayı tur atmalı: dört çeyreğe de uğramalı ve iç köşelerde dönmeli
        quads = {(tr[1] > 2.5, tr[2] > 2.0) for tr in r["trace"]}
        self.assertEqual(len(quads), 4)
        self.assertIn("TURN_INSIDE", r["states"])
        # duvara ortalama uzaklık hedefe yakın
        d = [tr[5]["d"] for tr in r["trace"] if tr[4] == "FOLLOW" and "d" in tr[5]]
        self.assertAlmostEqual(sum(d) / len(d), 0.40, delta=0.06)

    def test_rectangular_room_left_wall(self):
        w = World(World.rect(0, 0, 5, 4))
        r = self._room_lap("left", w, (1.0, 3.2, 0.0))
        quads = {(tr[1] > 2.5, tr[2] > 2.0) for tr in r["trace"]}
        self.assertEqual(len(quads), 4)

    def test_outside_corner_pillar(self):
        # Oda ortasında bir blok; blok solda kalacak şekilde çevresini dolaşır (saat yönünün tersi).
        # Bitişik kenar köşede hemen yeni duvar olarak görülür, araç ARC'sız dönebilir.
        room = World.rect(0, 0, 8, 6)
        block = World.rect(3, 2, 5, 4)
        w = World(room + block)
        r = self._room_lap("left", w, (3.5, 1.6, 0.0), seconds=70.0)
        quads = {(tr[1] > 4.0, tr[2] > 3.0) for tr in r["trace"]}
        self.assertEqual(len(quads), 4)          # bloğun etrafını tam dolaştı

    def test_wall_end_uses_arc(self):
        # Duvar bir noktada BİTİYOR ve etrafı boş (kapı boşluğu gibi): ARC ile köşeyi dönüp
        # duvarın öbür yüzüne geçmeli, çarpmamalı.
        far = World.rect(-10, -10, 14, 12)
        w = World(far + [(0.0, 2.0, 4.0, 2.0)])
        r = self._room_lap("left", w, (0.5, 1.6, 0.0), seconds=40.0)
        self.assertIn("ARC", r["states"])
        # Köşeyi dönüp duvarın öbür yüzünü (y>2, geri yön ~180°) tekrar FOLLOW ile takip etmeli
        back = [tr for tr in r["trace"]
                if tr[4] == "FOLLOW" and tr[2] > 2.2 and tr[1] < 3.5 and abs(abs(tr[3]) % (2 * math.pi) - math.pi) < 0.35]
        self.assertTrue(back, "duvarın öbür yüzü yakalanamadı")

    def test_lidar_offset_and_yaw(self):
        # LiDAR 8 cm önde ve 90° dönük monte: ScanView düzeltmeli
        w = World(World.rect(0, 0, 5, 4))
        r = self._room_lap("right", w, (1.0, 0.8, 0.0), seconds=60.0, lidar=(0.08, 0.0, math.radians(90)))
        d = [tr[5]["d"] for tr in r["trace"] if tr[4] == "FOLLOW" and "d" in tr[5]]
        self.assertAlmostEqual(sum(d) / len(d), 0.40, delta=0.07)

    def test_blocked_stops(self):
        # Gövde yarıçapına çok yakın duvarlar (0.18 m): acil dur, hareket yok
        w = World(World.rect(0, 0, 0.36, 0.36))
        r = run_follow(w, (0.18, 0.18, 0.0), 10.0)
        self.assertEqual(r["follower"].state, "ESTOP")
        self.assertAlmostEqual(r["robot"].x, 0.18, delta=0.01)
        self.assertAlmostEqual(r["robot"].y, 0.18, delta=0.01)

    def test_cornered_turns_without_hitting(self):
        # Dar ama hard_margin'in dışında bir kutu: yerinde dönmeli, çarpmamalı
        w = World(World.rect(0, 0, 0.5, 0.5))
        r = run_follow(w, (0.25, 0.25, 0.0), 10.0)
        self.assertGreater(r["min_clear"], 0.2)


if __name__ == "__main__":
    unittest.main()
