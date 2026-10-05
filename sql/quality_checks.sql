CREATE OR REPLACE TABLE qa.quality_result AS
SELECT * FROM (
    SELECT 'Q01' AS check_id, 'forecast_pair_primary_key_unique' AS check_name,
           COUNT(*) AS failures
    FROM (
        SELECT region, product, origin_step, target_step, COUNT(*) n
        FROM core.forecast_pair
        GROUP BY ALL HAVING COUNT(*) <> 1
    )
    UNION ALL
    SELECT 'Q02', 'target_after_origin', COUNT(*)
    FROM core.forecast_pair WHERE target_date <= origin_date
    UNION ALL
    SELECT 'Q03', 'finite_values', COUNT(*)
    FROM core.forecast_pair
    WHERE NOT isfinite(actual) OR NOT isfinite(baseline) OR NOT isfinite(adaptive)
    UNION ALL
    SELECT 'Q04', 'positive_horizon', COUNT(*)
    FROM core.forecast_pair WHERE target_step <= origin_step
    UNION ALL
    SELECT 'Q05', 'both_systems_present',
           CASE WHEN (SELECT COUNT(DISTINCT system) FROM mart.system_error)=2 THEN 0 ELSE 1 END
);
