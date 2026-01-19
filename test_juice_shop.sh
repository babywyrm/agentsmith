#!/bin/bash
# Test script for Juice-Shop with full feature set

echo "🧪 Testing SCRYNET with Juice-Shop"
echo "=================================="
echo ""
echo "Test Configuration:"
echo "  Target: ./test_targets/juice-shop"
echo "  Profiles: owasp,ctf"
echo "  Deduplication: ENABLED"
echo "  Payloads: ENABLED"
echo "  Annotations: ENABLED"
echo "  Prioritization: ENABLED (top 10 files)"
echo "  Cost Tracking: AUTOMATIC"
echo ""

# Check if --estimate-only flag is passed
if [ "$1" == "--estimate-only" ]; then
    echo "💰 Running cost estimation only (no API calls)..."
    echo ""
    python3 scrynet.py hybrid ./test_targets/juice-shop ./scanner \
      --profile owasp,ctf \
      --prioritize \
      --prioritize-top 10 \
      --question "find authentication bypass, SQL injection, XSS, and NoSQL injection vulnerabilities" \
      --deduplicate \
      --dedupe-threshold 0.7 \
      --dedupe-strategy keep_highest_severity \
      --generate-payloads \
      --annotate-code \
      --top-n 5 \
      --export-format json csv markdown html \
      --output-dir test-reports/juice-shop-test \
      --verbose \
      --estimate-cost
else
    echo "🚀 Running full scan with cost tracking..."
    echo ""
    python3 scrynet.py hybrid ./test_targets/juice-shop ./scanner \
      --profile owasp,ctf \
      --prioritize \
      --prioritize-top 10 \
      --question "find authentication bypass, SQL injection, XSS, and NoSQL injection vulnerabilities" \
      --deduplicate \
      --dedupe-threshold 0.7 \
      --dedupe-strategy keep_highest_severity \
      --generate-payloads \
      --annotate-code \
      --top-n 5 \
      --export-format json csv markdown html \
      --output-dir test-reports/juice-shop-test \
      --verbose

    echo ""
    echo "✅ Test complete!"
    echo ""
    echo "Check results:"
    echo "  ls -lh test-reports/juice-shop-test/"
    echo "  cat test-reports/juice-shop-test/cost_tracking.json | jq '.summary'"
    echo "  cat test-reports/juice-shop-test/combined_findings.json | jq 'length'"
fi
