#!/usr/bin/env bash
# ============================================================================
# Agent Smith — DVMCP (Damn Vulnerable MCP) Test Suite
#
# Launches the DVMCP challenge servers, scans each one with scan_mcp,
# and reports findings. Requires:
#   - Agent Smith MCP server running on port 2266
#   - DVMCP cloned at tests/test_targets/DVMCP
#
# Usage:
#   ./tests/test_dvmcp.sh              # scan all 10 challenges
#   ./tests/test_dvmcp.sh 1 8 9        # scan specific challenges
#   ./tests/test_dvmcp.sh --setup-only # just start DVMCP servers
#   ./tests/test_dvmcp.sh --kill       # just kill DVMCP servers
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DVMCP_DIR="$PROJECT_ROOT/tests/test_targets/DVMCP"
VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"
AGENTSMITH_URL="${AGENTSMITH_URL:-http://localhost:2266/sse}"
DVMCP_PIDS=()

# Colors
BOLD="\033[1m"
DIM="\033[2m"
RED="\033[0;31m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
CYAN="\033[0;36m"
RESET="\033[0m"

# Challenge metadata
declare -A CHALLENGE_NAMES=(
    [1]="Basic Prompt Injection"
    [2]="Tool Poisoning"
    [3]="Excessive Permission Scope"
    [4]="Rug Pull Attack"
    [5]="Tool Shadowing"
    [6]="Indirect Prompt Injection"
    [7]="Token Theft"
    [8]="Malicious Code Execution"
    [9]="Remote Access Control"
    [10]="Multi-Vector Attack"
)

declare -A CHALLENGE_PORTS=(
    [1]=9001 [2]=9002 [3]=9003 [4]=9004 [5]=9005
    [6]=9006 [7]=9007 [8]=9008 [9]=9009 [10]=9010
)

declare -A CHALLENGE_PATHS=(
    [1]="challenges/easy/challenge1/server_sse.py"
    [2]="challenges/easy/challenge2/server_sse.py"
    [3]="challenges/easy/challenge3/server_sse.py"
    [4]="challenges/medium/challenge4/server_sse.py"
    [5]="challenges/medium/challenge5/server_sse.py"
    [6]="challenges/medium/challenge6/server_sse.py"
    [7]="challenges/medium/challenge7/server_sse.py"
    [8]="challenges/hard/challenge8/server_sse.py"
    [9]="challenges/hard/challenge9/server_sse.py"
    [10]="challenges/hard/challenge10/server_sse.py"
)

# ============================================================================
# Helpers
# ============================================================================

log()  { echo -e "${BOLD}[agentsmith]${RESET} $*"; }
ok()   { echo -e "  ${GREEN}✓${RESET} $*"; }
warn() { echo -e "  ${YELLOW}!${RESET} $*"; }
err()  { echo -e "  ${RED}✗${RESET} $*"; }

check_prereqs() {
    if [[ ! -d "$DVMCP_DIR" ]]; then
        err "DVMCP not found at $DVMCP_DIR"
        log "Clone it with: git clone https://github.com/harishsg993010/damn-vulnerable-MCP-server.git tests/test_targets/DVMCP"
        exit 1
    fi

    if [[ ! -f "$VENV_PYTHON" ]]; then
        err "Python venv not found at $VENV_PYTHON"
        exit 1
    fi

    # Check Agent Smith MCP server is running
    if ! curl -s "$AGENTSMITH_URL" >/dev/null 2>&1; then
        health_url="${AGENTSMITH_URL%/sse}/health"
        if ! curl -s "$health_url" >/dev/null 2>&1; then
            err "Agent Smith MCP server not reachable at $AGENTSMITH_URL"
            log "Start it with: python3 -m mcp_server --no-auth"
            exit 1
        fi
    fi
}

