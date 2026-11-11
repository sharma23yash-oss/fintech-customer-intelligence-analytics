#!/usr/bin/env bash
# One-command setup for macOS (Apple Silicon or Intel) or Linux. Uses only the synthetic data in data/synthetic/.
# Usage:  bash scripts/setup_and_run.sh            # set up, build DB, run 8 daily runs, test, start dashboard
#         bash scripts/setup_and_run.sh --no-app   # same, but do not start Streamlit
set -euo pipefail
cd "$(dirname "$0")/.."

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

python -m friction_detector.cli build-db
python -m friction_detector.cli replay --start 2026-10-24 --end 2026-10-31   # 8 consecutive daily runs
python -m pytest -q
python validation/validate.py

if [[ "${1:-}" != "--no-app" ]]; then
  streamlit run app/streamlit_app.py
fi
