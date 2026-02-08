#!/bin/bash
# Quick activation script for Agent Smith virtual environment

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ ! -d "$SCRIPT_DIR/.venv" ]; then
    echo "Virtual environment not found. Run ./setup.sh first."
    exit 1
fi

source "$SCRIPT_DIR/.venv/bin/activate"

echo "Agent Smith environment activated"
echo ""
echo "Commands:"
echo "  python3 agentsmith.py --help       # All modes"
echo "  python3 orchestrator.py --help     # Hybrid mode (recommended)"
echo "  python3 orchestrator.py --list-presets   # Available presets"
echo ""