setup_dvmcp_dirs() {
    # Create directories needed by DVMCP challenges
    mkdir -p /tmp/dvmcp_challenge3/public /tmp/dvmcp_challenge3/private
    mkdir -p /tmp/dvmcp_challenge4/state
    mkdir -p /tmp/dvmcp_challenge6/user_uploads
    mkdir -p /tmp/dvmcp_challenge8/sensitive
    mkdir -p /tmp/dvmcp_challenge10/config

    echo '{"weather_tool_calls": 0}' > /tmp/dvmcp_challenge4/state/state.json
    echo "Welcome to the public directory!" > /tmp/dvmcp_challenge3/public/welcome.txt
    echo "CONFIDENTIAL: Employee Salary Information" > /tmp/dvmcp_challenge3/private/employee_salaries.txt
    echo "SYSTEM CONFIG" > /tmp/dvmcp_challenge10/config/system.conf
    echo '{"admin_token": "test-jwt-token"}' > /tmp/dvmcp_challenge10/config/tokens.json
}

start_challenge() {
    local num=$1
    local port=${CHALLENGE_PORTS[$num]}
    local path=${CHALLENGE_PATHS[$num]}
    local name=${CHALLENGE_NAMES[$num]}

    # Check if port is already in use
    if lsof -i ":$port" >/dev/null 2>&1; then
        warn "Port $port already in use, skipping Challenge $num"
        return 0
    fi

    cd "$DVMCP_DIR"
    "$VENV_PYTHON" "$path" >/dev/null 2>&1 &
    local pid=$!
    DVMCP_PIDS+=("$pid")
    echo -e "  ${DIM}Challenge $num${RESET} ($name) → port $port [pid $pid]"
    return 0
}

kill_dvmcp() {
    log "Stopping DVMCP servers..."
    for port in 9001 9002 9003 9004 9005 9006 9007 9008 9009 9010; do
        local pid
        pid=$(lsof -ti ":$port" 2>/dev/null || true)
        if [[ -n "$pid" ]]; then
            kill "$pid" 2>/dev/null || true
            echo -e "  ${DIM}Killed port $port (pid $pid)${RESET}"
        fi
    done
    # Also kill tracked PIDs
    for pid in "${DVMCP_PIDS[@]}"; do
        kill "$pid" 2>/dev/null || true
    done
    ok "All DVMCP servers stopped"
}

scan_challenge() {
    local num=$1
    local port=${CHALLENGE_PORTS[$num]}
    local name=${CHALLENGE_NAMES[$num]}
    local url="http://localhost:$port/sse"

    echo ""
    echo -e "${BOLD}━━━ Challenge $num: $name (port $port) ━━━${RESET}"

    # Quick check if server is responding
    if ! curl -s "http://localhost:$port/" >/dev/null 2>&1; then
        err "Server on port $port not responding, skipping"
        return 1
    fi

    # Call scan_mcp via the Agent Smith MCP server
    local result
    result=$("$VENV_PYTHON" -c "
import asyncio, json, sys

async def scan():
    from mcp.client.sse import sse_client
    from mcp import ClientSession

    ctx = sse_client('$AGENTSMITH_URL')
    rs, ws = await ctx.__aenter__()
    session = ClientSession(rs, ws)
    await session.__aenter__()
    await session.initialize()

    result = await session.call_tool('scan_mcp', {
        'target_url': '$url',
        'transport': 'sse',
        'timeout': 10,
    })

    await session.__aexit__(None, None, None)
    await ctx.__aexit__(None, None, None)

    data = json.loads(result.content[0].text)
    return data

try:
    data = asyncio.run(scan())
    print(json.dumps(data))
except Exception as e:
    print(json.dumps({'error': str(e)}))
" 2>/dev/null)

    if echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if 'error' not in d else 1)" 2>/dev/null; then
        # Parse and display results
        echo "$result" | "$VENV_PYTHON" -c "
import sys, json

d = json.load(sys.stdin)
s = d.get('summary', {})
risk = s.get('risk_score', '?')
total = s.get('total_findings', 0)
by_sev = s.get('by_severity', {})
tools = d.get('tools', [])
findings = d.get('findings', [])

colors = {'CRITICAL': '\033[0;31m', 'HIGH': '\033[0;31m', 'MEDIUM': '\033[0;33m', 'LOW': '\033[0;36m', 'INFO': '\033[2m', 'CLEAN': '\033[0;32m'}
R = '\033[0m'
B = '\033[1m'

risk_c = colors.get(risk, '')
print(f'  {B}Risk:{R}     {risk_c}{risk}{R}')
print(f'  {B}Findings:{R} {total}')

parts = []
for sev in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO']:
    if sev in by_sev:
        parts.append(f'{colors[sev]}{sev}: {by_sev[sev]}{R}')
if parts:
    print(f'  {B}Severity:{R} {\", \".join(parts)}')

print(f'  {B}Tools:{R}    {s.get(\"total_tools\", 0)}  Resources: {s.get(\"total_resources\", 0)}  Prompts: {s.get(\"total_prompts\", 0)}')

if tools:
    names = ', '.join(t['name'] for t in tools[:5])
    more = f' +{len(tools)-5} more' if len(tools) > 5 else ''
    print(f'  {B}Exposed:{R}  {names}{more}')

sev_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3, 'INFO': 4}
findings.sort(key=lambda f: sev_order.get(f.get('severity', 'INFO'), 5))
for f in findings[:5]:
    sev = f.get('severity', '?')
    c = colors.get(sev, '')
    title = f.get('title', '?')[:65]
    tool = f.get('tool', f.get('resource', ''))
    loc = f' ({tool})' if tool else ''
    print(f'  {c}[{sev}]{R} {title}{loc}')
