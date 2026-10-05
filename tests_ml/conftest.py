from copy import deepcopy

import pytest

from forecast_ml.contracts import load_contract
from forecast_ml.features import build_features, record_index
from forecast_ml.learning import calibrate, fit_at, forecast_holdout, rolling_select
from forecast_ml.monitoring import evaluate_holdout, monitor_windows
from forecast_ml.synthetic import generate


@pytest.fixture(scope="session")
def base_data():
    c = load_contract()
    c["forest_trees"] = 8  # Fast unit fixtures; end-to-end runs use the default 64.
    rows, _ = generate(c)
    features, lineage = build_features(rows, c)
    return c, rows, features, lineage


@pytest.fixture
def panel(base_data):
    c, rows, _, _ = base_data
    return deepcopy(c), deepcopy(rows)


@pytest.fixture(scope="session")
def trained(base_data):
    c, rows, features, lineage = base_data
    index = record_index(rows)
    selection, validation, audit = rolling_select(features, index, c)
    pack = fit_at(features, index, c["final_fit_index"], c, "final")
    reference, calibration = calibrate(pack, selection, features, index, c)
    predictions = forecast_holdout(pack, reference, features, c)
    evaluated, summary = evaluate_holdout(predictions, index, c)
    windows, alerts = monitor_windows(predictions, features, reference, index, c)
    return dict(c=c, rows=rows, features=features, lineage=lineage, index=index,
                selection=selection, validation=validation, audit=[*audit,*pack["training_audit"]],
                pack=pack, reference=reference, calibration=calibration,
                predictions=predictions, evaluated=evaluated, summary=summary, windows=windows, alerts=alerts)
