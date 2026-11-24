"""Şerit ortalama + boşluk takibi denetleyicisi (saf Python). Girdi: ScanView, çıktı: (v m/s, w rad/s).

Fibonacci Autonomous Car şartnamesi AC-3.5 duvar takibini yasaklar. Bu denetleyici tek bir duvarı
referans almaz: her taramada gövde genişliğinde bir koridorun hangi yönde en uzun açık kaldığına bakar
(boşluk takibi) ve düz kısımlarda iki duvarın ORTASINDA kalır. Köşeler, önü kapanınca açık tarafa
dönülerek geçilir; pistteki diğer robotlar da engel olarak görülür ve etraflarından dolaşılır.

Konvansiyon: x ileri, y sol; açı sola pozitif."""
import math


def _clamp(x, lo, hi):
    return lo if x < lo else hi if x > hi else x


class LaneFollower:
    def __init__(self, p, robot_radius):
        self.p = dict(p)
        self.rr = robot_radius
        self.state = "GO"
        self.rec_t = 0.0
        self.rec_dir = 1.0
        self.wait_t = 0.0
        self._v = self._w = 0.0
        self.info = {}
        n = int(round(2 * p["search_half_deg"] / p["step_deg"]))
        self.cands = [math.radians(-p["search_half_deg"] + i * p["step_deg"]) for i in range(n + 1)]

    def reset(self):
        self.state, self.rec_t, self._v, self._w = "GO", 0.0, 0.0, 0.0

    def _free(self, pts, a, half):
        """a yönünde, yarı genişliği `half` olan koridorda ilk engele kadar mesafe."""
        ca, sa = math.cos(a), math.sin(a)
        best = self.p["look_m"]
        for x, y in pts:
            f = x * ca + y * sa
            if 0.0 < f < best and abs(-x * sa + y * ca) < half:
                best = f
        return best

    def step(self, view, dt):
        p = self.p
        pts = list(zip(view.xs, view.ys))
        # yalnızca ÖNDEKİ yakın engel durdurur; yanda/arkada duran robot (başlangıç çizgisi) durdurmaz
        near = view.sector_min(0.0, math.radians(p["front_stop_half_deg"]))
        half = p["half_width_m"] + p["side_margin_m"]

        if near < p["front_len_m"] + p["hard_margin_m"] and self.state not in ("RECOVER", "WAIT"):
            # önde çok yakın engel: önce bekle (öndeki robot uzaklaşabilir), geri dönme (ters geçiş cezası)
            self.state, self.wait_t = "WAIT", 0.0
        if self.state == "WAIT":
            self.wait_t += dt
            if near >= p["front_len_m"] + p["hard_margin_m"] + 0.03:
                self.state = "GO"
            elif self.wait_t > p["wait_max_s"]:
                self.state = "RECOVER_START"
            else:
                return self._brake()

        if self.state == "RECOVER_START":
            # çok yakın: dur ve en açık tarafa doğru yerinde dön (sıkışmayı kendi çöz)
            self.state, self.rec_t = "RECOVER", 0.0
            left = view.sector_min(math.radians(60), math.radians(30))
            right = view.sector_min(math.radians(-60), math.radians(30))
            self.rec_dir = 1.0 if left >= right else -1.0

        if self.state == "RECOVER":
            self.rec_t += dt
            front = self._free(pts, 0.0, half)
            if front > p["recover_clear_m"] or self.rec_t > p["recover_max_s"]:
                self.state = "GO"
            v, w = 0.0, self.rec_dir * p["w_turn"]
        else:
            # 1) boşluk takibi: en uzun açık koridorun yönü (düz gitmek hafifçe tercih edilir)
            frees = [self._free(pts, a, half) for a in self.cands]
            score = [f - p["straight_bias"] * abs(a) for a, f in zip(self.cands, frees)]
            i = max(range(len(score)), key=score.__getitem__)
            a_gap, f_gap = self.cands[i], frees[i]
            front = frees[len(frees) // 2]

            # 2) şerit ortalama: iki yanda da duvar varsa ortaya çek
            dl = view.sector_min(math.radians(90), math.radians(p["side_half_deg"]))
            dr = view.sector_min(math.radians(-90), math.radians(p["side_half_deg"]))
            center = 0.0
            if dl < p["lane_max_m"] and dr < p["lane_max_m"] and front > p["slow_dist_m"]:
                center = _clamp(p["kc"] * (dl - dr) / 2.0, -p["max_center_rad"], p["max_center_rad"])

            heading = a_gap + center
            w = _clamp(p["kh"] * heading, -p["w_max"], p["w_max"])
            clear = _clamp((front - self.rr) / max(1e-6, p["slow_dist_m"] - self.rr), 0.0, 1.0)
            v = p["v_min"] + (p["v_max"] - p["v_min"]) * clear
            v *= 1.0 - 0.6 * min(1.0, abs(w) / p["w_max"])
            if f_gap < p["front_len_m"] + p["hard_margin_m"] + 0.05:   # hiçbir yön açık değil: bekle
                v, w = 0.0, 0.0
            self.state = "GO"
            self.info = {"a_gap": a_gap, "f_gap": f_gap, "front": front, "dl": dl, "dr": dr}

        dv, dw = p["max_accel"] * dt, p["max_alpha"] * dt
        if v < self._v:
            dv = max(dv, self._v - v) if self.state == "RECOVER" else dv * 2.5
        self._v += _clamp(v - self._v, -dv, dv)
        self._w += _clamp(w - self._w, -dw, dw)
        return self._v, self._w

    def _brake(self):
        self._v = self._w = 0.0
        return 0.0, 0.0
