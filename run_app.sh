#!/bin/bash
# Pro Tools Session Builder launch script

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Activate virtual environment
source "$SCRIPT_DIR/venv/bin/activate"

# Set PYTHONPATH to project root
export PYTHONPATH="$SCRIPT_DIR"

# Run the application
python3 "$SCRIPT_DIR/src/main.py" "$@"
