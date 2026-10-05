import unittest
from src.forecast_demo.generate import build_rows
from src.forecast_demo.pipeline import make_forecasts, evaluate

class TestPipeline(unittest.TestCase):
    def test_pairs_and_metrics(self):
        pairs = make_forecasts(build_rows())
        self.assertGreater(len(pairs), 20)
        metrics = evaluate(pairs)
        self.assertEqual({m['metric'] for m in metrics},{'MAE','RMSE'})
        self.assertEqual({m['system'] for m in metrics},{'baseline','adaptive'})

if __name__ == '__main__': unittest.main()
