# mcp_attack — MCP Red Teaming Scanner

Standalone MCP security scanner for red teaming and auditing Model Context
Protocol servers. Combines **static metadata analysis** with **active behavioral
probing** — it connects to MCP servers, enumerates tools/resources/prompts,
then actually calls tools with safe payloads and analyzes what comes back.

Use with [DVMCP](https://github.com/harishsg993010/damn-vulnerable-MCP-server)
for training, or point at any MCP server in dev/staging/prod.

**See [CHANGELOG.md](CHANGELOG.md) for recent changes and planned work.**

---

## Install

**Option A — uv (recommended):**
```bash
cd agentsmith
uv pip install -e .              # installs agentsmith + mcp-attack CLI
mcp-attack --targets http://localhost:2266
```

**Option B — pip + venv:**
```bash
cd agentsmith
source .venv/bin/activate        # or: source scripts/activate.sh
pip install -e .                 # installs agentsmith + mcp-attack CLI
mcp-attack --targets http://localhost:2266
```

**Option C — No install (run as module):**
```bash
cd agentsmith
source .venv/bin/activate
python3 -m mcp_attack --targets http://localhost:2266
```

---

## Quick Start

```bash
# Single target
mcp-attack --targets http://localhost:2266

# DVMCP challenges 1–10
mcp-attack --port-range localhost:9001-9010 --verbose

# Authenticated endpoint (JWT, PAT, etc.)
mcp-attack --targets https://api.githubcopilot.com/mcp/ --auth-token ghp_xxx

# JSON report for CI
mcp-attack --port-range localhost:9001-9010 --json report.json

# Differential scan (compare to baseline)
mcp-attack --targets http://localhost:9001 --baseline baseline.json
```

All commands also work as `mcp-audit` or `python3 -m mcp_attack`.

---

## How It Works

```
1. CONNECT        Detect transport (SSE or Streamable HTTP)
2. ENUMERATE      initialize → tools/list → resources/list → prompts/list
3. STATIC CHECKS  Pattern-match metadata (names, descriptions, schemas)
4. PROBE          Call tools with safe payloads, read resources
5. ANALYZE        Scan responses for injection, exfil, leakage, drift
6. AGGREGATE      Detect attack chains across findings
7. REPORT         Console table + optional JSON
```

### Scan Phases

The scanner runs checks in a deliberate order:

| Phase | Checks | What Happens |
|-------|--------|-------------|
| **Static** | prompt_injection, tool_poisoning, excessive_permissions, token_theft, code_execution, remote_access, schema_risks, rate_limit, prompt_leakage, supply_chain, tool_shadowing | Pattern-match on tool names, descriptions, schemas. No server interaction beyond enumeration. |
| **Behavioral** | rug_pull, indirect_injection, protocol_robustness | Light interaction: re-list tools, read resources, send invalid methods. |
| **Deep Probes** | deep_rug_pull, tool_response_injection, input_sanitization, error_leakage, temporal_consistency, resource_poisoning, state_mutation, notification_abuse | Active tool invocation with safe payloads. Analyze responses for threats. |
| **Transport** | sse_security | CORS, unauthenticated SSE, cross-origin POST. |
| **Aggregate** | multi_vector, attack_chains | Cross-reference all prior findings to detect compound threats. |

---

## Security Checks Reference

### Static Checks (metadata only)

| Check | Severity | What It Detects |
|-------|----------|----------------|
| `prompt_injection` | CRITICAL | Injection payloads in tool/resource/prompt descriptions |
| `tool_poisoning` | CRITICAL | Hidden instructions, invisible Unicode in tool descriptions |
| `excessive_permissions` | CRITICAL–MEDIUM | Dangerous capabilities (shell, filesystem, network, DB, cloud) |
| `code_execution` | CRITICAL–HIGH | Tools with exec/eval/shell parameters or descriptions |
| `remote_access` | CRITICAL–HIGH | Reverse shells, C2 beacons, port forwarding, data exfil |
| `token_theft` | CRITICAL–HIGH | Tools that accept or forward credentials as parameters |
| `supply_chain` | CRITICAL | Dynamic package install from user-controlled URLs |
| `schema_risk` | CRITICAL–MEDIUM | Command params, unbounded strings, freeform objects |
| `tool_shadowing` | HIGH–MEDIUM | Tool names that collide with common tools or other servers |
| `prompt_leakage` | HIGH | Tools that may echo, log, or expose internal prompts |
| `rate_limit` | MEDIUM | Descriptions suggesting unbounded/unthrottled usage |

### Behavioral Checks (active server interaction)

| Check | Severity | What It Detects |
|-------|----------|----------------|
| `rug_pull` | CRITICAL–HIGH | Tool list changes between two `tools/list` calls |
| `deep_rug_pull` | CRITICAL | Tool list/schema changes **after invoking tools** — catches state-dependent rug pulls that the shallow check misses |
| `tool_response_injection` | CRITICAL–HIGH | Injection payloads, exfil URLs, hidden content, invisible Unicode, or base64-encoded attacks in tool **responses** |
| `cross_tool_manipulation` | HIGH | Tool output that directs the LLM to invoke a different tool |
| `input_sanitization` | CRITICAL–HIGH | Path traversal, command injection, template injection, SQL injection probes reflected unsanitized |
| `error_leakage` | HIGH–MEDIUM | Stack traces, internal paths, connection strings, or secrets in error responses |
| `temporal_consistency` | CRITICAL–MEDIUM | Escalating injection, wildly inconsistent responses, or new threats across repeated identical calls |
| `resource_poisoning` | CRITICAL–HIGH | Base64-encoded injection, data URIs, steganographic Unicode, CSS-hidden HTML, or markdown image exfiltration in resource content |
| `state_mutation` | HIGH–MEDIUM | Resources that appear, disappear, or change content after tool invocations |
| `notification_abuse` | CRITICAL–MEDIUM | Unsolicited `sampling/createMessage`, `roots/list`, or other server-initiated requests |
| `indirect_injection` | CRITICAL–HIGH | Injection/poison patterns and exfil URLs in resource content |

### Transport & Aggregate Checks

| Check | Severity | What It Detects |
|-------|----------|----------------|
| `auth` | HIGH | Unauthenticated MCP initialize accepted |
| `sse_security` | HIGH–MEDIUM | Unauthenticated SSE stream, CORS misconfiguration, cross-origin POST |
| `multi_vector` | CRITICAL | 2+ dangerous vulnerability categories active on one server |
| `attack_chain` | CRITICAL | Linked vulnerability pairs (e.g. `input_sanitization → code_execution`) |

---

## Behavioral Probing Methodology

The deep probe checks **call tools on the target server** using safe,
non-destructive payloads. Here's how it works:

### Safe Argument Generation

For each tool, the scanner reads the `inputSchema` and generates minimal
arguments using context-aware safe values:

| Parameter Pattern | Safe Value |
|------------------|-----------|
| `path`, `file`, `dir` | `/tmp/mcp_probe_MCP_PROBE_8f4c2a` |
| `command`, `exec` | `echo hello` |
| `expression`, `code` | `1+1` |
| `url`, `endpoint` | `http://example.com/test` |
| `username`, `name` | `probe_user` |
| `password`, `token` | `MCP_PROBE_8f4c2a` (canary) |
| Enum params | First enum value |
| Everything else | `test` |

Only **required** parameters are filled. Optional params are skipped to
minimize side effects.

### Injection Probes

For `input_sanitization`, the scanner sends targeted probes based on
parameter semantics:

| Param Type | Probe Examples |
|-----------|---------------|
| File/path params | `../../../tmp/MCP_PROBE_8f4c2a`, path null bytes |
| Command params | `test; echo MCP_PROBE_8f4c2a`, pipe/backtick variants |
| Query/SQL params | `' OR '1'='1`, `UNION SELECT` |
| Other strings | `{{7*7}}`, `${7*7}`, ERB/Jinja templates |

The canary string `MCP_PROBE_8f4c2a` is embedded in probes. If it appears
in the response, the tool reflected input without sanitization.

### Response Analysis

Every tool response is scanned for:

- **Injection payloads** — "ignore previous instructions", role overrides, system prompt markers
- **Exfiltration URLs** — webhook, ngrok, burp, requestbin, pipedream, interactsh
- **Hidden content** — HTML comments, `<hidden>` blocks, `<script>` tags
- **Invisible Unicode** — zero-width chars, bidi overrides, invisible formatters
- **Base64-encoded attacks** — decoded and re-scanned for injection patterns
- **Cross-tool references** — "call tool X", "invoke function Y"

---

## CLI Reference

```
mcp-attack [OPTIONS]

Target Selection:
  --targets URL [URL ...]     One or more MCP target URLs
  --port-range HOST:START-END Scan a port range (e.g. localhost:9001-9010)
  --targets-file FILE         Read URLs from file (one per line, # comments)
  --public-targets            Use built-in public targets list

Authentication:
  --auth-token TOKEN          Bearer token for authenticated endpoints
                              (or set MCP_AUTH_TOKEN env var)

Scan Options:
  --timeout SEC               Per-target connection timeout (default: 25)
  --workers N                 Parallel scan workers (default: 4)

Safety Controls:
  --no-invoke                 Static-only: skip all behavioral probes (safe for production)
  --safe-mode                 Skip dangerous tools (delete/send/exec/write), probe read-only
  --probe-calls N             Invocations per tool for deep rug pull (default: 6)

Output:
  --json FILE                 Write JSON report to FILE
  --verbose, -v               Verbose output
  --debug                     Debug output (very noisy)

Differential:
  --baseline FILE             Compare against baseline
  --save-baseline FILE        Save scan as baseline

Kubernetes:
  --k8s-namespace NS          Namespace for internal checks (default: default)
  --no-k8s                    Skip Kubernetes checks
```

### Scan Modes

| Mode | Flag | What Runs | Use Case |
|------|------|-----------|----------|
| **Full** | (default) | Static + all behavioral probes | Dev/staging, DVMCP, CTFs |
| **Safe** | `--safe-mode` | Static + probes on read-only tools only | Prod servers with mixed tool risk |
| **Static** | `--no-invoke` | Static checks only, no tool calls | Prod servers, zero side-effect risk |

Tools are classified as **dangerous** if their name contains keywords like
`delete`, `execute`, `send`, `write`, `deploy`, `kill`, `transfer`, etc.
In `--safe-mode`, these are skipped while read-only tools (`get`, `list`,
`search`, `check`, `verify`, etc.) are still probed.

---

## Quickstart Scenarios

### Scan DVMCP (all 10 challenges)

```bash
# Terminal 1: start challenge servers
./tests/test_dvmcp.sh --setup-only

# Terminal 2: scan
mcp-attack --port-range localhost:9001-9010 --verbose
```

### Authenticated endpoint (GitHub MCP)

```bash
mcp-attack --targets https://api.githubcopilot.com/mcp/ --auth-token ghp_xxx

# Or via env var
export MCP_AUTH_TOKEN=ghp_xxx
mcp-attack --targets https://api.githubcopilot.com/mcp/
```

### Remote public MCP (DeepWiki)

```bash
mcp-attack --targets https://mcp.deepwiki.com/mcp
```

Use `/mcp` (Streamable HTTP), not `/sse`.

### Differential scan

```bash
# Save baseline
mcp-attack --targets http://localhost:9001 --save-baseline baseline.json

# Later: detect regressions
mcp-attack --targets http://localhost:9001 --baseline baseline.json
```

Reports added/removed/modified tools, resources, prompts. New tools
flagged as MEDIUM for review.

### JSON report for CI

```bash
mcp-attack --port-range localhost:9001-9010 --json report.json
```

Exit code is 1 if any CRITICAL or HIGH findings; 0 otherwise. Use in
CI pipelines to gate deployments.

### Run tests

```bash
python3 -m pytest mcp_attack/tests/ -v
```

---

## Project Structure

```
mcp_attack/
├── core/
│   ├── constants.py     # Protocol versions, severity weights, attack chain patterns
│   ├── enumerator.py    # MCP handshake: initialize → list tools/resources/prompts
│   ├── models.py        # Finding, TargetResult dataclasses
│   └── session.py       # SSE + HTTP transport detection and JSON-RPC session
├── patterns/
│   ├── rules.py         # Static regex patterns (injection, poison, theft, exec, etc.)
│   └── probes.py        # Behavioral probe payloads, canary strings, response analysis
├── checks/
│   ├── __init__.py      # Check registry and run_all_checks() orchestrator
│   ├── base.py          # time_check context manager
│   ├── injection.py     # prompt_injection, tool_poisoning, indirect_injection
│   ├── permissions.py   # excessive_permissions, schema_risks
│   ├── behavioral.py    # rug_pull, deep_rug_pull, state_mutation, notification_abuse
│   ├── tool_probes.py   # tool_response_injection, input_sanitization, error_leakage,
│   │                    # temporal_consistency, resource_poisoning, cross_tool_manipulation
│   ├── theft.py         # token_theft
│   ├── execution.py     # code_execution, remote_access
│   ├── chaining.py      # tool_shadowing, multi_vector, attack_chains
│   ├── transport.py     # sse_security (CORS, unauth SSE, cross-origin POST)
│   ├── rate_limit.py    # rate_limit
│   ├── prompt_leakage.py # prompt_leakage
│   └── supply_chain.py  # supply_chain
├── data/                # Built-in public_targets.txt
├── diff.py              # Differential scanning (baseline save/load/compare)
├── k8s/                 # Kubernetes internal checks (optional, needs SA token)
├── reporting/
│   ├── console.py       # Rich table output
│   └── json_out.py      # JSON report writer
├── tests/               # Pytest suite
├── scanner.py           # Scan orchestration, parallel execution, cross-target analysis
├── cli.py               # Argument parsing
├── mcp_audit.py         # Alternate entry point
└── __main__.py          # python -m mcp_attack entry point
```

---

## Risk Scoring

```
Score = SUM(finding_weights)

  CRITICAL  →  10 points
  HIGH      →   7 points
  MEDIUM    →   4 points
  LOW       →   1 point

Rating:
  ≥ 20  →  CRITICAL
  ≥ 10  →  HIGH
  ≥  5  →  MEDIUM
  ≥  1  →  LOW
     0  →  CLEAN
```

---

## Attack Chain Detection

After all individual checks run, the scanner looks for **linked
vulnerability pairs** that combine into compound attack paths:

| Chain | Risk |
|-------|------|
| `prompt_injection → code_execution` | Injection leads to RCE |
| `prompt_injection → token_theft` | Injection leads to credential exfil |
| `code_execution → token_theft` | RCE used to steal credentials |
| `code_execution → remote_access` | RCE to persistent access |
| `indirect_injection → token_theft` | Poisoned data exfils creds |
| `tool_response_injection → cross_tool_manipulation` | Output hijacks tool flow |
| `deep_rug_pull → tool_poisoning` | Post-trust tool mutation |
| `input_sanitization → code_execution` | Unsanitized input to RCE |
| `resource_poisoning → tool_response_injection` | Poisoned resource feeds tool |
| `cross_tool_manipulation → token_theft` | Tool chaining steals creds |

Chains are reported as CRITICAL and appear in the "Attack Chains Detected"
section of the scan output.

---

## Testing with DVMCP

[DVMCP](https://github.com/harishsg993010/damn-vulnerable-MCP-server) provides
10 deliberately vulnerable MCP servers for testing:

| Challenge | Port | Vulnerability |
|-----------|------|--------------|
| 1. Basic Prompt Injection | 9001 | Sensitive credentials in resources |
| 2. Tool Poisoning | 9002 | `execute_command` with `shell=True` |
| 3. Excessive Permissions | 9003 | `file_manager` with read/write/delete |
| 4. Rug Pull Attack | 9004 | Tool behavior changes after N calls |
| 5. Tool Shadowing | 9005 | Tool name conflicts |
| 6. Indirect Prompt Injection | 9006 | Injection via data sources |
| 7. Token Theft | 9007 | Passwords/tokens as parameters |
| 8. Code Execution | 9008 | `eval()` on user input |
| 9. Remote Access Control | 9009 | Command injection via `remote_access` |
| 10. Multi-Vector Attack | 9010 | Chained vulnerabilities |

```bash
# One-time setup
git clone https://github.com/harishsg993010/damn-vulnerable-MCP-server.git \
    tests/test_targets/DVMCP

# Reset to baseline + start servers + scan (recommended)
./tests/dvmcp_reset.sh --scan

# Or step by step:
./tests/dvmcp_reset.sh                  # reset + start servers
mcp-attack --port-range localhost:9001-9010 --verbose

# Scan specific challenges
mcp-attack --targets http://localhost:9002 http://localhost:9008

# Deeper rug pull probing (more calls per tool)
mcp-attack --port-range localhost:9001-9010 --probe-calls 10

# Static-only scan (no tool calls)
mcp-attack --port-range localhost:9001-9010 --no-invoke

# Kill servers + clean state
./tests/dvmcp_reset.sh --kill-only
```

---

## Exit Code

Exits **1** if any CRITICAL or HIGH findings; **0** otherwise.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and planned work.
