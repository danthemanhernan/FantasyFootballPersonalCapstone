import unittest

import numpy as np

from services.vision.shot_gate import ShotGate


class ShotGateTests(unittest.TestCase):
    def test_stable_and_hard_cut(self):
        gate = ShotGate(threshold=0.5)
        black = np.zeros((16, 16, 3), dtype=np.uint8)
        white = np.full((16, 16, 3), 255, dtype=np.uint8)
        self.assertEqual(gate.update(black).shot_id, 0)
        self.assertFalse(gate.update(black).cut)
        cut = gate.update(white)
        self.assertTrue(cut.cut)
        self.assertEqual(cut.shot_id, 1)
        self.assertFalse(gate.update(white).cut)

    def test_invalid_frame(self):
        with self.assertRaises(ValueError):
            ShotGate().update(np.zeros((8, 8), dtype=np.uint8))


if __name__ == "__main__":
    unittest.main()
