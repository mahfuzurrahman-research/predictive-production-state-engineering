from copy import deepcopy
import json
import random

import numpy as np
import pytest
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge

from forecast_ml.contracts import day_at, feature_names, load_contract, stamp, validate_records
from forecast_ml.features import build_features, record_index
from forecast_ml.learning import calibrate, fit_at, forecast_holdout, label_at, predict_all, rolling_select


@pytest.mark.parametrize("field,value", [
    ("target_value", float("nan")), ("target_value", float("inf")),
    ("target_value", True), ("target_value", -1), ("weather", "3"),
    ("weather", float("nan")), ("synthetic_record", False),
])
def test_invalid_raw_values_fail_before_modeling(panel, field, value):
    c, rows = panel
    rows[0][field] = value
    with pytest.raises(ValueError):
        validate_records(rows, c)


def test_truth_and_duplicate_ids_are_rejected(panel):
    c, rows = panel
    rows[0]["injected_event"] = "NONE"
    with pytest.raises(ValueError, match="schema"):
        validate_records(rows, c)
    rows[0].pop("injected_event")
    rows[1]["row_id"] = rows[0]["row_id"]
    with pytest.raises(ValueError, match="identity"):
        validate_records(rows, c)


@pytest.mark.parametrize("edit", ["claim", "calendar", "overlap"])
def test_contract_prevents_unsafe_claims_or_stage_timing(tmp_path, edit):
    c = load_contract()
    if edit == "claim":
        c["private_data_used"] = True
    elif edit == "calendar":
        c["deployment_index"] = 320
    else:
        c["validation_fit_indices"] = [160, 180, 240]
    p = tmp_path / "contract.json"
    p.write_text(json.dumps(c))
    with pytest.raises(ValueError):
        load_contract(p)


@pytest.mark.parametrize("failure,reason", [
    ("missing", "MISSING_HISTORY"), ("duplicate", "DUPLICATE_HISTORY"),
    ("target_future", "TARGET_HISTORY_UNAVAILABLE"), ("weather_future", "WEATHER_UNAVAILABLE"),
])
def test_missing_duplicate_and_unavailable_history_is_blocked(panel, failure, reason):
    c, rows = panel
    day = day_at(100, c)
    row = next(r for r in rows if r["area_id"] == "SYN000" and r["event_day"] == day)
    if failure == "missing":
        rows.remove(row)
    elif failure == "duplicate":
        rows.append({**row, "row_id": "OBS900000"})
    elif failure == "target_future":
        row["target_available_at"] = stamp(day_at(103, c), 6)
    else:
        row["weather_available_at"] = stamp(day_at(103, c), 6)
    features, _ = build_features(rows, c)
    origin = 101 if failure == "weather_future" else 102
    affected = [f for f in features if f["area_id"] == "SYN000" and f["origin_day"] == day_at(origin,c)]
    assert len(affected) == 2
    assert all(not f["admitted"] and reason in f["reason_codes"] for f in affected)
    assert all(f["lag_latest"] is None and f["weather_latest"] is None for f in affected)


def test_future_targets_and_exogenous_values_cannot_change_earlier_features(panel, base_data):
    c, rows = panel
    for r in rows:
        if r["event_day"] >= day_at(300, c):
            r["target_value"] += 500
            r["weather"] += 100
    changed, _ = build_features(rows, c)
    original = base_data[2]
    assert [f for f in changed if f["origin_day"] <= day_at(300,c)] == [f for f in original if f["origin_day"] <= day_at(300,c)]


def test_input_row_order_does_not_change_features_or_lineage(panel, base_data):
    c, rows = panel
    random.Random(71).shuffle(rows)
    features, lineage = build_features(rows, c)
    assert features == base_data[2] and lineage == base_data[3]


def test_model_training_and_scaling_use_only_mature_training_rows(trained):
    t = trained
    assert all(a["label_available_at"] <= a["fit_at"] for a in t["audit"])
    by_id = {f["forecast_id"]: f for f in t["features"]}
    for horizon in t["c"]["horizons"]:
        models = t["pack"]["models"][horizon]
        assert isinstance(models["ridge"].steps[-1][1], Ridge)
        assert isinstance(models["random_forest"], RandomForestRegressor)
        ids = [a["forecast_id"] for a in t["pack"]["training_audit"] if a["horizon"] == horizon]
        expected = np.mean([[by_id[i][name] for name in feature_names(t["c"])] for i in ids], axis=0)
        assert np.allclose(models["ridge"].steps[0][1].mean_, expected, atol=1e-12)
        assert all(by_id[i]["origin_at"] < t["pack"]["fit_at"] for i in ids)


