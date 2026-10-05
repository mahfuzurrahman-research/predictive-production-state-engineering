from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from .metrics import mae, rmse
from .temporal import VintageValue, admit_as_of, validate_pair


def read_rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def make_forecasts(rows: list[dict], horizon_steps: int = 3) -> list[dict]:
    if horizon_steps < 1:
        raise ValueError("horizon_steps must be positive")

    by_group: dict[tuple[str, str], list[dict]] = {}
    for r in rows:
        by_group.setdefault((r["region"], r["product"]), []).append(r)

    output: list[dict] = []
    for (region, product), group in sorted(by_group.items()):
        group = sorted(group, key=lambda x: int(x["release_step"]))
        for i in range(3, len(group) - horizon_steps):
            origin = group[i]
            target = group[i + horizon_steps]
            origin_date = date.fromisoformat(origin["release_date"])
            target_date = date.fromisoformat(target["release_date"])
            validate_pair(origin_date, target_date)

            history = group[: i + 1]
            available = [
                admit_as_of(
                    VintageValue(date.fromisoformat(h["release_date"]), float(h["value"])),
                    origin_date,
                )
                for h in history
            ]

            baseline = available[-1]
            adaptive = available[-1] + 0.5 * (available[-1] - available[-2])
            actual = float(target["value"])

            output.append({
                "region": region,
                "product": product,
                "origin_step": i,
                "target_step": i + horizon_steps,
                "origin_date": origin["release_date"],
                "target_date": target["release_date"],
                "actual": actual,
                "baseline": baseline,
                "adaptive": adaptive,
            })
    return output


def evaluate(pairs: list[dict]) -> list[dict]:
    actual = [r["actual"] for r in pairs]
    out = []
    for system in ("baseline", "adaptive"):
        pred = [r[system] for r in pairs]
        out.append({"system": system, "metric": "MAE", "value": mae(actual, pred)})
        out.append({"system": system, "metric": "RMSE", "value": rmse(actual, pred)})
    return out
