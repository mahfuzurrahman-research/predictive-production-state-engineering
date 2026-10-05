# Engineering architecture

The public repository demonstrates two independent engineering concerns.

## Forecast workflow

Synthetic release-vintage observations are admitted only if available by the origin date. Valid pairs are passed to two small demonstration forecasters, evaluated with standard metrics, written to a relational analytical layer, checked by SQL QA, and rendered into reports.

## Reliability workflow

Synthetic work is divided into deterministic units. Each unit receives a receipt containing source/config identities and an output hash. An intentional interruption is followed by a resume that reuses only validated units. A merged accepted artifact is written atomically.

Neither workflow reproduces the private empirical analysis.

## Fitted ML forecasting workflow

`forecast_ml/` is a separate synthetic daily panel with explicit target and
weather availability. As-of features supply pooled, horizon-specific ridge and
random-forest estimators alongside simple baselines. Expanding training cutoffs
admit only mature labels. Earlier rolling validation selects a system per horizon;
later calibration sets empirical bands. The final holdout never changes selection,
weights, thresholds or bands.

Logged feature distributions support input monitoring. A separate label-arrival
cohort assesses forecast errors only when targets become available; pending
predictions carry forward to a later arrival window. Feed and label problems,
input shifts, error deterioration and interval undercoverage become review
records. Independent DuckDB queries rebuild features and final metrics from
typed raw, lineage, training-audit, prediction and evaluation tables.

The pipeline stages all artifacts, checks saved-model replay and relational QA,
then publishes a complete hash receipt. Method assumptions and missing production
capabilities are described in `ml_forecasting.md`.
