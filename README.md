# The Predictive Production State — Research Engineering Demonstration

A public engineering demonstration associated with **The Predictive Production State: Total Production Intelligence, Fiscal Anticipation, and Adaptive Public Resource Allocation**.

This repository demonstrates forecasting-oriented data engineering, temporal information controls, analytical warehousing, reproducible evaluation, failure-safe execution, automated testing, CI, Docker, and reporting using **fully synthetic data**.

> **Scientific boundary:** this repository does not contain the protected research dataset, protected forecast pairs, unpublished empirical results, historical production-engine source code, reserve data, manuscript text, or the private scientific repository history. It is an engineering demonstration only.

## Engineering capabilities demonstrated

- Python forecasting/evaluation pipeline
- strict as-of / temporal-information guards
- synthetic multi-origin forecast data
- baseline and adaptive forecast interfaces
- MAE, RMSE and pinball-loss evaluation
- DuckDB staging/core/mart architecture
- executable relational quality checks
- deterministic run receipts and SHA-256 integrity
- interruption / resume demonstration
- automated JSON and Markdown reporting
- static HTML dashboard generation
- unit, integration and failure-mode tests
- GitHub Actions CI
- Dockerized execution

## Architecture

```text
Synthetic release-vintage data
            │
            ▼
     Temporal admission
            │
            ▼
   Forecast-pair construction
            │
       ┌────┴────┐
       ▼         ▼
   Baseline   Adaptive demo
       │         │
       └────┬────┘
            ▼
     Evaluation metrics
            │
            ▼
      DuckDB warehouse
            │
            ▼
       Relational QA
            │
            ▼
 JSON / Markdown / HTML reporting
```

A separate synthetic reliability path demonstrates:

```text
Synthetic work units
        ↓
Atomic writes
        ↓
Per-unit receipts
        ↓
Intentional interruption
        ↓
Validated resume
        ↓
Deterministic merge
        ↓
Accepted artifact
```

## Quick start

```bash
python -m pip install -r requirements.txt
./run_public_demo.sh
```

Run tests:

```bash
python -m unittest discover -s tests -v
```

Build the container:

```bash
docker build -t predictive-production-state-engineering .
docker run --rm predictive-production-state-engineering
```

## Repository map

- `data/synthetic/` — generated public-safe demo data
- `src/forecast_demo/` — temporal guards, metrics, pipeline, recovery and reporting
- `sql/` — DuckDB schema, marts and relational QA
- `tests/` — unit, integration and failure-mode verification
- `dashboards/` — static HTML dashboard builder
- `docs/` — architecture, engineering scope, reproducibility and capability matrix
- `.github/workflows/` — public CI

## What this demonstrates

A reviewer can inspect and execute the full synthetic workflow from data generation through validation, forecast evaluation, warehouse construction, QA, reporting and recovery testing.

## What this does not disclose

- protected empirical data
- real archived forecast-pair values
- unpublished empirical coefficients or scores
- protected holdout/reserve results
- exact private model-selection logic
- private execution archives or provenance history
- manuscript text
- journal-submission materials

## Author

**Mahfuzur Rahman**  

See `COPYRIGHT.md` and `docs/engineering_scope.md`.
