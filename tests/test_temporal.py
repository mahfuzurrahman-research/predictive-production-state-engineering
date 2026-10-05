import unittest
from datetime import date
from src.forecast_demo.temporal import VintageValue, TemporalError, admit_as_of, validate_pair

class TestTemporal(unittest.TestCase):
    def test_available_allowed(self):
        self.assertEqual(admit_as_of(VintageValue(date(2024,1,1),3.0), date(2024,1,2)),3.0)
    def test_future_rejected(self):
        with self.assertRaises(TemporalError): admit_as_of(VintageValue(date(2024,1,3),3.0), date(2024,1,2))
    def test_bad_pair_rejected(self):
        with self.assertRaises(TemporalError): validate_pair(date(2024,2,1),date(2024,1,1))

if __name__ == '__main__': unittest.main()
