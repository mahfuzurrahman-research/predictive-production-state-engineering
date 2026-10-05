from __future__ import annotations

import json
from pathlib import Path


def write_reports(metrics: list[dict], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    lines = ["# Synthetic Forecast Evaluation", "", "| System | Metric | Value |", "|---|---|---:|"]
    for row in metrics:
        lines.append(f"| {row['system']} | {row['metric']} | {row['value']:.4f} |")
    lines += ["", "> Synthetic engineering demonstration only; no private research result is represented."]
    (output_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