if len(findings) > 5:
    print(f'  \033[2m... and {len(findings) - 5} more\033[0m')
"
        return 0
    else
        local error
        error=$(echo "$result" | python3 -c "import sys,json; print(json.load(sys.stdin).get('error','unknown'))" 2>/dev/null || echo "parse error")
        err "Scan failed: $error"
        return 1
    fi
}

# ============================================================================
# Main
# ============================================================================

trap kill_dvmcp EXIT

# Parse args
CHALLENGES=()
SETUP_ONLY=false
KILL_ONLY=false

for arg in "$@"; do
    case "$arg" in
        --setup-only) SETUP_ONLY=true ;;
        --kill)       KILL_ONLY=true ;;
        [0-9]*)       CHALLENGES+=("$arg") ;;
        *)            echo "Usage: $0 [--setup-only|--kill] [challenge_numbers...]"; exit 1 ;;
    esac
done

# Default: all 10 challenges
if [[ ${#CHALLENGES[@]} -eq 0 ]]; then
    CHALLENGES=(1 2 3 4 5 6 7 8 9 10)
fi

if $KILL_ONLY; then
    kill_dvmcp
    exit 0
fi

echo ""
echo -e "${BOLD}Agent Smith — DVMCP Security Scan${RESET}"
echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "  Scanner:    ${CYAN}$AGENTSMITH_URL${RESET}"
echo -e "  DVMCP:      ${DIM}$DVMCP_DIR${RESET}"
echo -e "  Challenges: ${#CHALLENGES[@]}"
echo ""

check_prereqs

# Setup DVMCP data directories
log "Setting up DVMCP test data..."
setup_dvmcp_dirs
ok "Test data ready"

# Start challenge servers
log "Starting DVMCP challenge servers..."
for num in "${CHALLENGES[@]}"; do
    start_challenge "$num"
done

# Wait for servers to be ready
echo -e "  ${DIM}Waiting for servers to start...${RESET}"
sleep 3

if $SETUP_ONLY; then
    ok "DVMCP servers running. Press Ctrl+C to stop."
    wait
    exit 0
fi

# Scan each challenge
log "Scanning DVMCP challenges..."
PASSED=0
FAILED=0
TOTAL_FINDINGS=0

for num in "${CHALLENGES[@]}"; do
    if scan_challenge "$num"; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
done

# Summary
echo ""
echo -e "${BOLD}━━━ Summary ━━━${RESET}"
echo -e "  Scanned:  ${#CHALLENGES[@]} challenges"
echo -e "  Success:  ${GREEN}$PASSED${RESET}"
if [[ $FAILED -gt 0 ]]; then
    echo -e "  Failed:   ${RED}$FAILED${RESET}"
fi
echo ""

# Cleanup happens via trap
