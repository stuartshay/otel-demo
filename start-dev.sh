#!/bin/bash
# Start otel-demo in development mode with .env loaded

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Error: .env file not found in $(pwd). Please create a .env file before running start-dev.sh." >&2
    exit 1
fi

# Check if virtual environment exists
if [ ! -f "venv/bin/activate" ]; then
    echo "Error: Python virtual environment not found (missing venv/bin/activate)." >&2
    echo "Please run ./setup.sh to create the virtual environment before running this script." >&2
    exit 1
fi

set -a
# shellcheck source=/dev/null
source .env
set +a

source venv/bin/activate
python run.py
