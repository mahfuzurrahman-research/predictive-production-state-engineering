#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export PYTHONPATH="$PWD:${PYTHONPATH:-}"
mkdir -p outputs
python3 -m src.forecast_demo.generate
python3 examples/run_forecast_demo.py
python3 examples/run_recovery_demo.py
python3 sql/build_warehouse.py
python3 dashboards/build_dashboard.py
python3 -m unittest discover -s tests -v
printf '\nPUBLIC_ENGINEERING_DEMO=PASS\n'
