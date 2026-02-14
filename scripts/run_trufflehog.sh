#!/usr/bin/env bash
# Run TruffleHog secrets scan on the repo.
# Excludes .venv, output, test_targets (intentionally vulnerable apps), etc.
#
# Usage:
#   ./scripts/run_trufflehog.sh
#
# Requires: trufflehog installed (brew install trufflehog)

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

EXCLUDE_FILE="$PROJECT_ROOT/.trufflehog-exclude"
if [ ! -f "$EXCLUDE_FILE" ]; then
    echo "Exclude file not found: $EXCLUDE_FILE"
    exit 1
fi

if ! command -v trufflehog &>/dev/null; then
    echo "trufflehog not found. Install with: brew install trufflehog"
    exit 1
fi

echo "Running TruffleHog (excluding .venv, output, test_targets...)"
trufflehog filesystem . --no-update --exclude-paths "$EXCLUDE_FILE"
echo ""
echo "Done. 0 findings = clean."
