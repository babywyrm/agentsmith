#!/bin/bash
# Agent Smith Setup Script
# Sets up the complete environment: Go scanner binary + Python virtual environment
#
# Usage:
#   ./scripts/setup.sh           # Full setup (Go build + Python venv + dependencies)
#   ./scripts/setup.sh --python  # Python-only setup (skip Go build)
#   ./scripts/setup.sh --go      # Go-only setup (build scanner binary)

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

PYTHON_ONLY=false
GO_ONLY=false

for arg in "$@"; do
    case $arg in
        --python) PYTHON_ONLY=true ;;
        --go) GO_ONLY=true ;;
        --help|-h)
            echo "Usage: ./scripts/setup.sh [--python|--go|--help]"
            echo ""
            echo "  --python   Python-only setup (skip Go build)"
            echo "  --go       Go-only setup (build scanner binary)"
            echo "  --help     Show this help"
            echo ""
            echo "With no flags, runs full setup (Go + Python)."
            exit 0
            ;;
    esac
done

echo ""
echo "🕶️  Agent Smith Setup"
echo "====================="
echo ""

# ============================================================
# Step 1: Build Go Scanner Binary
# ============================================================
if [ "$PYTHON_ONLY" = false ]; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Step 1: Go Scanner Binary"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    if ! command -v go &> /dev/null; then
        echo "⚠️  Go is not installed."
        echo "   Install Go from https://go.dev/dl/ (requires Go 1.21+)"
        echo "   The scanner binary is needed for hybrid mode (static + AI)."
        echo ""
        if [ "$GO_ONLY" = true ]; then
            echo "❌ Cannot build scanner without Go. Exiting."
            exit 1
        fi
        echo "   Skipping Go build. You can run './scripts/setup.sh --go' later."
        echo ""
    else
        GO_VERSION=$(go version | awk '{print $3}')
        echo "✓ Found $GO_VERSION"

        # Check for agentsmith.go source
        if [ ! -f "agentsmith.go" ]; then
            echo "❌ Error: agentsmith.go not found in $SCRIPT_DIR"
            exit 1
        fi

        # Validate rules before build
        if python3 -c "import json" 2>/dev/null && [ -d rules ]; then
            python3 scripts/validate_rules.py || { echo "❌ Rules validation failed"; exit 1; }
        fi

        echo "  Building scanner binary..."
        go build -o scanner agentsmith.go
        chmod +x scanner

        # Verify the binary works
        if ./scanner --dir /dev/null --output json 2>/dev/null || true; then
            echo "✓ Scanner binary built successfully"
        else
            echo "✓ Scanner binary built ($(file scanner | awk -F: '{print $2}' | xargs))"
        fi

        # Check for rule files
        RULE_COUNT=$(ls rules/*.json 2>/dev/null | wc -l | xargs)
        if [ "$RULE_COUNT" -gt 0 ]; then
            echo "✓ Found $RULE_COUNT rule files in rules/"
        else
            echo "⚠️  No rule files found in rules/ — scanner will use built-in fallback rules"
        fi
        echo ""
    fi

    if [ "$GO_ONLY" = true ]; then
        echo "✅ Go setup complete!"
        echo ""
        echo "Test it:"
        echo "  ./scanner --dir . --output json --severity HIGH"
        echo ""
        exit 0
    fi
fi

# ============================================================
# Step 2: Python Environment (uv preferred, pip fallback)
# ============================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Step 2: Python Environment"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 not found. Please install Python 3.11 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo "✓ Found Python $PYTHON_VERSION"

if command -v uv &> /dev/null; then
    UV_VERSION=$(uv --version 2>/dev/null)
    echo "✓ Found $UV_VERSION (using uv as package manager)"

    echo "  Syncing environment..."
    uv sync --all-extras --quiet
    echo "✓ Environment synced (uv)"
else
    echo "⚠️  uv not found — falling back to pip"
    echo "   Install uv for faster setup: curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo ""

    if [ ! -d ".venv" ]; then
        echo "  Creating virtual environment..."
        python3 -m venv .venv
        echo "✓ Virtual environment created"
    else
        echo "✓ Virtual environment already exists"
    fi

    source .venv/bin/activate

    echo "  Upgrading pip..."
    pip install --upgrade pip --quiet

    echo "  Installing dependencies..."
    pip install -e ".[mcp-server,dev]" --quiet

    echo "✓ Python dependencies installed (pip)"
fi
echo ""

# ============================================================
# Step 3: Environment Verification
# ============================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Step 3: Verification"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check scanner binary
if [ -x "./scanner" ]; then
    echo "✓ Scanner binary:  ./scanner (ready)"
else
    echo "⚠️  Scanner binary:  not found (hybrid mode unavailable)"
    echo "   Run './scripts/setup.sh --go' to build it"
fi

# Check API key
if [ -n "$CLAUDE_API_KEY" ]; then
    echo "✓ CLAUDE_API_KEY:   set"
else
    echo "⚠️  CLAUDE_API_KEY:   not set (required for AI modes)"
    echo "   Set it with: export CLAUDE_API_KEY=\"sk-ant-api03-...\""
fi

# Check rules
RULE_COUNT=$(ls rules/*.json 2>/dev/null | wc -l | xargs)
echo "✓ Static rules:     $RULE_COUNT rule files in rules/"

# Check prompts
PROMPT_COUNT=$(ls prompts/*.txt 2>/dev/null | wc -l | xargs)
PROMPT_SECTIONS=$(ls prompts/profiles/*.txt 2>/dev/null | wc -l | xargs)
echo "✓ AI prompts:       $PROMPT_COUNT profile templates + $PROMPT_SECTIONS modular sections in prompts/"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "✅ Setup complete!"
echo ""
echo "Activate the environment:"
echo "  source scripts/activate.sh        # or: source .venv/bin/activate"
echo ""
echo "Quick start:"
echo "  # Fast static scan (no API key needed)"
echo "  python3 agentsmith.py static . --severity HIGH"
echo ""
echo "  # Full hybrid scan (requires API key)"
echo "  python3 orchestrator.py /path/to/repo ./scanner \\"
echo "    --profile owasp --prioritize --verbose"
echo ""
echo "  # See all options"
echo "  python3 agentsmith.py --help"
echo "  python3 orchestrator.py --help"
echo ""
