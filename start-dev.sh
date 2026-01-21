#!/bin/bash
# Start otel-demo in development mode with .env loaded

set -a
# shellcheck source=/dev/null
source .env
set +a

source venv/bin/activate
python run.py
