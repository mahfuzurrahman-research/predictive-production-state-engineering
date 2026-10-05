#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH="$PWD:${PYTHONPATH:-}"
rm -rf outputs/*
python -m src.forecast_demo.generate
python examples/run_forecast_demo.py
python examples/run_recovery_demo.py
python sql/build_warehouse.py
python dashboards/build_dashboard.py
python -m unittest discover -s tests -v
printf '\nPUBLIC_ENGINEERING_DEMO=PASS\n'
