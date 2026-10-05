import unittest
from src.forecast_demo.metrics import mae, rmse, pinball

class TestMetrics(unittest.TestCase):
    def test_mae(self): self.assertAlmostEqual(mae([1,3],[2,3]), 0.5)
    def test_rmse(self): self.assertAlmostEqual(rmse([1,3],[2,3]), 2**-0.5)
    def test_pinball(self): self.assertAlmostEqual(pinball(10,8,0.5), 1.0)
    def test_bad_lengths(self):
        with self.assertRaises(ValueError): mae([1],[1,2])

if __name__ == '__main__': unittest.main()
