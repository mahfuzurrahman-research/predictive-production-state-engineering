from __future__ import annotations

from collections import Counter
import json

import numpy as np

from .contracts import day_at, index_of, stamp
from .learning import SYSTEMS, label_at, metrics


def evaluate_holdout(predictions: list[dict], raw_index: dict, c: dict) -> tuple[list[dict], dict]:
    as_of = stamp(day_at(c["n_days"]-1, c), c["origin_hour_utc"])
    evaluated = [{
        "evaluation_as_of": as_of, **p,
        **(label_at(p, raw_index, as_of, c) if p["admitted"] else {
            "actual": None, "label_row_id": None, "label_available_at": None, "label_status": "BLOCKED_FORECAST",
        }),
    } for p in predictions]
    admitted = [p for p in evaluated if p["admitted"]]
    mature = [p for p in admitted if p["label_status"] == "MATURE"]
    scores, segments = [], []
    for h in c["horizons"]:
        selected = [p for p in mature if p["horizon"] == h]
        for system in (*SYSTEMS, "prediction"):
            if selected:
                scores.append({"horizon": h, "system": "selected" if system == "prediction" else system,
                               **metrics([p["actual"] for p in selected], [p[system] for p in selected])})
        for area in c["areas"]:
            rows = [p for p in selected if p["area_id"] == area]
            if rows:
                segments.append({"horizon": h, "area_id": area,
                    **metrics([p["actual"] for p in rows], [p["prediction"] for p in rows]),
                    "empirical_interval_coverage": float(np.mean([p["lower"] <= p["actual"] <= p["upper"] for p in rows])),
                })
    return evaluated, {
        "scope": "fixed-seed synthetic holdout; no real-world or scientific forecast claim",
        "evaluation_as_of": as_of, "holdout_used_for_selection": False,
        "scheduled_forecasts": len(predictions), "blocked_forecasts": len(predictions)-len(admitted),
        "mature_forecasts": len(mature), "unscored_label_status_counts": dict(Counter(p["label_status"] for p in admitted if p["label_status"] != "MATURE")),
        "scores": scores, "selected_model_area_segments": segments,
        "interval_nominal_coverage": c["nominal_interval_coverage"],
        "interval_coverage_guaranteed": False,
    }


def monitor_windows(predictions: list[dict], features: list[dict], reference: dict, raw_index: dict, c: dict) -> tuple[list[dict], list[dict]]:
    if reference.get("policy") != c:
        raise ValueError("frozen monitoring policy mismatch")
    by_id = {f["forecast_id"]: f for f in features}
    records, alerts = [], []
    previous_as_of = reference["released_at"]
    for start in range(c["deployment_index"], c["n_days"], c["monitor_window_days"]):
        end = min(start+c["monitor_window_days"], c["n_days"])
        as_of = stamp(day_at(min(end, c["n_days"]-1), c), c["origin_hour_utc"])
        for h in c["horizons"]:
            issued = [p for p in predictions if p["horizon"] == h and start <= index_of(p["origin_day"], c) < end]
            admitted = [p for p in issued if p["admitted"]]
            pending = sum(label_at(p, raw_index, as_of, c)["label_status"] == "PENDING" for p in admitted)
            # Performance cohorts use label ARRIVAL time. Pending forecasts from
            # an earlier issue window are assessed when their labels mature.
            matured = []
            missing_labels = 0
            for p in predictions:
                if p["horizon"] != h or not p["admitted"] or p["origin_at"] > as_of:
                    continue
                label = label_at(p, raw_index, as_of, c)
                missing_labels += label["label_status"] in {"MISSING_LABEL", "DUPLICATE_LABEL"}
                if label["label_status"] == "MATURE" and previous_as_of < label["label_available_at"] <= as_of:
                    matured.append({**p, **label})
            profiles = reference["horizons"][str(h)]
            shifts = {}
            for name, profile in profiles["input_profiles"].items():
                shifts[name] = abs(float(np.mean([by_id[p["forecast_id"]][name] for p in admitted]))-profile["mean"])/profile["sd"] if admitted else None
            error = coverage = ratio = None
            performance_status = "INSUFFICIENT_MATURE_LABELS"
            if len(matured) >= c["min_monitor_labels"]:
                error = metrics([p["actual"] for p in matured], [p["prediction"] for p in matured])["mae"]
                coverage = float(np.mean([p["lower"] <= p["actual"] <= p["upper"] for p in matured]))
                ratio = error/profiles["reference_mae"]
                performance_status = "ASSESSED"
            row = {
                "window_id": f"{day_at(start,c)}:h{h}", "horizon": h,
                "window_start": day_at(start, c), "window_end": day_at(end-1, c),
                "evaluation_as_of": as_of, "model_id": reference["model_id"],
                "issued_forecasts": len(issued), "blocked_forecasts": len(issued)-len(admitted),
                "pending_labels_in_issue_window": pending, "newly_mature_labels": len(matured),
                "unresolved_missing_or_duplicate_labels": missing_labels,
                "performance_status": performance_status, "mae": error,
                "error_ratio": ratio, "empirical_interval_coverage": coverage,
                "weather_mean_shift": shifts["weather_latest"], "lag_mean_shift": shifts["lag_latest"],
            }
            records.append(row)
            causes = []
            if row["blocked_forecasts"]:
                causes.append(("DATA_QUALITY", {"blocked_forecasts": row["blocked_forecasts"]}, "CHECK_FEED"))
            if missing_labels:
                causes.append(("LABEL_QUALITY", {"unresolved_labels": missing_labels}, "CHECK_LABEL_FEED"))
            for name, shift in shifts.items():
                if shift is not None and shift >= c["input_mean_shift_limit"]:
                    causes.append(("INPUT_DRIFT:"+name, {"standardized_mean_shift": shift}, "REVIEW_INPUT_DISTRIBUTION"))
            if ratio is not None and ratio >= c["error_ratio_limit"]:
                causes.append(("ERROR_DEGRADATION", {"error_ratio": ratio, "mature_labels": len(matured)}, "REVIEW_FORECAST_ERRORS"))
            if coverage is not None and coverage < c["coverage_floor"]:
                causes.append(("INTERVAL_UNDERCOVERAGE", {"coverage": coverage, "mature_labels": len(matured)}, "REVIEW_INTERVAL_CALIBRATION"))
            for kind, detail, action in causes:
                alerts.append({
                    "alert_id": row["window_id"]+":"+kind, "window_id": row["window_id"],
                    "alert_type": kind, "observed_at": as_of, "model_id": reference["model_id"],
                    "details": json.dumps(detail, sort_keys=True, allow_nan=False),
                    "recommended_action": action, "review_status": "PENDING_REVIEW",
                    "automatic_retraining_authorized": False,
                })
        previous_as_of = as_of
    return records, alerts
