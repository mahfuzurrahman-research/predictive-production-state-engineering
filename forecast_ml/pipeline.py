from __future__ import annotations

import argparse
from collections import Counter
import csv
import fcntl
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
import tempfile

import joblib

from .contracts import ROOT, load_contract
from .features import build_features, record_index
from .learning import calibrate, fit_at, forecast_holdout, rolling_select
from .monitoring import evaluate_holdout, monitor_windows
from .synthetic import generate
from .warehouse import build

DATA_ARTIFACTS = (
    "synthetic_observations.csv", "synthetic_injection_truth.csv", "features.csv", "feature_lineage.csv",
    "training_audit.csv", "validation_predictions.csv", "selection.json", "calibration_predictions.csv",
    "model_bundle.joblib", "monitoring_reference.json", "forecasts.csv", "holdout_evaluation.csv",
    "holdout_summary.json", "monitoring_windows.csv", "monitoring_alerts.csv", "quality.json", "forecast.duckdb",
)
RECEIPT_ARTIFACTS = (*DATA_ARTIFACTS, "manifest.json")
ALERT_FIELDS = ["alert_id", "window_id", "alert_type", "observed_at", "model_id", "details", "recommended_action", "review_status", "automatic_retraining_authorized"]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+"\n")


def write_csv(path: Path, rows: list[dict], fields: list[str] | None = None) -> None:
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def verify_receipt(output: Path) -> dict:
    receipt = json.loads((output / "run_receipt.json").read_text())
    if receipt.get("status") != "PASS" or set(receipt.get("artifacts", {})) != set(RECEIPT_ARTIFACTS):
        raise ValueError("incomplete ML forecast receipt")
    for name in RECEIPT_ARTIFACTS:
        path = output / name
        if not path.is_file() or digest(path) != receipt["artifacts"][name]:
            raise ValueError("ML forecast integrity failure: "+name)
    reference = json.loads((output / "monitoring_reference.json").read_text())
    manifest = json.loads((output / "manifest.json").read_text())
    if reference["model_id"] != receipt["model_id"] or manifest["model_id"] != receipt["model_id"] or manifest["synthetic_only"] is not True:
        raise ValueError("model/reference manifest mismatch")
    return receipt


def _stage(output: Path, c: dict) -> dict:
    rows, truth = generate(c)
    features, lineage = build_features(rows, c)
    index = record_index(rows)
    selection, validation, audit = rolling_select(features, index, c)
    pack = fit_at(features, index, c["final_fit_index"], c, "final")
    audit.extend(pack["training_audit"])
    reference, calibration = calibrate(pack, selection, features, index, c)
    forecasts = forecast_holdout(pack, reference, features, c)
    evaluated, summary = evaluate_holdout(forecasts, index, c)
    windows, alerts = monitor_windows(forecasts, features, reference, index, c)
    joblib.dump(pack, output / "model_bundle.joblib", compress=3)
    write_json(output / "monitoring_reference.json", reference)
    # Load only this freshly generated, trusted model; CLI receipt verification
    # never deserializes external model files.
    restored = joblib.load(output / "model_bundle.joblib")
    restored_reference = json.loads((output / "monitoring_reference.json").read_text())
    replay = forecast_holdout(restored, restored_reference, features, c)
    if replay != forecasts:
        raise ValueError("persisted-model forecast replay mismatch")
    qa = build(output / "forecast.duckdb", rows, features, lineage, audit, forecasts, evaluated, summary, alerts, c)
    quality = {
        **qa, "raw_records": len(rows), "feature_rows": len(features),
        "blocked_feature_rows": sum(not f["admitted"] for f in features),
        "holdout_forecasts": len(forecasts), "blocked_holdout_forecasts": sum(not p["admitted"] for p in forecasts),
        "reason_counts": dict(Counter(code for f in features for code in json.loads(f["reason_codes"]))),
        "saved_model_replay_equal": True,
    }
    for name, data in [
        ("synthetic_observations.csv", rows), ("synthetic_injection_truth.csv", truth),
        ("features.csv", features), ("feature_lineage.csv", lineage), ("training_audit.csv", audit),
        ("validation_predictions.csv", validation), ("calibration_predictions.csv", calibration),
        ("forecasts.csv", forecasts), ("holdout_evaluation.csv", evaluated), ("monitoring_windows.csv", windows),
    ]:
        write_csv(output / name, data)
    write_csv(output / "monitoring_alerts.csv", alerts, ALERT_FIELDS)
    for name, data in [("selection.json", selection), ("holdout_summary.json", summary), ("quality.json", quality)]:
        write_json(output / name, data)
    sources = sorted([*ROOT.glob("forecast_ml/*.py"), ROOT / "contracts/forecast_contract.json", ROOT / "sql/ml_forecasting.sql", ROOT / "requirements.txt", ROOT / "run_ml_demo.sh"])
    manifest = {
        "synthetic_only": True, "scientific_results_claimed": False, "model_id": reference["model_id"],
        "policy": c, "training_sha256": pack["training_sha256"], "python": platform.python_version(),
        "dependencies": {name: version(name) for name in ["numpy", "scikit-learn", "scipy", "joblib", "threadpoolctl", "duckdb", "pandas", "pytest"]},
        "source_sha256": {str(p.relative_to(ROOT)): digest(p) for p in sources},
        "determinism": "CSV/JSON data, fitted predictions and model identity in the pinned environment; database/model physical bytes not guaranteed",
    }
    write_json(output / "manifest.json", manifest)
    receipt = {
        "status": "PASS", "model_id": reference["model_id"],
        "artifacts": {name: digest(output / name) for name in RECEIPT_ARTIFACTS},
        "checks": {"independent_sql": True, "saved_model_replay_equal": True},
        "boundary": "synthetic engineering execution; no scientific or production validation",
    }
    write_json(output / "run_receipt.json", receipt)
    verify_receipt(output)
    return receipt


def run(output: Path = ROOT / "outputs/ml") -> dict:
    output.mkdir(parents=True, exist_ok=True)
    with (output / ".forecast_demo.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as e:
            raise RuntimeError("ML forecast writer already running for this directory") from e
        try:
            with tempfile.TemporaryDirectory(prefix=".stage-", dir=output) as tmp:
                stage = Path(tmp)
                receipt = _stage(stage, load_contract())
                for name in (*RECEIPT_ARTIFACTS, "run_receipt.json"):
                    os.replace(stage / name, output / name)
            verify_receipt(output)
            return receipt
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def main() -> None:
    parser = argparse.ArgumentParser(description="Synthetic ML forecasting demonstration")
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/ml")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    receipt = verify_receipt(args.output) if args.verify_only else run(args.output)
    print(f"ML_FORECAST_STATUS={receipt['status']} model={receipt['model_id']}")


if __name__ == "__main__":
    main()
