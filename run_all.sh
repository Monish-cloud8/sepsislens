#!/usr/bin/env bash
set -euo pipefail
export PATH="/opt/homebrew/bin:$PATH"
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
 if command -v uv >/dev/null; then uv venv --python 3.11 .venv; else python3.11 -m venv .venv; fi
fi
if command -v uv >/dev/null; then uv pip install --python .venv/bin/python -r requirements.txt; else .venv/bin/python -m pip install -r requirements.txt; fi
if [ "${1:-}" != "--resume" ]; then
 .venv/bin/python -u scripts/download.py
 .venv/bin/python -u -m src.load
 .venv/bin/python -u -m src.features
 .venv/bin/python -u -m src.train
 .venv/bin/python -u -m src.refine
else
 test -f data/processed/features.parquet
 test -f models/policy_lock.json
 test -f models/refined.joblib
fi
if [ "${1:-}" = "--resume" ] && .venv/bin/python scripts/validate_checkpoint.py; then
 :
else
 .venv/bin/python -u -m src.evaluate_refined
fi
.venv/bin/python -u scripts/docs.py
.venv/bin/python -m pytest -q
.venv/bin/python scripts/smoke_app.py
.venv/bin/python scripts/verify_bundle.py
echo "Ready: .venv/bin/streamlit run app/app.py"
