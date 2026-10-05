#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 -m forecast_ml.pipeline
python3 -m pytest -q tests_ml
python3 -m forecast_ml.pipeline --verify-only
echo "ML_FORECAST_ENGINEERING_STATUS=PASS"
