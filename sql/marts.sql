CREATE OR REPLACE VIEW mart.system_error AS
SELECT region, product, origin_step, target_step, 'baseline' AS system,
       actual, baseline AS forecast,
       ABS(actual-baseline) AS abs_error,
       SQRT(POWER(actual-baseline, 2)) AS root_sq_error
FROM core.forecast_pair
UNION ALL
SELECT region, product, origin_step, target_step, 'adaptive' AS system,
       actual, adaptive AS forecast,
       ABS(actual-adaptive) AS abs_error,
       SQRT(POWER(actual-adaptive, 2)) AS root_sq_error
FROM core.forecast_pair;

CREATE OR REPLACE VIEW mart.metric_summary AS
SELECT system,
       AVG(abs_error) AS mae,
       SQRT(AVG(POWER(actual-forecast, 2))) AS rmse,
       COUNT(*) AS n_pairs
FROM mart.system_error
GROUP BY system;
