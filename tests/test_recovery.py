import json
import tempfile
import unittest
from pathlib import Path
from src.forecast_demo.recovery import WorkUnit, SyntheticInterruption, RecoveryError, run_units, merge_units

UNITS=[WorkUnit('A',0,5),WorkUnit('B',5,10),WorkUnit('C',10,15),WorkUnit('D',15,20)]

class TestRecovery(unittest.TestCase):
    def test_interrupt_resume(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td)/'run'
            with self.assertRaises(SyntheticInterruption): run_units(d,UNITS,'s','c',2)
            r=run_units(d,UNITS,'s','c')
            self.assertEqual(r['reused'],2); self.assertEqual(r['written'],2)
            a=merge_units(d,UNITS,Path(td)/'accepted.json')
            self.assertEqual(a['rows'],20)
    def test_mixed_config_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td)/'run'
            with self.assertRaises(SyntheticInterruption): run_units(d,UNITS,'s','c1',1)
            with self.assertRaises(RecoveryError): run_units(d,UNITS,'s','c2')

if __name__ == '__main__': unittest.main()
