from copy import deepcopy
import fcntl
import json
import shutil

import duckdb
import pytest

from forecast_ml import pipeline
from forecast_ml.warehouse import build


def warehouse(t, path, **changes):
    inputs = {name: t[name] for name in ["rows", "features", "lineage", "audit", "predictions", "evaluated", "summary", "alerts", "c"]}
    inputs.update(changes)
    return build(path, **inputs)


def test_sql_independently_rebuilds_features_and_forecast_metrics(trained, tmp_path):
    path = tmp_path / "forecasts.duckdb"
    qa = warehouse(trained, path)
    assert qa["status"] == "PASS" and len(qa["checks"]) == 15 and not any(qa["checks"].values())
    with duckdb.connect(str(path), read_only=True) as con:
        assert con.execute("SELECT COUNT(*) FROM mart.ml_metric_summary").fetchone()[0] == 10
        assert con.execute("SELECT COUNT(*) FROM ml_training_audit WHERE label_available_at>fit_at").fetchone()[0] == 0


@pytest.mark.parametrize("corruption", ["future_feature", "feature_value", "training_label", "prediction", "metric", "missing_forecast"])
def test_sql_rejects_temporal_numerical_and_inventory_corruption(trained, tmp_path, corruption):
    changes = {}
    if corruption in {"future_feature", "feature_value"}:
        rows = deepcopy(trained["rows"])
        if corruption == "future_feature":
            rows[10]["target_available_at"] = "2099-01-01T06:00:00Z"
        else:
            rows[10]["target_value"] += 20
        changes["rows"] = rows
    elif corruption == "training_label":
        audit = deepcopy(trained["audit"])
        audit[0]["fit_at"] = "2023-01-01T07:00:00Z"
        changes["audit"] = audit
    elif corruption in {"prediction", "missing_forecast"}:
        predictions = deepcopy(trained["predictions"])
        if corruption == "prediction":
            predictions[0]["prediction"] = None
        else:
            predictions.pop(0)
        changes["predictions"] = predictions
    else:
        summary = deepcopy(trained["summary"])
        summary["scores"][0]["mae"] += 1
        changes["summary"] = summary
    with pytest.raises(ValueError, match="warehouse QA"):
        warehouse(trained, tmp_path / "corrupted.duckdb", **changes)


@pytest.fixture(scope="module")
def completed(tmp_path_factory):
    path = tmp_path_factory.mktemp("ml-forecast")
    pipeline.run(path)
    return path


def test_end_to_end_default_models_replay_and_integrity(completed):
    receipt = pipeline.verify_receipt(completed)
    assert receipt["status"] == "PASS"
    qa = json.loads((completed / "quality.json").read_text())
    assert qa["saved_model_replay_equal"] and qa["total_failures"] == 0
    assert qa["holdout_forecasts"] == 704 and qa["blocked_holdout_forecasts"] > 0
    selection = json.loads((completed / "selection.json").read_text())
    assert selection["holdout_used_for_selection"] is False and len(selection["scores"]) == 8
    for name in ["synthetic_observations.csv", "features.csv", "forecasts.csv", "monitoring_reference.json", "monitoring_alerts.csv"]:
        assert "injected_event" not in (completed / name).read_text()
    assert "actual" not in (completed / "forecasts.csv").read_text().splitlines()[0]


def test_repeated_runs_produce_same_data_predictions_and_identity(completed, tmp_path):
    pipeline.run(tmp_path)
    for name in pipeline.DATA_ARTIFACTS:
        if name.endswith((".csv", ".json")):
            assert (completed / name).read_bytes() == (tmp_path / name).read_bytes()
    assert (completed / "manifest.json").read_bytes() == (tmp_path / "manifest.json").read_bytes()


def test_modified_model_or_incomplete_receipt_is_rejected(completed, tmp_path):
    for name in (*pipeline.RECEIPT_ARTIFACTS, "run_receipt.json"):
        shutil.copyfile(completed / name, tmp_path / name)
    (tmp_path / "model_bundle.joblib").write_bytes(b"not a model")
    with pytest.raises(ValueError, match="integrity"):
        pipeline.verify_receipt(tmp_path)
    receipt = json.loads((tmp_path / "run_receipt.json").read_text())
    receipt["artifacts"].pop("model_bundle.joblib")
    pipeline.write_json(tmp_path / "run_receipt.json", receipt)
    with pytest.raises(ValueError, match="incomplete"):
        pipeline.verify_receipt(tmp_path)


def test_failed_staging_preserves_completed_run_and_releases_lock(completed, monkeypatch):
    original = pipeline.verify_receipt(completed)
    def fail(stage, c):
        (stage / "forecasts.csv").write_text("partial")
        raise RuntimeError("simulated failure")
    with monkeypatch.context() as patch:
        patch.setattr(pipeline, "_stage", fail)
        with pytest.raises(RuntimeError, match="simulated"):
            pipeline.run(completed)
    assert pipeline.verify_receipt(completed) == original
    assert not list(completed.glob(".stage-*"))
    with (completed / ".forecast_demo.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(lock, fcntl.LOCK_UN)


def test_concurrent_writer_is_rejected(completed):
    with (completed / ".forecast_demo.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            with pytest.raises(RuntimeError, match="already running"):
                pipeline.run(completed)
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)
