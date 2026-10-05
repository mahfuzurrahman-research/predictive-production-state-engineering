# Observed local ML validation

Validated on 2026-10-05 UTC with Python 3.12.14 on Linux, NumPy 2.3.5,
scikit-learn 1.8.0, SciPy 1.17.0, DuckDB 1.5.6, pandas 2.2.3 and pytest 9.1.1.
The following observations come from actual local execution.

## Assessment baseline and implementation evidence

Before the upgrade, the repository passed 12 local tests and compared two
hand-coded forecast formulas. It did not fit an ML estimator. The new code fits
ridge and random-forest estimators, controls label maturity during rolling model
selection, separates later calibration from the holdout, and monitors predictions
using observed inputs and arriving target labels. This changes the supported
engineering capability; it does not change the assessment of private scientific
findings or establish production forecasting experience.

| Check | Observed result |
|---|---|
| Original forecast, recovery, SQL and dashboard demo | PASS |
| Original test suite | 12 passed |
| New ML suite | 46 passed |
| Combined local pytest run | 58 passed, no skipped tests |
| Combined demonstration runner | PASS |
| Independent DuckDB QA | 15 checks, zero failures |
| Saved model/scaler/reference replay | Identical holdout forecasts |
| Repeat runs | Identical CSV/JSON data, predictions, selection and manifest |
| Future perturbations | Earlier features, selection, fitted predictions and earlier monitoring unchanged |
| Training preprocessing | Scaler statistics match mature training rows only |
| Delayed-label monitoring | Earlier pending forecasts assessed once when labels arrive |
| Model/feature/reference/horizon violations | Rejected |
| Numerical and inventory corruption | Rejected by independent SQL |
| Staging failure / concurrent writer | Previous run preserved / second writer rejected |
| Dependency compatibility | `python3 -m pip check` passed |

Unit fixtures use eight forest trees to keep focused checks small; the actual
default pipeline and end-to-end/repeat-run tests use the configured 64 trees.
Docker was unavailable locally. The GitHub workflow is configured to run both
demos and Docker build/execution; a completed passing hosted run is needed before
claiming CI or container execution passed for this revision. Earlier passing
workflow runs apply to earlier code.

## Fixed-seed forecast observations

Default seed: `20261006`; policy: `synthetic-forecast-v1`; model/reference ID:
`forecast-v1-d77413a8448e0bea`. The panel contains 1,679 fabricated observations
and 3,080 scheduled feature rows. There are 704 holdout forecasts, of which 80
are blocked by feature-quality rules. The final as-of evaluation admits 587
mature forecast labels (302 one-day and 285 seven-day forecasts), leaves 36
pending and identifies one missing target label. Blocked and unobserved values
are never converted to zero.

Both horizon selections choose ridge from earlier rolling validation. Each
validation metric uses 336 forecast pairs per horizon. The later calibration
uses 160 pairs per horizon; its empirical half-widths are about 2.486 and 2.668
arbitrary index units. Selection and bands remain unchanged in the holdout.

| Horizon | System | Validation MAE | Holdout MAE | Holdout RMSE |
|---|---|---:|---:|---:|
| 1 day | Persistence | 5.1785 | 5.2397 | 6.0658 |
| 1 day | Seasonal naive | 1.9584 | 3.0018 | 4.9433 |
| 1 day | Ridge (selected) | 1.0194 | 3.2577 | 6.4042 |
| 1 day | Random forest | 2.8374 | 4.7167 | 6.8515 |
| 7 days | Persistence | 4.3703 | 5.2828 | 7.2217 |
| 7 days | Seasonal naive | 2.9390 | 5.5684 | 8.0448 |
| 7 days | Ridge (selected) | 1.0984 | 4.3133 | 8.0424 |
| 7 days | Random forest | 3.2695 | 7.2592 | 9.3696 |

The selected ridge model loses to the one-day seasonal baseline on the shifted
holdout. At seven days it has lower MAE than both simple baselines but higher
RMSE than persistence. Neither model choice nor thresholds were changed to hide
these results. The strongest bounded claim is a functioning temporal evaluation
and monitoring workflow, not consistent ML superiority.

The injected relationship change affects `SYN002`. Its selected-model MAE rises
to about 8.673 at one day and 11.227 at seven days; empirical band coverage is
about 0.482 and 0.405. These failures remain in the area/horizon breakdowns.
The nominal 0.9 calibration setting is not a guaranteed holdout coverage level.

## Monitoring observations

Fourteen horizon/window records yield 37 review alerts: 10 feature-quality,
10 weather-input shift, 8 error-degradation, 6 interval-undercoverage and 3
unresolved-label reviews. A single episode can produce repeated window alerts;
these are not 37 independent detected incidents. Every alert remains pending
review and authorizes no automatic retraining.

All 587 mature holdout forecasts are assigned once to label-arrival performance
cohorts, including earlier pending forecasts whose labels arrive later. Inputs
can still be monitored when the new target-label feed is absent; error and
coverage statistics then remain null and insufficient. Full numerical records
are generated under `outputs/ml/` after a run.

This is one deliberately simple fabricated stream with seeded injections.
It establishes neither real-world forecast accuracy nor calibrated drift/error
alarm rates, valid agricultural measurement, causal identification, scientific
inference or readiness for deployment.
