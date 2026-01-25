#!/bin/bash
# Test script to demonstrate enhanced prompts

export CLAUDE_API_KEY="${CLAUDE_API_KEY}"

if [ -z "$CLAUDE_API_KEY" ]; then
    echo "❌ CLAUDE_API_KEY not set"
    echo "Set it with: export CLAUDE_API_KEY='your-key'"
    exit 1
fi

echo "═══════════════════════════════════════════════════════════════"
echo "Testing Enhanced Prompts on DVWA SQL Injection"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "Target: tests/test_targets/DVWA/vulnerabilities/sqli"
echo "Preset: ctf (uses ctf_enhanced + owasp_enhanced)"
echo ""
echo "Watch for enhanced fields:"
echo "  - exploitability_score"
echo "  - data_flow"
echo "  - attack_scenario"
echo "  - time_to_exploit"
echo "  - payload_example"
echo ""
echo "Starting scan..."
echo ""

python3 orchestrator.py tests/test_targets/DVWA/vulnerabilities/sqli ./scanner \
  --preset ctf \
  --verbose

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "Check the output files:"
echo "  - JSON: Look for 'exploitability_score', 'data_flow' fields"
echo "  - HTML: Visual report with all enhanced details"
echo "  - Payloads: Red/Blue team exploitation examples"
echo "═══════════════════════════════════════════════════════════════"
