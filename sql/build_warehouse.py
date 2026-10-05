from __future__ import annotations

import csv
from pathlib import Path
import duckdb

from src.forecast_demo.pipeline import read_rows, make_forecasts

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "outputs" / "demo.duckdb"


def main() -> None:
    rows = read_rows(ROOT / "data" / "synthetic" / "releases.csv")
    pairs = make_forecasts(rows)
    DB.parent.mkdir(exist_ok=True)
    con = duckdb.connect(str(DB))
    con.execute((ROOT / "sql" / "schema.sql").read_text())
    with (ROOT / "data" / "synthetic" / "releases.csv").open() as f:
        pass
    con.execute("DELETE FROM staging.release_value")
    con.executemany("INSERT INTO staging.release_value VALUES (?, ?, ?, ?, ?)", [
        (r["region"], r["product"], int(r["release_step"]), r["release_date"], float(r["value"]))
        for r in rows
    ])
    con.executemany("INSERT INTO core.forecast_pair VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", [
        (r["region"], r["product"], r["origin_step"], r["target_step"], r["origin_date"], r["target_date"],
         r["actual"], r["baseline"], r["adaptive"])
        for r in pairs
    ])
    con.execute((ROOT / "sql" / "marts.sql").read_text())
    con.execute((ROOT / "sql" / "quality_checks.sql").read_text())
    failures = con.execute("SELECT COALESCE(SUM(failures),0) FROM qa.quality_result").fetchone()[0]
    if failures:
        raise SystemExit(f"RELATIONAL_QA_FAILED={failures}")
    print("RELATIONAL_QA=PASS")
    print(con.execute("SELECT * FROM mart.metric_summary ORDER BY system").fetchdf().to_string(index=False))
    con.close()


if __name__ == "__main__":
    main()
