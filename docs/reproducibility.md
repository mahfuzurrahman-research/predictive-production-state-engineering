# Reproducibility

## Local

```bash
python -m pip install -r requirements.txt
bash run_all_demos.sh
```

## Tests

```bash
python3 -m pytest -q tests tests_ml
```

## Docker

```bash
docker build -t predictive-production-state-engineering .
docker run --rm predictive-production-state-engineering
```

All scientific inputs used here are synthetic and generated inside the repository.

## ML run and verification

`bash run_ml_demo.sh` generates the ML stream, trains/evaluates candidates,
creates monitoring records, runs its tests and verifies the receipt. The original
demo remains available through `bash run_public_demo.sh`.

```bash
python3 -m forecast_ml.pipeline --output /tmp/synthetic-forecasts
python3 -m forecast_ml.pipeline --output /tmp/synthetic-forecasts --verify-only
```

| Artifact in `outputs/ml/` | Purpose |
|---|---|
| `synthetic_observations.csv` | Fabricated daily values and arrival timestamps |
| `synthetic_injection_truth.csv` | Scenario labels, separate from operational inputs |
| `features.csv`, `feature_lineage.csv` | Scheduled forecast features and source records |
| `training_audit.csv` | Fit origins and admitted target-label records |
| `validation_predictions.csv`, `selection.json` | Earlier rolling comparison and chosen systems |
| `calibration_predictions.csv`, `monitoring_reference.json` | Later error reference, bands and policy |
| `model_bundle.joblib` | Fitted estimators, preprocessing and training identity |
| `forecasts.csv` | Frozen holdout predictions, no target-label values |
| `holdout_evaluation.csv`, `holdout_summary.json` | Final as-of label evaluation and area/horizon metrics |
| `monitoring_windows.csv`, `monitoring_alerts.csv` | Input, delayed-label, quality and interval reviews |
| `quality.json`, `forecast.duckdb` | Independent relational checks and analytical marts |
| `manifest.json`, `run_receipt.json` | Recorded provenance and complete artifact hashes |

The manifest records source hashes, the policy, Python/dependency versions and
training-input hash. These record provenance; verification does not compare the
current working tree against the recorded source hashes. Per-file SHA-256 checks
detect a missing or modified artifact against its receipt. They are not signed
authenticity guarantees, and `joblib` must not load untrusted model files.

The fixed seed and pinned environment reproduce data CSV/JSON files, selected
systems and fitted predictions. DuckDB/model physical file bytes are not promised
identical across builds; each run records their own hashes. Saved-model replay
must reproduce holdout predictions exactly within the run.

Staging and all QA complete before replacing any prior completed run. The receipt
is published last; an interrupted publication is detectable by verification.
A failure during staging preserves the previous artifacts. A per-output process
lock rejects concurrent writers and releases on exit; its retained file is safe
to leave in place.

The workflow runs both demos plus Docker build/execution. A configured workflow
or a passing result for an older revision does not validate the new code.
