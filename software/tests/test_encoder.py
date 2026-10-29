import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from arac.encoder import Encoder  # noqa: E402
from arac.gpio_backend import MockBackend  # noqa: E402

A, B = 17, 27
FWD = [(B, 1), (A, 1), (B, 0), (A, 0)]   # 00→01→11→10→00
REV = [(A, 1), (B, 1), (A, 0), (B, 0)]   # 00→10→11→01→00


def feed(g, seq, times=1):
    for _ in range(times):
        for pin, lvl in seq:
            g.emit(pin, lvl)


class EncoderTest(unittest.TestCase):
    def make(self, invert=False):
        g = MockBackend()
        return g, Encoder(g, A, B, invert)

    def test_forward_counts_up(self):
        g, e = self.make()
        feed(g, FWD, 25)
        self.assertEqual(e.count, 100)
        self.assertEqual(e.missed, 0)

    def test_reverse_counts_down(self):
        g, e = self.make()
        feed(g, REV, 10)
        self.assertEqual(e.count, -40)

    def test_invert(self):
        g, e = self.make(invert=True)
        feed(g, FWD, 5)
        self.assertEqual(e.count, -20)

    def test_missed_edge_detected(self):
        g, e = self.make()
        g.levels[A] = 1  # A ve B aynı anda değişmiş gibi (00→11)
        g.levels[B] = 1
        e._on_edge(A, 1, 0)   # A=1,B=0 → geçerli adım
        e._on_edge(B, 1, 0)
        e._A, e._B, e._state = 0, 0, 0
        e._on_edge(A, 1, 0)   # 00→10
        e._on_edge(B, 0, 0)   # 10→10 (değişmedi)
        e._state = 0b00
        e._A, e._B = 1, 1     # 00→11: iki bit birden
        e._on_edge(A, 1, 0)
        self.assertGreaterEqual(e.missed, 1)


if __name__ == "__main__":
    unittest.main()
