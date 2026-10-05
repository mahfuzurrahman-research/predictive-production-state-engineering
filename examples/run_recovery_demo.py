from pathlib import Path
import shutil

from src.forecast_demo.recovery import WorkUnit, SyntheticInterruption, run_units, merge_units

ROOT = Path(__file__).resolve().parents[1]
run_dir = ROOT / "outputs" / "recovery"
if run_dir.exists():
    shutil.rmtree(run_dir)
units = [WorkUnit("A",0,5), WorkUnit("B",5,10), WorkUnit("C",10,15), WorkUnit("D",15,20)]
try:
    run_units(run_dir, units, "synthetic-source", "demo-config", interrupt_after=2)
except SyntheticInterruption:
    print("INTERRUPTION_CAPTURED=PASS")
second = run_units(run_dir, units, "synthetic-source", "demo-config")
assert second["reused"] == 2 and second["written"] == 2
accepted = merge_units(run_dir, units, ROOT / "outputs" / "accepted.json")
print("RESUME=PASS")
print(f"ACCEPTED_ROWS={accepted['rows']}")
