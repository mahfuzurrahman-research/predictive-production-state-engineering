from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
metrics = json.loads((ROOT / "outputs" / "metrics.json").read_text())
rows = "".join(
    f"<tr><td>{html.escape(x['system'])}</td><td>{html.escape(x['metric'])}</td><td>{x['value']:.4f}</td></tr>"
    for x in metrics
)
page = f"""<!doctype html><meta charset='utf-8'><title>Forecast Engineering Demo</title>
<style>body{{font-family:system-ui;max-width:900px;margin:40px auto;padding:0 20px}}table{{border-collapse:collapse}}td,th{{border:1px solid #bbb;padding:8px}}</style>
<h1>Predictive Production State — Engineering Demo</h1>
<p><strong>Synthetic data only.</strong> No private empirical result is displayed.</p>
<table><thead><tr><th>System</th><th>Metric</th><th>Value</th></tr></thead><tbody>{rows}</tbody></table>
"""
(ROOT / "outputs" / "dashboard.html").write_text(page, encoding="utf-8")
print("DASHBOARD=outputs/dashboard.html")
