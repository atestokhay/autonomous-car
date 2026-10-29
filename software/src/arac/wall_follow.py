"""Duvar takip denetleyicisi (saf Python). Girdi: ScanView, çıktı: (v m/s, w rad/s).
Konvansiyon: x ileri, y sol. side='right' => duvar sağda (açı negatif)."""
import math

from .scan import fit_line


def _clamp(x, lo, hi):
    return lo if x < lo else hi if x > hi else x


class WallFollower:
    def __init__(self, p, robot_radius):
        self.p = dict(p)
        self.rr = robot_radius
        self.s = -1.0 if p["side"] == "right" else 1.0
        self.state = "SEARCH"
        self.lost_t = 0.0
        self.arc_t = 0.0
        self._v = self._w = 0.0
        self.info = {}

    def reset(self):
        self.state, self.lost_t, self.arc_t, self._v, self._w = "SEARCH", 0.0, 0.0, 0.0, 0.0

    def step(self, view, dt):
        p, s = self.p, self.s
        stop_front = self.rr + p["front_margin_m"]
        front = view.sector_min(0.0, math.radians(p["front_half_deg"]))
        near = view.sector_min(0.0, math.pi)
        pts = view.sector_points(s * math.radians(p["side_center_deg"]),
                                 math.radians(p["side_half_deg"]), p["lost_dist_m"])
        wall = fit_line(pts) if len(pts) >= p["min_wall_pts"] else None
        if wall is not None:
            # Gürültülü kısa parçaları (duvar ucunda kalan birkaç nokta) veya doğru olmayan
            # şekilleri duvar sayma: yeterince uzun ve düzgün çizgi şart.
            ca, sa = math.cos(wall[1]), math.sin(wall[1])
            proj = [x * ca + y * sa for x, y in pts]
            if max(proj) - min(proj) < p["min_wall_span_m"] or wall[2] > p["max_wall_rms_m"]:
                wall = None

        v = w = 0.0
        if near < self.rr + p["hard_margin_m"]:
            self.state = "ESTOP"
        elif self.state == "ESTOP":
            self.state = "SEARCH"                      # engel çekildi: yeniden başla

        if self.state == "ESTOP":
            v = w = 0.0
        elif self.state == "TURN_INSIDE":
            if front >= p["clear_dist_m"] and wall is not None and abs(wall[1]) < 0.35:
                self.state = "FOLLOW"
            else:
                v, w = 0.0, -s * p["w_turn"]
        elif front < stop_front:
            self.state = "TURN_INSIDE"
            v, w = 0.0, -s * p["w_turn"]

        if self.state not in ("ESTOP", "TURN_INSIDE"):
            if wall is not None:
                self.lost_t = self.arc_t = 0.0
                self.state = "FOLLOW"
                d, alpha, _ = wall
                err = d - p["target_dist_m"]
                phi_des = s * _clamp(p["kd"] * err, -p["max_approach_rad"], p["max_approach_rad"])
                w = _clamp(p["kh"] * (phi_des + alpha), -p["w_max"], p["w_max"])
                clear = _clamp((front - stop_front) / max(1e-6, p["slow_dist_m"] - stop_front), 0.0, 1.0)
                v = p["v_min"] + (p["v_max"] - p["v_min"]) * clear
                v *= 1.0 - 0.4 * min(1.0, abs(w) / p["w_max"])
                v *= 1.0 - _clamp(abs(err) / 0.5, 0.0, 0.2)
                self.info = {"d": d, "alpha": alpha, "err": err}
            else:
                self.lost_t += dt
                if self.state == "FOLLOW" and self.lost_t < p["lost_debounce_s"]:
                    v, w = p["v_arc"], 0.0             # kısa süre düz git
                elif self.state in ("FOLLOW", "ARC") and self.arc_t < p["arc_max_s"]:
                    self.state = "ARC"
                    self.arc_t += dt
                    v = p["v_arc"]
                    w = _clamp(s * v / p["arc_radius_m"], -p["w_max"], p["w_max"])
                else:
                    self.state = "SEARCH"
                    v, w = p["v_search"], s * 0.25

        # komut yumuşatma (ivme sınırı); acil/dönüş durumlarında v hemen düşebilir
        dv, dw = p["max_accel"] * dt, p["max_alpha"] * dt
        if v < self._v:
            dv = max(dv, self._v - v) if self.state in ("ESTOP", "TURN_INSIDE") else dv * 2.5
        self._v += _clamp(v - self._v, -dv, dv)
        self._w += _clamp(w - self._w, -dw, dw)
        if self.state == "ESTOP":
            self._v = self._w = 0.0
        return self._v, self._w
