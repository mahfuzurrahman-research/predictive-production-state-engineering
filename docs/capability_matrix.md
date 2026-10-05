# Capability matrix

| Capability | Public evidence |
|---|---|
| Python | `src/forecast_demo/` |
| Temporal validation | `src/forecast_demo/temporal.py` |
| Forecast evaluation | `src/forecast_demo/metrics.py`, `pipeline.py` |
| SQL / DuckDB | `sql/` |
| Relational QA | `sql/quality_checks.sql` |
| Recovery engineering | `src/forecast_demo/recovery.py` |
| Failure-mode testing | `tests/test_recovery.py`, `tests/test_public_boundary.py` |
| Automated reporting | `src/forecast_demo/reporting.py` |
| Dashboard | `dashboards/build_dashboard.py` |
| CI | `.github/workflows/public-validation.yml` |
| Docker | `Dockerfile` |
| Reproducibility | `docs/reproducibility.md` |
| Fitted ML forecasting | ridge pipeline and random forest in `forecast_ml/learning.py` |
| Baseline comparison | persistence/seasonal-naive forecasts; rolling and holdout metrics |
| Delayed-label temporal validation | `label_at`, training audits and explicit fit origins |
| As-of feature construction | `forecast_ml/features.py`, observation arrival times and lineage |
| Calibration/holdout separation | `contracts/forecast_contract.json`, frozen monitoring reference |
| Model monitoring | input drift, label-arrival cohorts, error and interval alerts |
| Independent numerical verification | feature reconstruction and metric parity in `sql/ml_forecasting.sql` |
| Artifact replay and failure handling | saved-model replay, complete receipts, process lock and staging tests |
| Bounded CV claims | `docs/cv_evidence.md`, observed validation and model limitations |

Passing synthetic tests demonstrates engineering behavior. It does not establish
scientific validity, real forecasting performance or production deployment.
