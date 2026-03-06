#!/usr/bin/env bash
# ============================================================================
# DVMCP Reset — Kill servers, wipe state, restart clean
#
# Brings all 10 DVMCP challenge servers back to a known baseline so that
# scans are reproducible.  Run this before every mcp-attack sweep.
#
# Usage:
#   ./tests/dvmcp_reset.sh                # reset + restart servers
#   ./tests/dvmcp_reset.sh --kill-only    # just kill, don't restart
#   ./tests/dvmcp_reset.sh --scan         # reset, restart, then scan
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DVMCP_DIR="$PROJECT_ROOT/tests/test_targets/DVMCP"
VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"

BOLD="\033[1m"
DIM="\033[2m"
RED="\033[0;31m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
CYAN="\033[0;36m"
RESET="\033[0m"

log()  { echo -e "${BOLD}[dvmcp]${RESET} $*"; }
ok()   { echo -e "  ${GREEN}✓${RESET} $*"; }
warn() { echo -e "  ${YELLOW}!${RESET} $*"; }
err()  { echo -e "  ${RED}✗${RESET} $*"; }

PORTS="9001 9002 9003 9004 9005 9006 9007 9008 9009 9010"

# ── Parse args ─────────────────────────────────────────────────────────────

KILL_ONLY=false
RUN_SCAN=false
for arg in "$@"; do
    case "$arg" in
        --kill-only) KILL_ONLY=true ;;
        --scan)      RUN_SCAN=true ;;
        -h|--help)
            echo "Usage: $0 [--kill-only] [--scan]"
            echo "  --kill-only   Kill servers and wipe state, don't restart"
            echo "  --scan        Reset, restart, then run mcp-attack sweep"
            exit 0
            ;;
        *) echo "Unknown arg: $arg"; exit 1 ;;
    esac
done

# ── Step 1: Kill all DVMCP processes ──────────────────────────────────────

echo ""
echo -e "${BOLD}DVMCP Reset${RESET}"
echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

log "Killing DVMCP servers on ports 9001-9010..."
killed=0
for port in $PORTS; do
    pid=$(lsof -ti ":$port" 2>/dev/null || true)
    if [ -n "$pid" ]; then
        kill "$pid" 2>/dev/null || true
        killed=$((killed + 1))
    fi
done
if [ "$killed" -gt 0 ]; then
    ok "Killed $killed server process(es)"
    sleep 1
else
    ok "No servers running"
fi

# ── Step 2: Wipe all state ────────────────────────────────────────────────

log "Wiping challenge state..."

rm -rf /tmp/dvmcp_challenge3
rm -rf /tmp/dvmcp_challenge4
rm -rf /tmp/dvmcp_challenge6
rm -rf /tmp/dvmcp_challenge8
rm -rf /tmp/dvmcp_challenge10

ok "State directories removed"

# ── Step 3: Recreate clean state ──────────────────────────────────────────

log "Creating fresh test data..."

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

ok "Test data ready"

if $KILL_ONLY; then
    echo ""
    ok "Reset complete (kill-only mode)"
    exit 0
fi

# ── Step 4: Check prerequisites ───────────────────────────────────────────

if [ ! -d "$DVMCP_DIR" ]; then
    err "DVMCP not found at $DVMCP_DIR"
    log "Clone it: git clone https://github.com/harishsg993010/damn-vulnerable-MCP-server.git tests/test_targets/DVMCP"
    exit 1
fi

if [ ! -f "$VENV_PYTHON" ]; then
    err "Python venv not found at $VENV_PYTHON"
    exit 1
fi

# ── Step 5: Start all challenge servers ───────────────────────────────────

challenge_path() {
    case "$1" in
        1)  echo "challenges/easy/challenge1/server_sse.py" ;;
        2)  echo "challenges/easy/challenge2/server_sse.py" ;;
        3)  echo "challenges/easy/challenge3/server_sse.py" ;;
        4)  echo "challenges/medium/challenge4/server_sse.py" ;;
        5)  echo "challenges/medium/challenge5/server_sse.py" ;;
        6)  echo "challenges/medium/challenge6/server_sse.py" ;;
        7)  echo "challenges/medium/challenge7/server_sse.py" ;;
        8)  echo "challenges/hard/challenge8/server_sse.py" ;;
        9)  echo "challenges/hard/challenge9/server_sse.py" ;;
        10) echo "challenges/hard/challenge10/server_sse.py" ;;
    esac
}

challenge_name() {
    case "$1" in
        1)  echo "Basic Prompt Injection" ;;
        2)  echo "Tool Poisoning" ;;
        3)  echo "Excessive Permission Scope" ;;
        4)  echo "Rug Pull Attack" ;;
        5)  echo "Tool Shadowing" ;;
        6)  echo "Indirect Prompt Injection" ;;
        7)  echo "Token Theft" ;;
        8)  echo "Malicious Code Execution" ;;
        9)  echo "Remote Access Control" ;;
        10) echo "Multi-Vector Attack" ;;
    esac
}

log "Starting DVMCP challenge servers..."
cd "$DVMCP_DIR"
for num in 1 2 3 4 5 6 7 8 9 10; do
    port=$((9000 + num))
    path=$(challenge_path "$num")
    name=$(challenge_name "$num")
    "$VENV_PYTHON" "$path" >/dev/null 2>&1 &
    pid=$!
    echo -e "  ${DIM}Challenge $num${RESET} ($name) → port $port [pid $pid]"
done

echo -e "  ${DIM}Waiting for servers to initialize...${RESET}"

# Wait until all 10 ports are listening (up to 15 seconds)
max_wait=15
waited=0
while [ "$waited" -lt "$max_wait" ]; do
    alive=0
    for port in $PORTS; do
        if lsof -i ":$port" >/dev/null 2>&1; then
            alive=$((alive + 1))
        fi
    done
    if [ "$alive" -ge 10 ]; then
        break
    fi
    sleep 1
    waited=$((waited + 1))
done

# Extra settling time for FastAPI to finish initialization
sleep 2

if [ "$alive" -ge 10 ]; then
    ok "All 10 DVMCP servers listening"
elif [ "$alive" -ge 6 ]; then
    warn "$alive/10 servers up after ${waited}s (some may have failed to start)"
else
    err "Only $alive/10 servers up after ${waited}s"
    exit 1
fi

# ── Step 6: Optionally run scan ───────────────────────────────────────────

if $RUN_SCAN; then
    echo ""
    log "Running mcp-attack sweep..."
    cd "$PROJECT_ROOT"
    "$VENV_PYTHON" -m mcp_attack --port-range localhost:9001-9010 --verbose
fi

echo ""
ok "DVMCP ready — all challenges at baseline"
echo ""
echo -e "  ${CYAN}Scan:${RESET}  python3 -m mcp_attack --port-range localhost:9001-9010 --verbose"
echo -e "  ${CYAN}Kill:${RESET}  $0 --kill-only"
echo -e "  ${CYAN}Reset:${RESET} $0"
echo ""
