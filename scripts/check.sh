#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
node --test tests/browser_core.mjs
python3 -m unittest discover -s tests -p 'test_*.py'
python3 tests/browser_smoke.py
