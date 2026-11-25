"""Şerit ortalama + boşluk takibi + robot tanıma denetleyicisi (saf Python). Girdi: ScanView, çıktı: (v m/s, w rad/s).

Fibonacci Autonomous Car şartnamesi AC-3.5 duvar takibini yasaklar. Bu denetleyici tek bir duvarı
referans almaz: her taramada gövde genişliğinde bir koridorun hangi yönde en uzun açık kaldığına bakar
(boşluk takibi) ve düz kısımlarda iki duvarın ORTASINDA kalır. Köşeler, önü kapanınca açık tarafa
dönülerek geçilir.

Robot tanıma (Faz 1): LiDAR noktaları kümelere ayrılır. Kısa (<= robot_max_m) ve iki yanındaki noktalardan
belirgin biçimde YAKIN olan küme "robot" sayılır (duvar uzun ve süreklidir).
  - Yol yönü YALNIZCA duvarlardan seçilir; rakip pistin gidişini değiştirmez (yoksa rakip virajın içindeyken
    araç yanlış boşluğa, ör. köşe cebine yönelir).
  - Yol üzerindeki robot YAVAŞSA (ona yaklaşılıyor ya da arkasında yavaş kalınıyor) yol yönünün
    ±pass_half_deg içinde, robotun ötesine kadar açık yönden sollanır; yer yoksa mesafe korunarak takip edilir.
  - Robot yüzünden durulup o da gitmiyorsa yerinde dönülmez, kısa geri gidilir (ters yöne dönüp ters geçiş
    cezası almamak için).
  - Gidiş yönü (trav) gidilen yola göre güncellenir; bundan max_dev_free_deg'den fazla sapan yön seçilmez.

Konvansiyon: x ileri, y sol; açı sola pozitif."""
import math


def _clamp(x, lo, hi):
    return lo if x < lo else hi if x > hi else x


def _wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


