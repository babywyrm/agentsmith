#!/bin/bash
# Quick activation script for SCRYNET virtual environment

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ ! -d "$SCRIPT_DIR/.venv" ]; then
    echo "❌ Virtual environment not found. Run ./setup.sh first."
    exit 1
fi

source "$SCRIPT_DIR/.venv/bin/activate"

echo "✓ Virtual environment activated"
echo "You're now in: $(pwd)"
echo ""
echo "Run SCRYNET commands:"
echo "  python3 scrynet.py --help"
echo ""

