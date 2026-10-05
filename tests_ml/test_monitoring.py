from copy import deepcopy

from forecast_ml.features import record_index
from forecast_ml.monitoring import monitor_windows


def test_arrival_cohorts_assess_prior_pending_forecasts_exactly_once(trained):
    t = trained
    for horizon in t["c"]["horizons"]:
        expected = sum(e["label_status"] == "MATURE" and e["horizon"] == horizon for e in t["evaluated"])
        assert sum(w["newly_mature_labels"] for w in t["windows"] if w["horizon"] == horizon) == expected
    assert any(w["newly_mature_labels"] > w["issued_forecasts"]-w["blocked_forecasts"] for w in t["windows"])
    delayed = next(r for r in t["rows"] if r["area_id"] == "SYN003" and r["target_available_at"] > r["event_day"]+"T23:59:59Z" and r["event_day"] == "2023-12-17")
    forecasts = [e for e in t["evaluated"] if e["label_row_id"] == delayed["row_id"]]
    assert forecasts and all(e["label_status"] == "MATURE" for e in forecasts)


def test_future_label_values_do_not_change_earlier_monitoring(trained):
    t = trained
    first_close = t["windows"][0]["evaluation_as_of"]
    rows = deepcopy(t["rows"])
    for row in rows:
        if row["target_available_at"] > first_close:
            row["target_value"] += 1000
    windows, alerts = monitor_windows(t["predictions"], t["features"], t["reference"], record_index(rows), t["c"])
    assert [w for w in windows if w["evaluation_as_of"] == first_close] == [w for w in t["windows"] if w["evaluation_as_of"] == first_close]
    assert [a for a in alerts if a["observed_at"] == first_close] == [a for a in t["alerts"] if a["observed_at"] == first_close]


def test_input_monitoring_can_run_without_new_target_labels(trained):
    t = trained
    windows, alerts = monitor_windows(t["predictions"], t["features"], t["reference"], {}, t["c"])
    assert all(w["newly_mature_labels"] == 0 and w["performance_status"] == "INSUFFICIENT_MATURE_LABELS" for w in windows)
    assert all(w["mae"] is None and w["empirical_interval_coverage"] is None for w in windows)
    assert any(a["alert_type"].startswith("INPUT_DRIFT") for a in alerts)
    assert not any(a["alert_type"] in {"ERROR_DEGRADATION", "INTERVAL_UNDERCOVERAGE"} for a in alerts)


def test_blocked_forecasts_and_pending_targets_are_not_zero_imputed(trained):
    t = trained
    for p in t["predictions"]:
        if not p["admitted"]:
            assert p["prediction"] is None and p["lower"] is None and p["upper"] is None
    for e in t["evaluated"]:
        if e["label_status"] != "MATURE":
            assert e["actual"] is None
    assert t["summary"]["unscored_label_status_counts"]["PENDING"] > 0
    assert t["summary"]["unscored_label_status_counts"]["MISSING_LABEL"] > 0


def test_alerts_are_bounded_reviews_and_never_use_injection_labels(trained):
    alerts = trained["alerts"]
    kinds = {a["alert_type"] for a in alerts}
    assert {"DATA_QUALITY", "INPUT_DRIFT:weather_latest", "ERROR_DEGRADATION", "INTERVAL_UNDERCOVERAGE", "LABEL_QUALITY"}.issubset(kinds)
    assert len({a["alert_id"] for a in alerts}) == len(alerts)
    assert all(a["automatic_retraining_authorized"] is False and a["review_status"] == "PENDING_REVIEW" for a in alerts)
    assert all("injected_event" not in a and "concept_shift" not in a for a in alerts)
