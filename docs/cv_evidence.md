# Supported CV evidence

The upgraded code supports this project bullet:

> Built a synthetic ML forecasting pipeline in Python, scikit-learn and DuckDB,
> comparing ridge and random-forest models with simple baselines using rolling
> temporal validation, delayed-label controls and model monitoring.

A more detailed engineering description:

> Implemented as-of lag features, training-only preprocessing, horizon-specific
> model selection, separate calibration/holdout evaluation, drift and error
> monitoring, independent SQL checks and saved-model replay on fabricated data.

| Claim | Evidence |
|---|---|
| Fitted ML models | `forecast_ml/learning.py`: fitted ridge/scaler and random forest |
| Temporal validation | explicit rolling origins, mature-label training audit, future-perturbation tests |
| Model comparison | persistence/seasonal baselines, validation and holdout score tables |
| Monitoring | logged input profiles, label-arrival cohorts, error/coverage review policies |
| Numerical verification | independent feature and MAE/RMSE reconstruction in DuckDB |
| Reproducible execution | fixed policy/seed, dependency/source manifest, persisted-model replay |
| Failure handling | blocked histories, pending labels, corruption checks and staged publication |
| CI and container configuration | workflow and Dockerfile; completed run required for execution claims |

This substantiates synthetic engineering work, not production ML experience,
real crop forecasting accuracy, fiscal prediction, scientific replication or
causal identification. Do not describe the project as consistently outperforming
baselines: the selected model loses to the one-day seasonal baseline on the
default shifted holdout. Empirical error bands are not guaranteed prediction
intervals. Actual local checks and numerical results are in `ml_validation_record.md`.
