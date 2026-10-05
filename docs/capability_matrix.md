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
