from pathlib import Path

from src.forecast_demo.generate import write_csv
from src.forecast_demo.pipeline import read_rows, make_forecasts, evaluate
from src.forecast_demo.reporting import write_reports

ROOT = Path(__file__).resolve().parents[1]
write_csv(ROOT / "data" / "synthetic" / "releases.csv")
rows = read_rows(ROOT / "data" / "synthetic" / "releases.csv")
pairs = make_forecasts(rows)
metrics = evaluate(pairs)
write_reports(metrics, ROOT / "outputs")
print(f"SYNTHETIC_PAIRS={len(pairs)}")
print("FORECAST_DEMO=PASS")
