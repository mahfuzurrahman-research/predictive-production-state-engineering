from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from .contracts import ROOT, day_at, stamp


def build(path: Path, rows: list[dict], features: list[dict], lineage: list[dict], audit: list[dict], predictions: list[dict], evaluated: list[dict], summary: dict, alerts: list[dict], c: dict) -> dict:
    con = duckdb.connect(str(path))
    try:
        con.execute("SET TimeZone='UTC'")
        con.execute((ROOT / "sql/ml_forecasting.sql").read_text())
        def insert(table, records, columns):
            if not records:
                return
            frame = pd.DataFrame([{key: row[key] for key in columns} for row in records], columns=columns)
            con.register("_load", frame)
            con.execute(f"INSERT INTO {table} SELECT * FROM _load")
            con.unregister("_load")
        insert("ml_observations", rows, ["row_id", "area_id", "event_day", "target_value", "target_available_at", "weather", "weather_available_at", "synthetic_record"])
        insert("ml_features", features, ["forecast_id", "area_id", "origin_day", "origin_at", "target_day", "horizon", "admitted", "feature_max_available_at", "lag_latest", "mean_7", "mean_28", "weather_latest", "reason_codes"])
        insert("ml_lineage", lineage, ["forecast_id", "row_id", "source_kind"])
        insert("ml_training_audit", audit, ["fit_tag", "fit_at", "horizon", "forecast_id", "label_row_id", "label_available_at"])
        insert("ml_predictions", predictions, ["forecast_id", "area_id", "origin_at", "target_day", "horizon", "admitted", "model_fit_at", "reference_released_at", "model_id", "prediction", "lower", "upper", "persistence", "seasonal_naive", "ridge", "random_forest"])
        insert("ml_evaluation", evaluated, ["forecast_id", "evaluation_as_of", "label_row_id", "label_available_at", "actual", "label_status"])
        insert("ml_metric_report", summary["scores"], ["horizon", "system", "n", "mae", "rmse"])
        insert("ml_alerts", alerts, ["alert_id", "window_id", "alert_type", "observed_at", "model_id", "automatic_retraining_authorized"])
        queries = {
            "duplicate_forecast_ids": "SELECT COUNT(*) FROM (SELECT forecast_id FROM ml_predictions GROUP BY forecast_id HAVING COUNT(*)>1)",
            "admitted_lineage_inventory": """SELECT COUNT(*) FROM ml_features f LEFT JOIN mart.ml_feature_rebuild b USING(forecast_id)
                WHERE f.admitted AND (b.forecast_id IS NULL OR b.history_n<>28 OR b.weather_n<>1)""",
            "future_or_wrong_area_features": """SELECT COUNT(*) FROM ml_features f JOIN ml_lineage l USING(forecast_id)
                JOIN ml_observations o USING(row_id) WHERE f.admitted AND
                (o.area_id<>f.area_id OR o.event_day>=f.origin_day OR
                 (l.source_kind='TARGET_HISTORY' AND o.target_available_at>f.origin_at) OR
                 (l.source_kind='WEATHER_HISTORY' AND o.weather_available_at>f.origin_at))""",
            "python_sql_feature_parity": """SELECT COUNT(*) FROM ml_features f JOIN mart.ml_feature_rebuild b USING(forecast_id)
                WHERE f.admitted AND (f.lag_latest IS NULL OR f.mean_7 IS NULL OR f.mean_28 IS NULL OR f.weather_latest IS NULL
                    OR ABS(f.lag_latest-b.lag_latest)>1e-9 OR ABS(f.mean_7-b.mean_7)>1e-9
                    OR ABS(f.mean_28-b.mean_28)>1e-9 OR ABS(f.weather_latest-b.weather_latest)>1e-9)""",
            "training_label_availability": """SELECT COUNT(*) FROM ml_training_audit a
                LEFT JOIN ml_features f USING(forecast_id) LEFT JOIN ml_observations o ON o.row_id=a.label_row_id
                WHERE f.forecast_id IS NULL OR o.row_id IS NULL OR NOT f.admitted OR
                    f.origin_at>=a.fit_at OR o.target_available_at>a.fit_at OR a.label_available_at<>o.target_available_at
                    OR o.area_id<>f.area_id OR o.event_day<>f.target_day OR a.horizon<>f.horizon""",
            "forecast_horizon_integrity": """SELECT COUNT(*) FROM ml_predictions
                WHERE DATE_DIFF('day',CAST(origin_at AS DATE),target_day)<>horizon OR horizon NOT IN (1,7)""",
            "model_or_reference_unavailable": """SELECT COUNT(*) FROM ml_predictions
                WHERE model_fit_at>origin_at OR reference_released_at>origin_at""",
            "blocked_forecast_scored": """SELECT COUNT(*) FROM ml_predictions WHERE NOT admitted AND
                (prediction IS NOT NULL OR lower IS NOT NULL OR upper IS NOT NULL OR persistence IS NOT NULL
                 OR seasonal_naive IS NOT NULL OR ridge IS NOT NULL OR random_forest IS NOT NULL)""",
            "invalid_admitted_forecast": """SELECT COUNT(*) FROM ml_predictions WHERE admitted AND
                (prediction IS NULL OR lower IS NULL OR upper IS NULL OR persistence IS NULL OR seasonal_naive IS NULL
                 OR ridge IS NULL OR random_forest IS NULL OR NOT ISFINITE(prediction) OR NOT ISFINITE(lower)
                 OR NOT ISFINITE(upper) OR NOT ISFINITE(ridge) OR NOT ISFINITE(random_forest)
                 OR lower>prediction OR prediction>upper)""",
            "immature_or_wrong_evaluation_labels": """SELECT COUNT(*) FROM ml_evaluation e
                LEFT JOIN ml_predictions p USING(forecast_id) LEFT JOIN ml_observations o ON o.row_id=e.label_row_id
                WHERE e.label_status='MATURE' AND (p.forecast_id IS NULL OR NOT p.admitted OR o.row_id IS NULL
                    OR e.actual IS NULL OR e.label_available_at IS NULL OR e.label_available_at>e.evaluation_as_of
                    OR e.label_available_at<>o.target_available_at OR e.actual<>o.target_value
                    OR o.area_id<>p.area_id OR o.event_day<>p.target_day)""",
            "unavailable_label_has_value": """SELECT COUNT(*) FROM ml_evaluation WHERE label_status<>'MATURE'
                AND (actual IS NOT NULL OR label_available_at IS NOT NULL)""",
            "forecast_inventory_mismatch": """SELECT COUNT(*) FROM ml_features f FULL OUTER JOIN ml_predictions p USING(forecast_id)
                WHERE (f.origin_at>=CAST(? AS TIMESTAMPTZ) AND (p.forecast_id IS NULL OR p.admitted IS DISTINCT FROM f.admitted))
                    OR (p.forecast_id IS NOT NULL AND (f.forecast_id IS NULL OR f.origin_at<CAST(? AS TIMESTAMPTZ)))""",
            "evaluation_inventory_mismatch": """SELECT COUNT(*) FROM ml_predictions p FULL OUTER JOIN ml_evaluation e USING(forecast_id)
                WHERE p.forecast_id IS NULL OR e.forecast_id IS NULL""",
            "python_sql_metric_parity": """SELECT COUNT(*) FROM ml_metric_report r FULL OUTER JOIN mart.ml_metric_summary s USING(horizon,system)
                WHERE r.system IS NULL OR s.system IS NULL OR r.n<>s.n OR ABS(r.mae-s.mae)>1e-9 OR ABS(r.rmse-s.rmse)>1e-9""",
            "automatic_retraining_unauthorized": "SELECT COUNT(*) FROM ml_alerts WHERE automatic_retraining_authorized",
        }
        deployment = stamp(day_at(c["deployment_index"], c), c["origin_hour_utc"])
        checks = {name: int(con.execute(query, [deployment, deployment] if name == "forecast_inventory_mismatch" else []).fetchone()[0]) for name, query in queries.items()}
        result = {"status": "PASS" if not any(checks.values()) else "FAIL", "checks": checks, "total_failures": sum(checks.values())}
    finally:
        con.close()
    if result["status"] != "PASS":
        raise ValueError("ML forecast warehouse QA failed: "+str({k: v for k, v in checks.items() if v}))
    return result
