CREATE SCHEMA IF NOT EXISTS mart;
CREATE TABLE ml_observations (
    row_id VARCHAR, area_id VARCHAR, event_day DATE, target_value DOUBLE,
    target_available_at TIMESTAMPTZ, weather DOUBLE, weather_available_at TIMESTAMPTZ,
    synthetic_record BOOLEAN
);
CREATE TABLE ml_features (
    forecast_id VARCHAR, area_id VARCHAR, origin_day DATE, origin_at TIMESTAMPTZ,
    target_day DATE, horizon INTEGER, admitted BOOLEAN,
    feature_max_available_at TIMESTAMPTZ, lag_latest DOUBLE, mean_7 DOUBLE,
    mean_28 DOUBLE, weather_latest DOUBLE, reason_codes VARCHAR
);
CREATE TABLE ml_lineage (forecast_id VARCHAR, row_id VARCHAR, source_kind VARCHAR);
CREATE TABLE ml_training_audit (
    fit_tag VARCHAR, fit_at TIMESTAMPTZ, horizon INTEGER, forecast_id VARCHAR,
    label_row_id VARCHAR, label_available_at TIMESTAMPTZ
);
CREATE TABLE ml_predictions (
    forecast_id VARCHAR, area_id VARCHAR, origin_at TIMESTAMPTZ, target_day DATE,
    horizon INTEGER, admitted BOOLEAN, model_fit_at TIMESTAMPTZ,
    reference_released_at TIMESTAMPTZ, model_id VARCHAR, prediction DOUBLE,
    lower DOUBLE, upper DOUBLE, persistence DOUBLE, seasonal_naive DOUBLE,
    ridge DOUBLE, random_forest DOUBLE
);
CREATE TABLE ml_evaluation (
    forecast_id VARCHAR, evaluation_as_of TIMESTAMPTZ, label_row_id VARCHAR,
    label_available_at TIMESTAMPTZ, actual DOUBLE, label_status VARCHAR
);
CREATE TABLE ml_metric_report (horizon INTEGER, system VARCHAR, n INTEGER, mae DOUBLE, rmse DOUBLE);
CREATE TABLE ml_alerts (
    alert_id VARCHAR, window_id VARCHAR, alert_type VARCHAR,
    observed_at TIMESTAMPTZ, model_id VARCHAR, automatic_retraining_authorized BOOLEAN
);

CREATE VIEW mart.ml_feature_rebuild AS
WITH sources AS (
    SELECT l.forecast_id,l.source_kind,o.*,
        MAX(o.event_day) FILTER (WHERE l.source_kind='TARGET_HISTORY')
            OVER (PARTITION BY l.forecast_id) AS latest_history_day
    FROM ml_lineage l JOIN ml_observations o USING (row_id)
)
SELECT forecast_id,
    COUNT(*) FILTER (WHERE source_kind='TARGET_HISTORY') AS history_n,
    COUNT(*) FILTER (WHERE source_kind='WEATHER_HISTORY') AS weather_n,
    ARG_MAX(target_value,event_day) FILTER (WHERE source_kind='TARGET_HISTORY') AS lag_latest,
    AVG(target_value) FILTER (WHERE source_kind='TARGET_HISTORY'
        AND event_day>=latest_history_day-INTERVAL '6 days') AS mean_7,
    AVG(target_value) FILTER (WHERE source_kind='TARGET_HISTORY') AS mean_28,
    MAX(weather) FILTER (WHERE source_kind='WEATHER_HISTORY') AS weather_latest
FROM sources GROUP BY forecast_id;

CREATE VIEW mart.ml_metric_summary AS
SELECT p.horizon,v.system,COUNT(*)::INTEGER AS n,
       AVG(ABS(e.actual-v.prediction)) AS mae,
       SQRT(AVG(POWER(e.actual-v.prediction,2))) AS rmse
FROM ml_predictions p JOIN ml_evaluation e USING (forecast_id)
CROSS JOIN LATERAL (VALUES
    ('persistence',p.persistence),('seasonal_naive',p.seasonal_naive),
    ('ridge',p.ridge),('random_forest',p.random_forest),('selected',p.prediction)
) v(system,prediction)
WHERE p.admitted AND e.label_status='MATURE'
GROUP BY p.horizon,v.system;

CREATE VIEW mart.ml_label_coverage AS
SELECT p.horizon,e.label_status,COUNT(*) AS forecasts
FROM ml_predictions p JOIN ml_evaluation e USING (forecast_id)
GROUP BY p.horizon,e.label_status;
