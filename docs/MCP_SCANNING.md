# MCP Server Security Scanning Guide

Agent Smith includes `scan_mcp` — a security scanner purpose-built for auditing
[Model Context Protocol](https://modelcontextprotocol.io/) servers. It connects
to any MCP server, enumerates its entire attack surface, and runs 14 security
heuristics covering OWASP-aligned vulnerability classes.

This guide walks through the full scanning workflow using the
[Damn Vulnerable MCP Server (DVMCP)](https://github.com/harishsg993010/damn-vulnerable-MCP-server)
as a live target.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        Your Terminal / IDE                        │
│                                                                  │
│   ┌─────────────────┐          ┌──────────────────────────────┐  │
│   │  MCP Client      │  scan_  │  Agent Smith MCP Server      │  │
│   │  (test_client /  │──mcp──▶│  :2266                        │  │
│   │   Cursor / CLI)  │         │                              │  │
│   └─────────────────┘          │  ┌────────────────────────┐  │  │
│                                │  │  scan_mcp handler       │  │  │
│                                │  │                        │  │  │
│                                │  │  1. Validate URL       │  │  │
│                                │  │  2. Check transport    │  │  │
│                                │  │  3. Spawn subprocess ──┼──┼──┼──┐
│                                │  │  4. Analyze results    │  │  │  │
│                                │  │  5. Return findings    │  │  │  │
│                                │  └────────────────────────┘  │  │  │
│                                └──────────────────────────────┘  │  │
└──────────────────────────────────────────────────────────────────┘  │
                                                                     │
      ┌──────────────────────────────────────────────────────────────┘
      │  Isolated subprocess (MCP client)
      │
      ▼
┌──────────────────────────────────────────────────────────────────┐
│                    Target MCP Server                              │
│                    (e.g., DVMCP :9001)                            │
│                                                                  │
│   SSE /sse  ◄────── MCP Protocol Handshake                       │
│                                                                  │
│   ┌──────────────────────────────────────────────────────────┐   │
│   │  initialize()                                            │   │
│   │  list_tools()      → tool names, descriptions, schemas   │   │
│   │  list_resources()  → resource URIs and metadata          │   │
│   │  list_prompts()    → prompt templates                    │   │
│   └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│   Enumerated data returned to Agent Smith for analysis           │
└──────────────────────────────────────────────────────────────────┘
```

### Why a Subprocess?

The `scan_mcp` handler runs the MCP client connection in an isolated subprocess.
This prevents async context conflicts between Agent Smith's own MCP server event
loop and the outbound client connection to the target. It also provides security
isolation — a malicious target server cannot corrupt the scanner's process.

---

## Scan Flow (Step by Step)

```
scan_mcp called with target_url
        │
        ▼
┌───────────────────┐
│ 1. URL Validation  │  Reject non-http(s), check length
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 2. Transport Check │  Flag HTTP as CWE-319 (cleartext)
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 3. Health Probe    │  GET /health — grab server metadata
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 4. MCP Connect     │  Subprocess: SSE or Streamable HTTP
│    (subprocess)    │  initialize → list_tools → list_resources
└────────┬──────────┘  → list_prompts
         │
         │  If connection rejected (401/403):
         │  ──▶ Report: "Auth required" (good)
         │
         │  If connection succeeds without auth:
         │  ──▶ Finding: "No auth required" (CWE-306)
         │
         ▼
┌───────────────────┐
│ 5. Tool Analysis   │  For each tool:
│                    │  ├─ Name pattern matching (exec, shell, eval...)
│                    │  ├─ Description analysis (dangerous capabilities)
│                    │  ├─ Parameter risk assessment (paths, commands, URLs)
│                    │  ├─ Input validation check (maxLength, enum, bounds)
│                    │  ├─ Credential parameter detection (password, token)
│                    │  ├─ Excessive permissions check (read+write+delete)
│                    │  └─ Tool poisoning detection (hidden instructions)
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 6. Resource        │  For each resource:
│    Analysis        │  ├─ Sensitive URI patterns (secret, key, password)
│                    │  └─ File system exposure (file:// URIs)
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 7. Risk Scoring    │  CRITICAL (≥20) / HIGH (≥10) / MEDIUM (≥5) /
│                    │  LOW (≥1) / CLEAN (0)
└────────┬──────────┘  Weights: CRITICAL=10, HIGH=5, MEDIUM=2, LOW=1
         │
         ▼
┌───────────────────┐
│ 8. Return Report   │  JSON with findings, tools, resources,
│                    │  prompts, summary, risk score
└───────────────────┘
```

---

## Security Checks Reference

### Transport & Authentication

| # | Check | Severity | CWE | What It Catches |
|---|-------|----------|-----|-----------------|
| 1 | Unencrypted transport | MEDIUM | CWE-319 | HTTP instead of HTTPS |
| 2 | No authentication | HIGH | CWE-306 | Server accepts unauthenticated connections |
| 3 | Auth enforced | INFO | — | Server correctly rejects without credentials |

### Dangerous Tool Capabilities

| # | Check | Severity | CWE | Pattern Examples |
|---|-------|----------|-----|-----------------|
| 4 | Command/code execution | CRITICAL | CWE-78 | `exec`, `shell`, `eval`, `system`, `spawn` |
| 5 | File write/delete | HIGH | CWE-73 | `write_file`, `delete_file`, `upload`, `remove` |
| 6 | Network/SSRF | HIGH | CWE-918 | `fetch`, `http_request`, `curl`, `proxy` |
| 7 | Database access | HIGH | CWE-89 | `query`, `sql`, `db_exec`, `raw_query` |
| 8 | File read | MEDIUM | CWE-22 | `read_file`, `list_dir`, `browse`, `glob` |
| 9 | Environment access | MEDIUM | CWE-200 | `get_env`, `config`, `secret` |
| 10 | Auth/authz control | HIGH | CWE-287 | `authenticate`, `manage_permissions`, `grant_access` |
| 11 | Excessive permissions | HIGH | CWE-250 | Tools combining read + write + delete |

### Input Validation

| # | Check | Severity | CWE | What It Catches |
|---|-------|----------|-----|-----------------|
| 12 | Path traversal params | MEDIUM | CWE-22 | `path`, `file`, `dir` params without constraints |
| 13 | Injection params | MEDIUM | CWE-74 | `query`, `command`, `code` params without constraints |
| 14 | SSRF params | MEDIUM | CWE-918 | `url`, `endpoint`, `host` params without constraints |
| 15 | Unbounded strings | LOW | CWE-20 | Required strings with no maxLength/enum/pattern |
| 16 | Unbounded integers | LOW | CWE-20 | Integers with no min/max bounds |

### Advanced Detection

| # | Check | Severity | CWE | What It Catches |
|---|-------|----------|-----|-----------------|
| 17 | Tool poisoning | CRITICAL | CWE-94 | Hidden instructions in tool descriptions |
| 18 | Credential exposure | HIGH | CWE-522 | Password/token/secret accepted as tool parameters |
| 19 | Sensitive resources | HIGH | CWE-200 | Resources with secret/credential/key in URI |
| 20 | File system resources | MEDIUM | CWE-22 | Resources exposing `file://` URIs |
| 21 | Experimental features | LOW | CWE-1104 | Server exposes experimental MCP capabilities |
| 22 | Poor documentation | LOW | CWE-1059 | Tools with missing or minimal descriptions |

---

## Walkthrough: Scanning DVMCP

### Prerequisites

```
agentsmith/
├── .venv/                    # Python virtual environment
├── mcp_server/               # Agent Smith MCP server
└── tests/
    └── test_targets/
        └── DVMCP/            # Damn Vulnerable MCP Server
```

```bash
# One-time setup
git clone https://github.com/harishsg993010/damn-vulnerable-MCP-server.git \
    tests/test_targets/DVMCP
pip install -r mcp_server/requirements.txt
```

### Step 1: Start Agent Smith

```bash
# Terminal 1 — Agent Smith MCP server
python3 -m mcp_server --no-auth
```

```
Agent Smith MCP Server starting on 0.0.0.0:2266
Transport: both
SSE endpoint: http://0.0.0.0:2266/sse
Streamable HTTP endpoint: http://0.0.0.0:2266/mcp
Tools available: 10
Auth: DISABLED
```

### Step 2: Start DVMCP Targets

```bash
# Terminal 2 — DVMCP challenge servers
./tests/test_dvmcp.sh --setup-only
```

```
Agent Smith — DVMCP Security Scan
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Challenge 1  (Basic Prompt Injection)     → port 9001
  Challenge 2  (Tool Poisoning)             → port 9002
  Challenge 3  (Excessive Permission Scope) → port 9003
  ...
  Challenge 10 (Multi-Vector Attack)        → port 9010
✓ DVMCP servers running. Press Ctrl+C to stop.
```

### Step 3: Scan Interactively

```bash
# Terminal 3 — Interactive REPL
python3 -m mcp_server.test_client interact
```

#### Example: Challenge 1 — Basic Prompt Injection (port 9001)

```
mcp> scan_mcp {"target_url": "http://localhost:9001/sse"}

  Risk Score:  HIGH
  Findings:    4
  Severity:    HIGH: 2, MEDIUM: 1, LOW: 1
  Tools:       1
  Resources:   1
  Prompts:     0
  Top findings:
    [HIGH] No authentication required
    [HIGH] Resource with sensitive name or URI (get_credentials)
    [MEDIUM] Unencrypted transport (HTTP)
    [LOW] No length limit on required string parameter (get_user_info)
  Exposed tools:
    > get_user_info(username)
```

**What the scanner found:**
- `internal://credentials` resource exposes system credentials (CWE-200)
- No authentication — anyone can connect and read them (CWE-306)

#### Example: Challenge 3 — Excessive Permission Scope (port 9003)

```
mcp> scan_mcp {"target_url": "http://localhost:9003/sse"}

  Risk Score:  CRITICAL
  Findings:    8
  Severity:    HIGH: 4, MEDIUM: 2, LOW: 2
  Top findings:
    [HIGH] No authentication required
    [HIGH] Dangerous capability: File System Write/Delete (file_manager)
    [HIGH] Dangerous capability: Excessive Permissions (file_manager)
    [HIGH] Tool has excessive permissions (delete, read, write) (file_manager)
    [MEDIUM] Unencrypted transport (HTTP)
    [MEDIUM] Unconstrained path traversal parameter (file_manager)
  Exposed tools:
    > file_manager(action, path)
```

**What the scanner found:**
- `file_manager` combines read + write + delete in a single tool (CWE-250)
- `path` parameter has no constraints — full path traversal possible (CWE-22)
- No auth on a tool that can delete arbitrary files (CWE-306)

#### Example: Challenge 7 — Token Theft (port 9007)

```
mcp> scan_mcp {"target_url": "http://localhost:9007/sse"}

  Risk Score:  CRITICAL
  Findings:    9
  Severity:    HIGH: 5, MEDIUM: 1, LOW: 3
  Top findings:
    [HIGH] No authentication required
    [HIGH] Dangerous capability: Authentication/Authorization Control (authenticate)
    [HIGH] Tool accepts credentials via parameter 'password' (authenticate)
    [HIGH] Dangerous capability: Authentication/Authorization Control (verify_token)
    [HIGH] Tool accepts credentials via parameter 'token' (verify_token)
  Exposed tools:
    > authenticate(username, password)
    > verify_token(token)
```

**What the scanner found:**
- Passwords transmitted as plain tool parameters (CWE-522)
- Tokens accepted as tool arguments — visible in logs/transport (CWE-522)
- Auth tools exposed on an unauthenticated server (CWE-306 + CWE-287)

#### Example: Challenge 8 — Malicious Code Execution (port 9008)

```
mcp> scan_mcp {"target_url": "http://localhost:9008/sse"}

  Risk Score:  CRITICAL
  Findings:    7
  Severity:    CRITICAL: 1, HIGH: 1, MEDIUM: 2, LOW: 3
  Top findings:
    [CRITICAL] Dangerous capability: Command/Code Execution (evaluate_expression)
    [HIGH] No authentication required
    [MEDIUM] Unencrypted transport (HTTP)
    [MEDIUM] Unconstrained injection parameter (evaluate_expression)
  Exposed tools:
    > evaluate_expression(expression)
    > generate_code_example(language, task)
```

**What the scanner found:**
- `evaluate_expression` → CRITICAL code execution risk (CWE-78)
- `expression` parameter accepts arbitrary input with no validation (CWE-74)
- Server uses `eval()` internally — any Python code can be executed

### Step 4: Automated Sweep

Scan all 10 challenges at once:

```bash
./tests/test_dvmcp.sh
```

Or scan specific ones:

```bash
./tests/test_dvmcp.sh 1 3 7 8 9
```

The script starts the DVMCP servers, scans each one, prints findings, and
cleans up automatically.

---

## DVMCP Challenge Coverage

| Challenge | Port | Vulnerability | Scanner Detection |
|-----------|------|--------------|-------------------|
| 1. Prompt Injection | 9001 | Sensitive credentials in resources | `sensitive_resource` (CWE-200) |
| 2. Tool Poisoning | 9002 | `execute_command` with shell=True | `command_execution` (CWE-78), `file_read` (CWE-22) |
| 3. Excessive Permissions | 9003 | `file_manager` with read/write/delete | `excessive_permissions` (CWE-250), `file_write` (CWE-73) |
| 4. Rug Pull Attack | 9004 | Tool behavior changes after N calls | `weak_validation` (CWE-20) |
| 5. Tool Shadowing | 9005 | Tool name conflicts | Enumerated for manual review |
| 6. Indirect Prompt Injection | 9006 | Injection via data sources | `injection_vector` (CWE-74) |
| 7. Token Theft | 9007 | Passwords/tokens as parameters | `credential_exposure` (CWE-522), `auth_control` (CWE-287) |
| 8. Code Execution | 9008 | `eval()` on user input | `command_execution` (CWE-78), `injection` (CWE-74) |
| 9. Remote Access | 9009 | Command injection via `remote_access` | `injection_vector` (CWE-74), `auth_control` (CWE-287) |
| 10. Multi-Vector | 9010 | Chained vulnerabilities | Multiple categories detected |

---

## Output Format

`scan_mcp` returns a JSON report:

```json
{
  "target": "http://localhost:9008/sse",
  "transport": "sse",
  "server_info": {
    "capabilities": { "tools": true },
    "health": { "status": "ok" }
  },
  "tools": [
    {
      "name": "evaluate_expression",
      "description": "Evaluate a mathematical expression...",
      "parameters": ["expression"]
    }
  ],
  "resources": [],
  "prompts": [],
  "findings": [
    {
      "severity": "CRITICAL",
      "category": "dangerous_capability",
      "title": "Dangerous capability: Command/Code Execution",
      "detail": "Tool 'evaluate_expression' appears to provide command/code execution...",
      "tool": "evaluate_expression",
      "cwe": "CWE-78",
      "recommendation": "Ensure 'evaluate_expression' has strict access controls..."
    }
  ],
  "summary": {
    "total_tools": 2,
    "total_resources": 0,
    "total_prompts": 0,
    "total_findings": 7,
    "by_severity": { "CRITICAL": 1, "HIGH": 1, "MEDIUM": 2, "LOW": 3 },
    "risk_score": "CRITICAL"
  }
}
```

---

## Risk Score Calculation

```
Score = SUM(finding_weights)

  CRITICAL  →  10 points each
  HIGH      →   5 points each
  MEDIUM    →   2 points each
  LOW       →   1 point each
  INFO      →   0 points

Rating:
  ≥ 20  →  CRITICAL
  ≥ 10  →  HIGH
  ≥  5  →  MEDIUM
  ≥  1  →  LOW
     0  →  CLEAN
```

---

## Scanning Your Own MCP Servers

Point `scan_mcp` at any MCP server:

```
mcp> scan_mcp {"target_url": "http://localhost:3000/sse"}
mcp> scan_mcp {"target_url": "https://mcp.example.com/mcp/", "transport": "http"}
mcp> scan_mcp {"target_url": "https://mcp.example.com/sse", "auth_token": "your-token"}
```

### Self-Scan (Audit Your Own Server)

```
mcp> scan_mcp {"target_url": "http://localhost:2266/sse"}
```

Agent Smith can scan itself — useful for verifying your own security posture.

### CI/CD Integration

```bash
# In your CI pipeline
python3 -m mcp_server.test_client interact <<EOF
scan_mcp {"target_url": "$MCP_SERVER_URL"}
last
quit
EOF
```

Use `last` to get the full JSON output for programmatic processing.

---

## Limitations & Future Work

**Current limitations:**
- Static analysis only — does not call tools or test for actual exploitation
- Cannot detect runtime behavior changes (e.g., rug pull attacks after N calls)
- Tool poisoning detection relies on keyword patterns, not semantic analysis
- Resource content is not inspected (only URI and metadata)

**Planned enhancements:**
- Active probing mode (safe, non-destructive tool calls to verify findings)
- AI-powered description analysis for subtle tool poisoning
- Differential scanning (detect tool definition changes over time)
- SARIF output format for IDE integration
- Integration with [agentgateway](https://github.com/agentgateway/agentgateway) for runtime traffic analysis
