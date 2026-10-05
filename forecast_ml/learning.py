from __future__ import annotations

import hashlib
import json

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .contracts import day_at, feature_names, index_of, stamp

SYSTEMS = ("persistence", "seasonal_naive", "ridge", "random_forest")


def validate_features(rows: list[dict], c: dict) -> None:
    ids = set()
    for row in rows:
        if row["forecast_id"] in ids:
            raise ValueError("duplicate forecast identity")
        ids.add(row["forecast_id"])
        origin = index_of(row["origin_day"], c)
        if row["horizon"] not in c["horizons"] or row["target_day"] != day_at(origin+row["horizon"], c):
            raise ValueError("forecast horizon mismatch")
        if row["origin_at"] != stamp(row["origin_day"], c["origin_hour_utc"]):
            raise ValueError("forecast origin timestamp mismatch")
        if row["admitted"] and (row["feature_max_available_at"] is None or row["feature_max_available_at"] > row["origin_at"]):
            raise ValueError("feature unavailable at forecast origin")


def matrix(rows: list[dict], c: dict) -> np.ndarray:
    values = np.asarray([[r[k] for k in feature_names(c)] for r in rows], dtype=float)
    if values.ndim != 2 or values.shape[1] != len(feature_names(c)) or not np.isfinite(values).all():
        raise ValueError("finite declared feature matrix required")
    return values


def label_at(forecast: dict, raw_index: dict, as_of: str, c: dict) -> dict:
    records = raw_index.get((forecast["area_id"], forecast["target_day"]), [])
    result = {"actual": None, "label_row_id": None, "label_available_at": None, "label_status": "PENDING"}
    if len(records) > 1:
        result["label_status"] = "DUPLICATE_LABEL"
    elif not records:
        expected = stamp(day_at(index_of(forecast["target_day"], c)+c["observation_lag_days"], c), 6)
        if expected <= as_of:
            result["label_status"] = "MISSING_LABEL"
    elif records[0]["target_available_at"] <= as_of:
        r = records[0]
        result.update(actual=r["target_value"], label_row_id=r["row_id"], label_available_at=r["target_available_at"], label_status="MATURE")
    return result


def fit_at(features: list[dict], raw_index: dict, fit_index: int, c: dict, tag: str) -> dict:
    validate_features(features, c)
    fit_time = stamp(day_at(fit_index, c), c["origin_hour_utc"])
    pack = {"policy": json.loads(json.dumps(c)), "feature_names": feature_names(c), "fit_at": fit_time, "models": {}, "training_audit": []}
    hash_rows = []
    for horizon in c["horizons"]:
        eligible = []
        for f in features:
            if not f["admitted"] or f["horizon"] != horizon or f["origin_at"] >= fit_time:
                continue
            label = label_at(f, raw_index, fit_time, c)
            if label["label_status"] == "MATURE":
                eligible.append((f, label))
        if len(eligible) < c["min_train_examples"]:
            raise ValueError("insufficient mature training examples")
        x = matrix([f for f, _ in eligible], c)
        y = np.asarray([l["actual"] for _, l in eligible], dtype=float)
        ridge = make_pipeline(StandardScaler(), Ridge(alpha=c["ridge_alpha"]))
        forest = RandomForestRegressor(
            n_estimators=c["forest_trees"], max_depth=c["forest_max_depth"],
            min_samples_leaf=c["forest_min_leaf"], random_state=c["seed"], n_jobs=1,
        )
        ridge.fit(x, y)
        forest.fit(x, y)
        pack["models"][horizon] = {"ridge": ridge, "random_forest": forest}
        for f, label in eligible:
            pack["training_audit"].append({
                "fit_tag": tag, "fit_at": fit_time, "horizon": horizon,
                "forecast_id": f["forecast_id"], "label_row_id": label["label_row_id"],
                "label_available_at": label["label_available_at"],
            })
            hash_rows.append([f["forecast_id"], [f[k] for k in feature_names(c)], label["actual"], label["label_available_at"]])
    pack["training_sha256"] = hashlib.sha256(json.dumps(hash_rows, allow_nan=False).encode()).hexdigest()
    return pack


def predict_all(pack: dict, rows: list[dict], c: dict) -> list[dict]:
    validate_features(rows, c)
    if pack.get("policy") != c or pack.get("feature_names") != feature_names(c):
        raise ValueError("frozen model policy/feature order mismatch")
    if any(r["origin_at"] < pack["fit_at"] for r in rows):
        raise ValueError("model unavailable at forecast origin")
    predictions = {}
    for h in c["horizons"]:
        admitted = [r for r in rows if r["horizon"] == h and r["admitted"]]
        if not admitted:
            continue
        x = matrix(admitted, c)
        ridge = pack["models"][h]["ridge"].predict(x)
        forest = pack["models"][h]["random_forest"].predict(x)
        for row, r, f in zip(admitted, ridge, forest):
            predictions[row["forecast_id"]] = {
                "persistence": row["lag_latest"], "seasonal_naive": row["seasonal_naive"],
                "ridge": float(r), "random_forest": float(f),
            }
    return [{
        **{k: row[k] for k in ["forecast_id", "area_id", "origin_day", "origin_at", "target_day", "horizon", "admitted", "reason_codes"]},
        "model_fit_at": pack["fit_at"],
        **predictions.get(row["forecast_id"], {name: None for name in SYSTEMS}),
    } for row in rows]


