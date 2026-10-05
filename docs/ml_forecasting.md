# Synthetic ML forecasting: method and limits

## Measurement and claim baseline

This upgrade is a software demonstration using independently fabricated data.
The target is an arbitrary non-negative production index, not observed crop
output, administrative performance, tax revenue or fiscal risk. The original
demo has two hand-coded formulas. The new module adds actually fitted ML models,
controlled temporal evaluation and monitoring; successful execution does not
establish the private paper's measurement validity or scientific findings.

The synthetic panel has four neutral area IDs and 420 daily dates. Fabricated
seasonal patterns and noise supply variation. The generator injects an input
distribution change, a target relationship change, a delayed target-history
record, unavailable weather and a missing observation. Injection truth is stored
separately and is never passed to features, training, selection or monitoring.

## As-of information

Forecasts are issued at 07:00 UTC, at one- and seven-day horizons. Daily target
observations normally arrive two days after their event date at 06:00; weather
normally arrives the following day at 06:00. A completed daily observation cannot
claim arrival before the event day ends.

Each feature vector uses 28 target observations ending two days before the origin
and weather from the previous day. All required records must exist exactly once
and have arrived by issue time. Missing, duplicate or unavailable history blocks
the forecast and leaves all predictions null. It does not become a zero or a
silently imputed value. Arrival exactly at the origin is admitted. Each admitted
forecast records its source IDs and latest feature availability.

The feature set contains the latest target, targets seven/fourteen days before
that latest target, seven/twenty-eight-day means, latest weather, known target-date
annual/weekly sine and cosine terms, and area indicators. Calendar terms are
known ahead of time; no future observed weather or future target value is used.
Feature order is declared in code and checked against the saved bundle.

## Fitting, selection and separation

| Stage | Default schedule and information rule |
|---|---|
| Feature warmup | First issue date 2023-02-05 |
| Rolling fit origins | 2023-06-10, 2023-07-20, 2023-08-29 |
| Rolling validation | 28 issue days following each fit, model frozen within each fold |
| Selection and final fit | 2023-10-08; all selection labels must already be available |
| Later calibration issues | 2023-10-08 through 2023-11-16 |
| Calibration label deadline | Complete default labels by 2023-11-25 |
| Frozen holdout begins | 2023-11-29 |
| Final evaluation as-of | 2024-02-24 at 07:00 UTC |

Training examples require an earlier issue origin, admitted features and a target
label available by the fit time. This label-maturity rule creates a horizon-specific
gap at the end of each training set. No random train/test shuffle is used. The
training archive expands at later folds; earlier validation examples can enter
later training after their labels arrive. The final refit can use all mature
pre-fit examples, including prior validation dates. Calibration occurs afterward
and never changes model selection or model weights.

Separate direct models are fitted for each horizon on the pooled area panel:

- Persistence uses the latest available target.
- Seasonal naive uses the most recent available observation matching the target
  weekday; it does not assume yesterday's value has arrived.
- Ridge uses a `StandardScaler` fitted only on each training matrix, then ridge
  regression with alpha 1.
- Random forest uses 64 trees, maximum depth 10, minimum leaf size 4, one worker
  and a fixed seed. Its hyperparameters stay fixed.

Model selection uses pooled rolling-validation MAE per horizon, with a lexical
tie break. Both baselines are eligible to win. Later holdout performance never
reselects the system. RMSE and signed error are also reported; final metrics use
the same mature admitted forecast rows for every system. Area/horizon breakdowns
make concentrated failures visible. No claim is made that the ML model must beat
a simple baseline or that a selected model remains best after a shift.

The implementation uses explicit calendar cutoffs and label availability rather
than generic row-count splitting. The scikit-learn
[lagged forecasting example](https://scikit-learn.org/1.8/auto_examples/applications/plot_time_series_lagged_features.html)
and [TimeSeriesSplit documentation](https://scikit-learn.org/1.8/modules/generated/sklearn.model_selection.TimeSeriesSplit.html)
provide the relevant time-ordering context. This implementation additionally
handles delayed labels and multiple series explicitly.

## Empirical error bands

The frozen selected model predicts the later calibration block. The 90th
percentile of absolute calibration error, using NumPy's `higher` quantile rule,
defines a symmetric band for each horizon. Calibration labels must mature before
deployment; too few mature labels fail the run. The band remains unchanged
throughout the holdout. Bounds are in arbitrary index units and are not clipped
to impose a physical production model.

These are historical error bands, not formal uncertainty guarantees. Dependent
time-series observations and changing regimes do not justify exchangeable-sample
coverage claims. Target uncertainty, model uncertainty and scientific inference
are not fully modeled. The demo therefore reports observed coverage and its
deterioration rather than promising 90% future coverage.

## Monitoring and delayed labels

Input monitoring compares the mean of logged latest weather and latest target
features with their final training mean/std. A standardized mean difference of
at least 2.5 requests distribution review. This simple heuristic can miss variance,
tail, subgroup or compensating shifts and has no calibrated false-alarm guarantee.

Every 14 issue days, performance monitoring gathers labels newly arrived since
the previous monitoring close. An earlier pending forecast is assessed in the
later window when its label arrives. A forecast is counted once in the arrival
cohorts. Missing/duplicate labels remain unresolved feed issues. Without at least
eight mature labels, MAE and coverage are null and marked insufficient; input
monitoring can still operate.

Window MAE at least 1.8 times the fixed calibration MAE requests error review.
Coverage below 0.7 requests interval review. These policies were set before the
default holdout evaluation. They are not optimized detection rules, causal
evidence of concept drift or statistically tested change points. Alerts are
pending reviews and authorize no automatic retraining. Repeated windows may
generate repeated reviews; a production incident lifecycle is not implemented.

## Numerical and artifact controls

DuckDB independently reconstructs latest/history means/weather from raw source
lineage, checks feature and training-label availability, verifies horizon and
forecast inventory, and recomputes final MAE/RMSE. Pending label values and blocked
predictions must stay null. Saved estimators, scaler and monitoring reference
must replay the same holdout forecasts. Artifact hashes verify a complete run
inventory and detect accidental modification.

Replay loads only the model produced by the current process. `joblib` is a
pickle-based trusted-source format, not a safe loader for arbitrary uploaded
models; see the [official persistence guidance](https://scikit-learn.org/stable/model_persistence.html).
CLI receipt verification does not deserialize model files. Matching dependencies
are recorded and pinned; hashes alone do not authenticate a model's producer.

## Limits beyond this demonstration

This fixed-seed panel is deliberately simple. It omits genuine release revisions,
real data acquisition, validated exposure/production measurement, multiyear
forecast evaluation, external-area generalization, inferential uncertainty,
online serving, automatic refitting, model registry operations and production
incident resolution. Multiple horizons share targets and neighboring windows
are dependent. More elaborate computation on these fabricated rows would not
resolve those limitations or substantiate the private scientific claims.
