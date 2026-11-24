import pathlib
import subprocess
import sys
import time
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))
from arac.config import load_config  # noqa: E402
from arac.gpio_backend import MockBackend  # noqa: E402
from arac.start_button import BEKLE, CALISIYOR, GERI_SAYIM, Debouncer, StartController  # noqa: E402

DT = 0.01


class Sim:
    """Sahte zaman + sahte buton + sahte program."""

    def __init__(self, delay=5.0):
        self.t, self.raw = 0.0, 1
        self.started = self.stopped = 0
        self.alive = False
        self.deb = Debouncer(0.05)
        self.ctl = StartController(delay, self._start, self._stop, lambda: self.alive, log=lambda s: None)
        self.run(0.2)                                            # açılış: buton bırakılmış (HIGH)

    def _start(self):
        self.started += 1
        self.alive = True

    def _stop(self):
        self.stopped += 1
        self.alive = False

    def run(self, seconds):
        for _ in range(int(round(seconds / DT))):
            self.t += DT
            self.ctl.update(self.t, self.deb.update(self.t, self.raw))

    def press(self, hold=0.2):
        self.raw = 0
        self.run(hold)
        self.raw = 1
        self.run(0.1)


class DebouncerTest(unittest.TestCase):
    def test_bounce_gives_single_press(self):
        d, t, edges = Debouncer(0.05), 0.0, 0
        for raw in [1] * 10 + [0, 1, 0, 1, 0] + [0] * 20 + [1, 0, 1] + [1] * 20:
            t += DT
            edges += d.update(t, raw)
        self.assertEqual(edges, 1)

    def test_short_glitch_ignored(self):
        d, t, edges = Debouncer(0.05), 0.0, 0
        for raw in [1] * 10 + [0, 0] + [1] * 10:                 # 20 ms parazit
            t += DT
            edges += d.update(t, raw)
        self.assertEqual(edges, 0)

    def test_line_low_at_boot_does_not_start(self):
        d, t, edges = Debouncer(0.05), 0.0, 0
        for raw in [0] * 50:                                     # açılışta hat LOW (kısa devre / basılı)
            t += DT
            edges += d.update(t, raw)
        self.assertEqual(edges, 0)
        for raw in [1] * 10 + [0] * 10:                          # bırak + yeniden bas: kabul
            t += DT
            edges += d.update(t, raw)
        self.assertEqual(edges, 1)


class StartControllerTest(unittest.TestCase):
    def test_starts_after_exactly_delay(self):
        s = Sim(5.0)
        s.run(1.0)
        s.raw = 0
        s.run(0.06)                                              # basma kabul edildi (50 ms süzme)
        t_press = s.t
        s.raw = 1
        s.run(4.8)
        self.assertEqual(s.started, 0)
        self.assertEqual(s.ctl.state, GERI_SAYIM)
        s.run(0.3)
        self.assertEqual(s.started, 1)
        self.assertEqual(s.ctl.state, CALISIYOR)
        self.assertAlmostEqual(s.ctl.deadline - t_press, 5.0, delta=0.02)

    def test_second_press_during_countdown_cancels(self):
        s = Sim(5.0)
        s.press()
        s.run(2.0)
        s.press()
        s.run(10.0)
        self.assertEqual(s.started, 0)
        self.assertEqual(s.ctl.state, BEKLE)

    def test_press_while_running_stops(self):
        s = Sim(5.0)
        s.press()
        s.run(5.5)
        self.assertTrue(s.alive)
        s.press()
        self.assertEqual(s.stopped, 1)
        self.assertFalse(s.alive)
        self.assertEqual(s.ctl.state, BEKLE)
        s.press()                                               # yeniden başlatılabilir
        s.run(5.5)
        self.assertEqual(s.started, 2)

    def test_program_exit_returns_to_wait(self):
        s = Sim(5.0)
        s.press()
        s.run(5.5)
        s.alive = False                                          # program kendi kapandı / çöktü
        s.run(0.1)
        self.assertEqual(s.ctl.state, BEKLE)
        self.assertEqual(s.stopped, 0)

    def test_held_button_starts_once(self):
        s = Sim(5.0)
        s.raw = 0
        s.run(20.0)                                              # 20 sn basılı tutuldu
        self.assertEqual(s.started, 1)
        self.assertEqual(s.stopped, 0)


class ConfigAndToolTest(unittest.TestCase):
    def test_pins_yaml_button_is_free_pin(self):
        p = load_config()["pins"]
        sb = p["start_button"]
        self.assertEqual(sb["gpio"], 16)
        self.assertEqual(sb["delay_s"], 5)
        used = {p["driver"]["stby"]}
        for side in ("left", "right"):
            used |= {p["motors"][side][k] for k in ("pwm", "in1", "in2")}
            used |= {p["encoders"][side][k] for k in ("a", "b")}
        used |= {2, 3}                                           # I2C (BNO055)
        self.assertNotIn(sb["gpio"], used)

    def test_mock_backend_input_pull_up(self):
        g = MockBackend()
        g.input(16, pull_up=True)
        self.assertEqual(g.read(16), 1)

    def test_command_uses_wall_follow_without_second_countdown(self):
        import baslat_butonu as bb
        cmd = bb.build_command({"side": "left", "v_scale": 0.3}, mock=False)
        self.assertIn("ros/launch/wall_follow.launch.py", cmd)
        self.assertIn("side:=left", cmd)
        self.assertIn("v_scale:=0.3", cmd)
        self.assertIn("countdown:=0", cmd)

    def test_program_start_stop_real_process(self):
        import baslat_butonu as bb
        p = bb.Program("exec sleep 30")
        p.start()
        time.sleep(0.2)
        self.assertTrue(p.running())
        t0 = time.monotonic()
        p.stop()
        self.assertFalse(p.running())
        self.assertLess(time.monotonic() - t0, 5)

    def test_mock_end_to_end(self):
        """Gerçek betik, deneme modu: Enter -> 5 sn -> program başlar."""
        proc = subprocess.Popen([sys.executable, str(ROOT / "tools" / "baslat_butonu.py"), "--mock"],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, cwd=ROOT)
        try:
            time.sleep(1.0)
            t0 = time.monotonic()
            proc.stdin.write("\n")
            proc.stdin.flush()
            lines = []
            while time.monotonic() - t0 < 9:
                line = proc.stdout.readline()
                lines.append(line)
                if "program çalışıyor" in line:
                    break
            elapsed = time.monotonic() - t0
            self.assertIn("program çalışıyor", "".join(lines))
            self.assertGreaterEqual(elapsed, 4.9)
            self.assertLess(elapsed, 7.0)
        finally:
            proc.terminate()
            proc.wait(timeout=20)


if __name__ == "__main__":
    unittest.main()
