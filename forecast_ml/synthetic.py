from __future__ import annotations

import math
import numpy as np

from .contracts import day_at, stamp


def generate(c: dict) -> tuple[list[dict], list[dict]]:
    rng = np.random.default_rng(c["seed"])
    rows, truth = [], []
    for area_index, area in enumerate(c["areas"]):
        weather = []
        for i in range(c["n_days"]):
            value = (0.6*weather[-1] if weather else 0)+float(rng.normal(0, 0.8))
            weather.append(value)
        for i in range(c["n_days"]):
            input_shift = 4.0 if i >= 365 else 0.0
            concept_shift = 25.0 if area_index == 2 and i >= 375 else 0.0
            lag_weather = weather[max(i-3, 0)]+(4.0 if i-3 >= 365 else 0.0)
            target = (100+10*area_index+18*math.sin(2*math.pi*i/365)
                      +5*math.cos(2*math.pi*i/365)+4*math.sin(2*math.pi*i/7)
                      +0.7*lag_weather+float(rng.normal(0, 1.2))+concept_shift)
            event = "NONE"
            if input_shift:
                event = "INPUT_SHIFT"
            if concept_shift:
                event = "INPUT_AND_CONCEPT_SHIFT"
            target_available = stamp(day_at(i+c["observation_lag_days"], c), 6)
            weather_available = stamp(day_at(i+c["weather_lag_days"], c), 6)
            if area_index == 3 and i == 350:
                target_available = stamp(day_at(i+20, c), 6)
                event = "LATE_TARGET_HISTORY"
            if area_index == 3 and i == 390:
                weather_available = stamp(day_at(i+5, c), 6)
                event = "LATE_WEATHER"
            truth.append({"area_id": area, "event_day": day_at(i, c), "injected_event": event})
            if area_index == 3 and i == 398:
                truth[-1]["injected_event"] = "MISSING_OBSERVATION"
                continue
            rows.append({
                "row_id": f"OBS{len(rows):06d}", "area_id": area, "event_day": day_at(i, c),
                "target_value": round(target, 6), "target_available_at": target_available,
                "weather": round(weather[i]+input_shift, 6), "weather_available_at": weather_available,
                "synthetic_record": True,
            })
    return rows, truth
