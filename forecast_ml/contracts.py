from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
RAW_FIELDS = {
    "row_id", "area_id", "event_day", "target_value", "target_available_at",
    "weather", "weather_available_at", "synthetic_record",
}


def utc(value: str) -> datetime:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value):
        raise ValueError("canonical UTC timestamp required")
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def stamp(day: str, hour: int = 7) -> str:
    return f"{day}T{hour:02d}:00:00Z"


def day_at(index: int, c: dict) -> str:
    return (date.fromisoformat(c["start_day"])+timedelta(days=index)).isoformat()


def index_of(day: str, c: dict) -> int:
    return (date.fromisoformat(day)-date.fromisoformat(c["start_day"])).days


def feature_names(c: dict) -> list[str]:
    return [
        "lag_latest", "lag_7", "lag_14", "mean_7", "mean_28", "weather_latest",
        "annual_sin", "annual_cos", "weekly_sin", "weekly_cos",
        *["area_"+area for area in c["areas"]],
    ]


def load_contract(path: Path | None = None) -> dict:
    c = json.loads((path or ROOT / "contracts/forecast_contract.json").read_text())
    if c.get("synthetic_only") is not True or c.get("private_data_used") is not False or c.get("scientific_results_claimed") is not False:
        raise ValueError("synthetic claim contract violated")
    if c.get("version") != "1.0" or c.get("horizons") != [1, 7]:
        raise ValueError("unsupported version/horizons")
    if not c["areas"] or len(set(c["areas"])) != len(c["areas"]) or any(not re.fullmatch(r"SYN\d{3}", a) for a in c["areas"]):
        raise ValueError("fabricated area inventory required")
    date.fromisoformat(c["start_day"])
    integers = [
        "n_days", "warmup_days", "observation_lag_days", "weather_lag_days", "validation_days",
        "final_fit_index", "calibration_days", "deployment_index", "min_train_examples",
        "min_calibration_examples", "forest_trees", "forest_max_depth", "forest_min_leaf",
        "monitor_window_days", "min_monitor_labels",
    ]
    if any(type(c[k]) is not int or c[k] <= 0 for k in integers):
        raise ValueError("positive integer policy parameters required")
    if type(c["seed"]) is not int or c["seed"] < 0 or type(c["origin_hour_utc"]) is not int or not 0 <= c["origin_hour_utc"] <= 23:
        raise ValueError("invalid seed/origin hour")
    for k in ["ridge_alpha", "input_mean_shift_limit", "error_ratio_limit", "coverage_floor", "nominal_interval_coverage"]:
        if isinstance(c[k], bool) or not isinstance(c[k], (float, int)) or not math.isfinite(c[k]) or c[k] <= 0:
            raise ValueError("finite positive numeric policy required")
    if not 0 < c["coverage_floor"] < c["nominal_interval_coverage"] < 1:
        raise ValueError("invalid interval policy")
    fits = c["validation_fit_indices"]
    if not fits or any(type(x) is not int for x in fits) or fits != sorted(set(fits)):
        raise ValueError("ordered unique validation origins required")
    if c["warmup_days"] < 28+c["observation_lag_days"] or fits[0] <= c["warmup_days"]:
        raise ValueError("insufficient historical warmup")
    if any(a+c["validation_days"] > b for a, b in zip(fits, fits[1:])):
        raise ValueError("overlapping validation windows")
    latest_validation = fits[-1]+c["validation_days"]-1+max(c["horizons"])+c["observation_lag_days"]
    latest_calibration = c["final_fit_index"]+c["calibration_days"]-1+max(c["horizons"])+c["observation_lag_days"]
    if not latest_validation < c["final_fit_index"] < latest_calibration < c["deployment_index"] < c["n_days"]:
        raise ValueError("selection/calibration labels must mature before later stages")
    return c


def validate_records(rows: list[dict], c: dict) -> None:
    if not isinstance(rows, list) or not rows:
        raise ValueError("non-empty synthetic records required")
    ids = set()
    for row in rows:
        if set(row) != RAW_FIELDS:
            raise ValueError("raw schema mismatch; truth/unknown fields forbidden")
        identity = row["row_id"]
        if not isinstance(identity, str) or not re.fullmatch(r"OBS\d{6}", identity) or identity in ids:
            raise ValueError("invalid/duplicate row identity")
        ids.add(identity)
        if row["area_id"] not in c["areas"] or row["synthetic_record"] is not True:
            raise ValueError("fabricated inventory/marker required")
        day = row["event_day"]
        if not isinstance(day, str) or date.fromisoformat(day).isoformat() != day or not 0 <= index_of(day, c) < c["n_days"]:
            raise ValueError("invalid event day")
        for key in ["target_value", "weather"]:
            value = row[key]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError("finite numeric values required")
        if row["target_value"] < 0:
            raise ValueError("non-negative fabricated index required")
        end = utc(stamp(day_at(index_of(day, c)+1, c), 0))
        if any(utc(row[key]) < end for key in ["target_available_at", "weather_available_at"]):
            raise ValueError("completed daily observation cannot precede period end")
