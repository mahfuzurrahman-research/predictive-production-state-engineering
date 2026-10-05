from __future__ import annotations

import csv
from datetime import date, timedelta
from pathlib import Path


def build_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    regions = ["North", "Central", "South"]
    products = ["Alpha", "Beta"]
    start = date(2023, 1, 15)
    for g, region in enumerate(regions):
        for p, product in enumerate(products):
            base = 80 + 11 * g + 7 * p
            for step in range(18):
                release_date = start + timedelta(days=30 * step)
                value = base + 0.8 * step + ((step + g + 2 * p) % 5 - 2) * 1.7
                rows.append({
                    "region": region,
                    "product": product,
                    "release_step": str(step),
                    "release_date": release_date.isoformat(),
                    "value": f"{value:.3f}",
                })
    return rows


def write_csv(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = build_rows()
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path


if __name__ == "__main__":
    write_csv(Path("data/synthetic/releases.csv"))