def find_robots(xs, ys, p):
    """Nokta listesinden (açı sırasıyla) robot kümelerini bulur.
    Döner: [(cx, cy, en_yakin_mesafe, [nokta indeksleri])]"""
    n = len(xs)
    if n < 3:
        return []
    gap = p.get("cluster_gap_m", 0.06)
    clusters, cur = [], [0]
    for i in range(1, n):
        if math.hypot(xs[i] - xs[i - 1], ys[i] - ys[i - 1]) < gap:
            cur.append(i)
        else:
            clusters.append(cur)
            cur = [i]
    clusters.append(cur)
    if len(clusters) > 1 and math.hypot(xs[0] - xs[-1], ys[0] - ys[-1]) < gap:   # 360° sarma
        clusters[0] = clusters.pop() + clusters[0]
    rng = [math.hypot(x, y) for x, y in zip(xs, ys)]
    out = []
    for c in clusters:
        if len(c) < p.get("robot_min_pts", 3):
            continue
        span = max(math.hypot(xs[a] - xs[b], ys[a] - ys[b]) for a in (c[0], c[len(c) // 2]) for b in (c[-1], c[len(c) // 2]))
        if span > p.get("robot_max_m", 0.30):
            continue
        rmin = min(rng[i] for i in c)
        before, after = rng[(c[0] - 1) % n], rng[(c[-1] + 1) % n]
        jump = p.get("depth_jump_m", 0.08)
        if before > rmin + jump and after > rmin + jump:
            cx = sum(xs[i] for i in c) / len(c)
            cy = sum(ys[i] for i in c) / len(c)
            out.append((cx, cy, rmin, c))
    return out


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
        self.robots = []
        self.yaw = 0.0          # aracın yön tahmini (IMU verilmezse komut edilen dönüşlerin toplamı)
        self.trav = 0.0         # gidiş yönü: yaw'ın yavaş ortalaması (ters yöne dönmeyi önlemek için)
        self.back_t = 0.0       # robot kilitlenmesinde geri gitme süresi
        self.d_prev = math.inf  # yol üzerindeki robota önceki mesafe (yaklaşma hızı için)
        self.closing = 0.0      # yaklaşma hızı (m/s, süzülmüş)
        self.slow_t = 0.0       # takipte yavaş kalınan süre
        n = int(round(2 * p["search_half_deg"] / p["step_deg"]))
        self.cands = [math.radians(-p["search_half_deg"] + i * p["step_deg"]) for i in range(n + 1)]

    def reset(self):
        self.state, self.rec_t, self._v, self._w = "GO", 0.0, 0.0, 0.0

    def _free(self, groups, a):
        """a yönünde ilk engele kadar mesafe. groups: [(noktalar, koridor yarı genişliği)]."""
        ca, sa = math.cos(a), math.sin(a)
        best = self.p["look_m"]
        for pts, half in groups:
            for x, y in pts:
                f = x * ca + y * sa
                if 0.0 < f < best and abs(-x * sa + y * ca) < half:
                    best = f
        return best

    def step(self, view, dt, yaw=None):
        """yaw: varsa IMU/odometri açısı (rad). Yoksa komut edilen dönüşler toplanır."""
        p = self.p
        self.yaw = yaw if yaw is not None else self.yaw + self._w * dt
        # gidiş yönü ZAMANA değil GİDİLEN YOLA göre güncellenir: yerinde/yavaş dönerek ters yöne kayılamaz
        self.trav += _wrap(self.yaw - self.trav) * min(1.0, max(0.0, self._v) * dt / p.get("travel_len_m", 0.5))
        self.max_dev = max(getattr(self, "max_dev", 0.0), abs(_wrap(self.yaw - self.trav)))
        xs, ys = view.xs, view.ys
        half = p["half_width_m"] + p["side_margin_m"]
        detect = p.get("robot_detect", True)

        # --- robot tanıma ---
        self.robots = find_robots(xs, ys, p) if detect else []
        robot_idx = set()
        for r in self.robots:
            robot_idx.update(r[3])
        wall_pts = [(xs[i], ys[i]) for i in range(len(xs)) if i not in robot_idx]
        bot_pts = [(xs[i], ys[i]) for i in robot_idx]
        groups = [(wall_pts, half), (bot_pts, half + p.get("robot_margin_m", 0.06))]
        ahead = [r for r in self.robots
                 if r[0] > 0.0 and abs(r[1]) < half + 0.15 and r[2] < p.get("follow_look_m", 1.0)]
        d_ahead = min((r[2] for r in ahead), default=math.inf)

        # --- önde çok yakın engel ---
        fs = math.radians(p["front_stop_half_deg"])
        near, near_is_bot = math.inf, False
        for i, (a, r) in enumerate(zip(view.angs, view.rs)):
            if abs(a) <= fs and r < near:
                near, near_is_bot = r, i in robot_idx
        stop_at = p["front_len_m"] + p["hard_margin_m"]

        if self.state == "BACK":
            # robot kaynaklı kilitlenme: yönü değiştirmeden kısa geri git (ters yöne dönme riski yok)
            self.back_t += dt
            rear = view.sector_min(math.pi, math.radians(30))
            if self.back_t > p.get("back_s", 1.0) or rear < p["front_len_m"] + p["hard_margin_m"] + 0.05:
                self.state = "GO"
            else:
                self._v, self._w = -p.get("v_back", 0.08), 0.0
                return self._v, self._w

        if near < stop_at and self.state not in ("RECOVER", "WAIT"):
            self.state, self.wait_t = "WAIT", 0.0
        if self.state == "WAIT":
            self.wait_t += dt
            limit = p.get("wait_robot_max_s", 8.0) if near_is_bot else p["wait_max_s"]
            if near >= stop_at + 0.03:
                self.state = "GO"
            elif self.wait_t > limit and near_is_bot:
                # robot gitmedi (karşılıklı kilitlenme): yerinde DÖNME, kısa geri git
                self._v = self._w = 0.0
                self.state, self.back_t = "BACK", 0.0
                return 0.0, 0.0
            elif self.wait_t > limit:
                self.state = "RECOVER_START"          # duvar köşesinde sıkıştı: yerinde dön
            else:
                return self._brake()

        if self.state == "RECOVER_START":
            self.state, self.rec_t = "RECOVER", 0.0
            left = view.sector_min(math.radians(60), math.radians(30))
            right = view.sector_min(math.radians(-60), math.radians(30))
            back = _wrap(self.trav - self.yaw)
            if abs(back) > math.radians(30):          # gidiş yönünden saptıysa o tarafa dön
                self.rec_dir = 1.0 if back > 0 else -1.0
            else:
                self.rec_dir = 1.0 if left >= right else -1.0

        if self.state == "RECOVER":
            self.rec_t += dt
            front = self._free(groups, 0.0)
            if front > p["recover_clear_m"] or self.rec_t > p["recover_max_s"]:
                self.state = "GO"
            v, w = 0.0, self.rec_dir * p["w_turn"]
        else:
            # 1) YOL YÖNÜ yalnızca duvarlardan: rakip robot pistin gidişini değiştirmez
            dev = math.radians(p.get("max_dev_free_deg", 120))
            cands = [a for a in self.cands if abs(_wrap(self.yaw + a - self.trav)) <= dev]
            if not cands:                             # gidiş yönüne en yakın aday
                cands = [min(self.cands, key=lambda a: abs(_wrap(self.yaw + a - self.trav)))]
            wall_only = [(wall_pts, half)]
            frees = [self._free(wall_only, a) for a in cands]
            kt = p.get("trav_bias", 0.15)            # gidiş yönüne yakın açık yön tercih edilir
            score = [f - p["straight_bias"] * abs(a) - kt * abs(_wrap(self.yaw + a - self.trav))
                     for a, f in zip(cands, frees)]
            i = max(range(len(score)), key=score.__getitem__)
            a_gap, f_gap = cands[i], frees[i]
            front = self._free(groups, 0.0)

            # 2) yol üzerinde robot var mı (yol yönündeki koridorda)
            ca, sa = math.cos(a_gap), math.sin(a_gap)
            lat_need = half + p.get("robot_half_m", 0.075) + p.get("robot_margin_m", 0.06)
            block = [(cx * ca + cy * sa, r) for cx, cy, r, _ in self.robots
                     if 0.0 < cx * ca + cy * sa < min(f_gap, p.get("follow_look_m", 1.0))
                     and abs(-cx * sa + cy * ca) < lat_need]
            d_ahead = min((r for _, r in block), default=math.inf)
            # yalnızca YAVAŞ robotu solla: ona yaklaşıyorsak ya da arkasında bir süredir yavaş kaldıysak
            if block and self.d_prev < math.inf:
                self.closing += 0.3 * ((self.d_prev - d_ahead) / dt - self.closing)
            else:
                self.closing = 0.0
            self.d_prev = d_ahead
            if block and self._v < p.get("slow_frac", 0.7) * p["v_max"]:
                self.slow_t += dt
            elif not block:
                self.slow_t = 0.0
            want_pass = self.closing > p.get("pass_closing_mps", 0.03) or self.slow_t > p.get("pass_wait_s", 1.0)
            passing = False
            if block and want_pass:
                # sollama: yol yönünün ±pass_half_deg içinde, robotun ötesine kadar açık en yakın yön
                need = min(b for b, _ in block) + p.get("pass_beyond_m", 0.25)
                lim = math.radians(p.get("pass_half_deg", 60))
                opts = [a for a in self.cands if abs(a - a_gap) <= lim
                        and abs(_wrap(self.yaw + a - self.trav)) <= math.radians(p.get("max_dev_deg", 70))
                        and self._free(groups, a) >= min(need, f_gap)]
                if opts:
                    a_gap, passing = min(opts, key=lambda a: abs(a - a_gap)), True

            # 3) şerit ortalama (sollamıyorsa)
            dl = view.sector_min(math.radians(90), math.radians(p["side_half_deg"]))
            dr = view.sector_min(math.radians(-90), math.radians(p["side_half_deg"]))
            center = 0.0
            if not passing and dl < p["lane_max_m"] and dr < p["lane_max_m"] and front > p["slow_dist_m"]:
                center = _clamp(p["kc"] * (dl - dr) / 2.0, -p["max_center_rad"], p["max_center_rad"])

            heading = a_gap + center
            w = _clamp(p["kh"] * heading, -p["w_max"], p["w_max"])
            clear = _clamp((front - self.rr) / max(1e-6, p["slow_dist_m"] - self.rr), 0.0, 1.0)
            v = p["v_min"] + (p["v_max"] - p["v_min"]) * clear
            v *= 1.0 - 0.6 * min(1.0, abs(w) / p["w_max"])
            self.state = "SOLLA" if passing else "GO"
            if block and not passing:
                # 4) sollama yeri yok: yol yönünde, arkasından mesafe koruyarak git
                self.state = "TAKIP"
                v = min(v, _clamp(p.get("k_follow", 1.0) * (d_ahead - p.get("follow_dist_m", 0.30)),
                                  0.0, p["v_max"]))
            ahead = block
            if f_gap < stop_at + 0.05:                # hiçbir yön açık değil
                v, w = 0.0, 0.0
                if not ahead:                         # sebep robot değilse kilitlenme: yerinde dön
                    self.wait_t += dt
                    if self.wait_t > p["wait_max_s"]:
                        self.state = "RECOVER_START"
                else:
                    self.wait_t = 0.0
            else:
                self.wait_t = 0.0
            self.info = {"a_gap": a_gap, "f_gap": f_gap, "front": front, "dl": dl, "dr": dr,
                         "robots": len(self.robots), "d_ahead": d_ahead, "closing": self.closing}

        dv, dw = p["max_accel"] * dt, p["max_alpha"] * dt
        if v < self._v:
            dv = max(dv, self._v - v) if self.state == "RECOVER" else dv * 2.5
        self._v += _clamp(v - self._v, -dv, dv)
        self._w += _clamp(w - self._w, -dw, dw)
        return self._v, self._w

    def _brake(self):
        self._v = self._w = 0.0
        return 0.0, 0.0
