from __future__ import annotations

from collections import defaultdict
import json
import math
from statistics import mean

from .contracts import day_at, feature_names, stamp, validate_records


def record_index(rows: list[dict]) -> dict:
    index = defaultdict(list)
    for row in rows:
        index[row["area_id"], row["event_day"]].append(row)
    return index


def build_features(rows: list[dict], c: dict) -> tuple[list[dict], list[dict]]:
    validate_records(rows, c)
    index = record_index(rows)
    output, lineage = [], []
    for origin in range(c["warmup_days"], c["n_days"]):
        origin_at = stamp(day_at(origin, c), c["origin_hour_utc"])
        latest = origin-c["observation_lag_days"]
        for area in c["areas"]:
            history = [index[area, day_at(i, c)] for i in range(latest-27, latest+1)]
            weather = index[area, day_at(origin-c["weather_lag_days"], c)]
            reasons = []
            if any(not group for group in [*history, weather]):
                reasons.append("MISSING_HISTORY")
            if any(len(group) > 1 for group in [*history, weather]):
                reasons.append("DUPLICATE_HISTORY")
            if any(r["target_available_at"] > origin_at for group in history for r in group):
                reasons.append("TARGET_HISTORY_UNAVAILABLE")
            if any(r["weather_available_at"] > origin_at for r in weather):
                reasons.append("WEATHER_UNAVAILABLE")
            admitted = not reasons
            source = [group[0] for group in history] if admitted else []
            for horizon in c["horizons"]:
                target_index = origin+horizon
                identity = f"{area}:{day_at(origin,c)}:h{horizon}"
                values = {name: None for name in feature_names(c)}
                seasonal = None
                if admitted:
                    counts = [r["target_value"] for r in source]
                    values.update({
                        "lag_latest": counts[-1], "lag_7": counts[-8], "lag_14": counts[-15],
                        "mean_7": mean(counts[-7:]), "mean_28": mean(counts),
                        "weather_latest": weather[0]["weather"],
                        "annual_sin": math.sin(2*math.pi*target_index/365),
                        "annual_cos": math.cos(2*math.pi*target_index/365),
                        "weekly_sin": math.sin(2*math.pi*target_index/7),
                        "weekly_cos": math.cos(2*math.pi*target_index/7),
                        **{"area_"+a: float(a == area) for a in c["areas"]},
                    })
                    seasonal_index = latest-((latest-target_index) % 7)
                    seasonal = source[seasonal_index-(latest-27)]["target_value"]
                    for r in source:
                        lineage.append({"forecast_id": identity, "row_id": r["row_id"], "source_kind": "TARGET_HISTORY"})
                    lineage.append({"forecast_id": identity, "row_id": weather[0]["row_id"], "source_kind": "WEATHER_HISTORY"})
                output.append({
                    "forecast_id": identity, "area_id": area, "origin_day": day_at(origin, c),
                    "origin_at": origin_at, "target_day": day_at(target_index, c), "horizon": horizon,
                    "admitted": admitted, "reason_codes": json.dumps(sorted(reasons), separators=(",", ":")),
                    "feature_max_available_at": max([r["target_available_at"] for r in source]+[weather[0]["weather_available_at"]]) if admitted else None,
                    "seasonal_naive": seasonal, **values,
                })
    return output, lineage
