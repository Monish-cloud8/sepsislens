#!/usr/bin/env bash
set -euo pipefail
export PATH="/opt/homebrew/bin:$PATH"
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
 if command -v uv >/dev/null; then uv venv --python 3.12 .venv; else python3 -m venv .venv; fi
fi
.venv/bin/python -m pip --version >/dev/null 2>&1 || true
if command -v uv >/dev/null; then uv pip install --python .venv/bin/python -r requirements.txt; else .venv/bin/python -m pip install -r requirements.txt; fi
.venv/bin/python -u scripts/download.py
.venv/bin/python -u -m src.load
.venv/bin/python -u -m src.features
.venv/bin/python -u -m src.train
.venv/bin/python -u -m src.evaluate
.venv/bin/python -u scripts/docs.py
.venv/bin/python -m pytest -q
echo "Ready: .venv/bin/streamlit run app/app.py"