def test_late_training_label_is_excluded(panel, trained):
    c, rows = panel
    delayed = next(r for r in rows if r["area_id"] == "SYN000" and r["event_day"] == day_at(278,c))
    assert delayed["row_id"] in {a["label_row_id"] for a in trained["pack"]["training_audit"]}
    delayed["target_available_at"] = stamp(day_at(350,c), 6)
    features, _ = build_features(rows, c)
    pack = fit_at(features, record_index(rows), 280, c, "test")
    assert all(a["label_row_id"] != delayed["row_id"] for a in pack["training_audit"])


def test_holdout_changes_cannot_change_selection_or_fitted_predictions(panel, trained):
    c, rows = panel
    for r in rows:
        if r["event_day"] >= day_at(c["deployment_index"], c):
            r["target_value"] += 900
            r["weather"] += 200
    features, _ = build_features(rows, c)
    index = record_index(rows)
    selection, _, _ = rolling_select(features, index, c)
    pack = fit_at(features, index, c["final_fit_index"], c, "final")
    assert selection == trained["selection"]
    assert pack["training_sha256"] == trained["pack"]["training_sha256"]
    unchanged = [f for f in features if f["origin_day"] == day_at(c["deployment_index"], c)]
    original = [f for f in trained["features"] if f["origin_day"] == day_at(c["deployment_index"], c)]
    assert predict_all(pack, unchanged, c) == predict_all(trained["pack"], original, c)


def test_temporal_separation_extends_to_calibration(trained):
    t = trained
    assert all(r["model_fit_at"] <= r["origin_at"] for r in t["calibration"])
    assert all(r["label_available_at"] <= r["evaluation_as_of"] for r in t["calibration"] if r["label_status"] == "MATURE")
    training_labels = {a["label_row_id"] for a in t["pack"]["training_audit"]}
    assert not training_labels.intersection(r["label_row_id"] for r in t["calibration"])
    assert t["selection"]["holdout_used_for_selection"] is False


@pytest.mark.parametrize("corruption", ["policy", "features", "future_feature", "horizon", "future_model", "future_reference"])
def test_model_and_feature_temporal_integrity_is_enforced(trained, corruption):
    t = trained
    c = deepcopy(t["c"])
    pack = deepcopy(t["pack"])
    reference = deepcopy(t["reference"])
    rows = deepcopy([f for f in t["features"] if f["origin_day"] == day_at(c["deployment_index"], c)])
    if corruption == "policy":
        c["ridge_alpha"] = 10
    elif corruption == "features":
        pack["feature_names"].reverse()
    elif corruption == "future_feature":
        rows[0]["feature_max_available_at"] = stamp(day_at(419, c), 6)
    elif corruption == "horizon":
        rows[0]["target_day"] = rows[0]["origin_day"]
    elif corruption == "future_model":
        pack["fit_at"] = stamp(day_at(419,c), 7)
    else:
        reference["released_at"] = stamp(day_at(419,c), 7)
    with pytest.raises(ValueError):
        if corruption == "future_reference":
            forecast_holdout(pack, reference, rows, c)
        else:
            predict_all(pack, rows, c)


def test_label_is_not_visible_before_its_recorded_arrival(trained):
    t = trained
    p = t["predictions"][0]
    raw = t["index"][p["area_id"], p["target_day"]][0]
    before = raw["target_available_at"].replace("T06:", "T05:")
    pending = label_at(p, t["index"], before, t["c"])
    assert pending["label_status"] == "PENDING" and pending["actual"] is None
    available = label_at(p, t["index"], raw["target_available_at"], t["c"])
    assert available["label_status"] == "MATURE" and available["actual"] == raw["target_value"]


def test_insufficient_training_or_calibration_fails(trained):
    t = trained
    c = {**t["c"], "min_train_examples": 100000}
    with pytest.raises(ValueError, match="training"):
        fit_at(t["features"], t["index"], c["final_fit_index"], c, "test")
    c = {**t["c"], "min_calibration_examples": 100000}
    pack = {**t["pack"], "policy": c}
    with pytest.raises(ValueError, match="calibration"):
        calibrate(pack, t["selection"], t["features"], t["index"], c)
