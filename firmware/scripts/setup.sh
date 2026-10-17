#!/bin/sh
set -eu

cd "$(dirname "$0")/.."

PYTHON=${PYTHON:-python3}
if ! command -v "$PYTHON" >/dev/null 2>&1; then
    echo "Python 3 was not found. Install Python 3 and rerun make setup." >&2
    exit 1
fi

if [ ! -d .venv ]; then
    "$PYTHON" -m venv .venv
fi

.venv/bin/python -m pip install -r requirements.txt
