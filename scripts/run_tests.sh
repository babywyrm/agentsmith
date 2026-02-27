#!/usr/bin/env bash
# Run pytest for Agent Smith. Uses venv if available.
#
# Usage:
#   ./scripts/run_tests.sh              # run main tests (excludes test_targets)
#   ./scripts/run_tests.sh --all        # include test_targets (needs: pip install requests)
#   ./scripts/run_tests.sh -v           # verbose
#   ./scripts/run_tests.sh tests/test_mcp_client.py  # specific file

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

PY="${PROJECT_ROOT}/.venv/bin/python"
if [ ! -f "$PY" ]; then
    echo "❌ Virtual environment not found. Run: ./scripts/setup.sh"
    exit 1
fi

# Ensure pytest is installed
"$PY" -c "import pytest" 2>/dev/null || "$PY" -m pip install pytest -q

if [ "$1" = "--all" ]; then
    shift
    "$PY" -m pytest tests/ mcp_attack/tests/ -v --tb=short "$@"
else
    "$PY" -m pytest tests/ mcp_attack/tests/ -v --tb=short --ignore=tests/test_targets "$@"
fi