def metrics(actual: list[float], prediction: list[float]) -> dict:
    if not actual or len(actual) != len(prediction):
        raise ValueError("non-empty equal-length evaluation vectors required")
    residual = np.asarray(actual, dtype=float)-np.asarray(prediction, dtype=float)
    if not np.isfinite(residual).all():
        raise ValueError("finite evaluation values required")
    return {"n": len(actual), "mae": float(np.mean(np.abs(residual))), "rmse": float(np.sqrt(np.mean(residual**2))), "bias_actual_minus_prediction": float(np.mean(residual))}


def rolling_select(features: list[dict], raw_index: dict, c: dict) -> tuple[dict, list[dict], list[dict]]:
    evaluated, audits = [], []
    selection_at = stamp(day_at(c["final_fit_index"], c), c["origin_hour_utc"])
    for number, cutoff in enumerate(c["validation_fit_indices"], 1):
        pack = fit_at(features, raw_index, cutoff, c, f"validation-{number}")
        audits.extend(pack["training_audit"])
        valid = [f for f in features if cutoff <= index_of(f["origin_day"], c) < cutoff+c["validation_days"]]
        for forecast in predict_all(pack, valid, c):
            evaluated.append({"fold": number, "evaluation_as_of": selection_at, **forecast, **label_at(forecast, raw_index, selection_at, c)})
    scores, selected = [], {}
    for h in c["horizons"]:
        rows = [r for r in evaluated if r["horizon"] == h and r["admitted"] and r["label_status"] == "MATURE"]
        if len(rows) < c["min_calibration_examples"]:
            raise ValueError("insufficient mature validation labels")
        horizon_scores = []
        for system in SYSTEMS:
            score = {"horizon": h, "system": system, **metrics([r["actual"] for r in rows], [r[system] for r in rows])}
            scores.append(score)
            horizon_scores.append(score)
        selected[str(h)] = min(horizon_scores, key=lambda s: (s["mae"], s["system"]))["system"]
    return {
        "selection_as_of": selection_at, "criterion": "pooled rolling-validation MAE per horizon; lexical tie break",
        "scores": scores, "selected": selected, "holdout_used_for_selection": False,
        "fold_fit_indices": c["validation_fit_indices"],
    }, evaluated, audits


def calibrate(pack: dict, selection: dict, features: list[dict], raw_index: dict, c: dict) -> tuple[dict, list[dict]]:
    release = stamp(day_at(c["deployment_index"], c), c["origin_hour_utc"])
    rows = [f for f in features if c["final_fit_index"] <= index_of(f["origin_day"], c) < c["final_fit_index"]+c["calibration_days"]]
    calibration = [{"evaluation_as_of": release, **p, **label_at(p, raw_index, release, c)} for p in predict_all(pack, rows, c)]
    feature_by_id = {f["forecast_id"]: f for f in features}
    reference = {
        "policy": json.loads(json.dumps(c)), "feature_names": feature_names(c),
        "released_at": release, "model_fit_at": pack["fit_at"], "selected": selection["selected"],
        "training_sha256": pack["training_sha256"], "horizons": {},
        "interval_method": "historical absolute-error quantile; empirical band without time-series coverage guarantee",
    }
    for h in c["horizons"]:
        selected = selection["selected"][str(h)]
        eligible = [r for r in calibration if r["horizon"] == h and r["admitted"] and r["label_status"] == "MATURE"]
        if len(eligible) < c["min_calibration_examples"]:
            raise ValueError("insufficient mature calibration labels")
        errors = [abs(r["actual"]-r[selected]) for r in eligible]
        training = [feature_by_id[r["forecast_id"]] for r in pack["training_audit"] if r["horizon"] == h]
        profiles = {}
        for name in ["weather_latest", "lag_latest"]:
            values = np.asarray([f[name] for f in training])
            profiles[name] = {"mean": float(np.mean(values)), "sd": max(float(np.std(values, ddof=1)), 1e-6)}
        reference["horizons"][str(h)] = {
            "calibration_n": len(eligible), "calibration_latest_label_at": max(r["label_available_at"] for r in eligible),
            "reference_mae": max(float(np.mean(errors)), 1e-6),
            "interval_half_width": float(np.quantile(errors, c["nominal_interval_coverage"], method="higher")),
            "input_profiles": profiles,
        }
    identity = hashlib.sha256(json.dumps({"reference": reference, "selection": selection}, sort_keys=True, allow_nan=False).encode()).hexdigest()[:16]
    reference["model_id"] = "forecast-v1-"+identity
    pack["model_id"] = reference["model_id"]
    return reference, calibration


def forecast_holdout(pack: dict, reference: dict, features: list[dict], c: dict) -> list[dict]:
    if reference.get("policy") != c or reference.get("feature_names") != feature_names(c) or reference.get("model_id") != pack.get("model_id"):
        raise ValueError("frozen monitoring reference mismatch")
    later = [f for f in features if index_of(f["origin_day"], c) >= c["deployment_index"]]
    if any(f["origin_at"] < reference["released_at"] for f in later):
        raise ValueError("calibration/reference unavailable at deployment origin")
    output = []
    for row in predict_all(pack, later, c):
        selected = reference["selected"][str(row["horizon"])]
        prediction = row[selected]
        width = reference["horizons"][str(row["horizon"])]["interval_half_width"]
        output.append({
            **row, "model_id": reference["model_id"], "reference_released_at": reference["released_at"],
            "selected_model": selected, "prediction": prediction,
            "lower": prediction-width if row["admitted"] else None,
            "upper": prediction+width if row["admitted"] else None,
        })
    return output
