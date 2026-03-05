# mcp_attack Changelog

All notable changes to this submodule are documented here.

## [Unreleased] - 2026-03

### Added

- **Behavioral probe engine** — 9 new checks that actively call tools and analyze responses, moving beyond static metadata analysis:
  - `check_tool_response_injection` — Calls each tool with safe inputs, scans responses for injection payloads, hidden instructions, exfiltration URLs, invisible Unicode, and base64-encoded attacks
  - `check_input_sanitization` — Sends context-aware probes (path traversal, command injection, template injection, SQL injection) and detects unsanitized reflection. Uses a canary string (`MCP_PROBE_8f4c2a`) to confirm reflection.
  - `check_error_leakage` — Sends empty, wrong-type, and prototype-pollution inputs; checks for stack traces, internal paths, connection strings, secrets in error responses
  - `check_temporal_consistency` — Calls the same tool 3x with identical input; detects escalating injection, wildly inconsistent responses, or new threats appearing in later calls
  - `check_resource_poisoning` — Deep resource content analysis: base64-encoded injection payloads, data URIs, steganographic invisible Unicode, CSS-hidden HTML, markdown image exfiltration
  - `check_cross_tool_manipulation` — Detects when a tool's output contains instructions directing the LLM to invoke other tools (cross-tool orchestration attacks)
  - `check_deep_rug_pull` — Snapshots tools → invokes each tool multiple times → re-snapshots. Catches rug pulls that only trigger after N tool invocations (e.g. DVMCP challenge 4), including schema mutations
  - `check_state_mutation` — Snapshots resource contents before and after tool invocations; detects silent server state changes, new/disappeared resources
  - `check_notification_abuse` — Monitors SSE message queue for unsolicited `sampling/createMessage`, `roots/list`, or other server-initiated requests that abuse MCP's bidirectional protocol

- **Probe payload library** (`patterns/probes.py`)
  - Canary string system for detecting unsanitized reflection
  - Context-aware safe argument generation from tool schemas
  - Injection probe sets: path traversal (4), command injection (5), template injection (5), SQL injection (3)
  - Response analysis patterns: injection (12), exfiltration (3), cross-tool (3), hidden content (5), error leakage (9)
  - Steganographic Unicode detection (zero-width, bidi, invisible formatters)
  - CSS-hidden HTML and markdown image exfiltration detection

- **Attack chain patterns** — 10 new behavioral chain combinations:
  - `tool_response_injection → cross_tool_manipulation`
  - `tool_response_injection → token_theft`
  - `deep_rug_pull → tool_poisoning`
  - `deep_rug_pull → tool_response_injection`
  - `input_sanitization → code_execution`
  - `resource_poisoning → tool_response_injection`
  - `state_mutation → deep_rug_pull`
  - `notification_abuse → token_theft`
  - `cross_tool_manipulation → code_execution`
  - `cross_tool_manipulation → token_theft`

- **Check execution ordering** — `run_all_checks()` now runs in deliberate phases: static → behavioral → deep probes → transport → aggregate. Aggregate checks (multi_vector, attack_chains) run last so they see all prior findings.

### Changed

- `checks/__init__.py` — Reorganized check execution into clear phases with comments
- `checks/behavioral.py` — Refactored tool-list diffing into shared `_diff_tool_lists()` helper used by both shallow and deep rug pull checks

---

## [4.1] - 2026-02

### Added

- **Bearer token auth** — `--auth-token TOKEN` for authenticated MCP endpoints (JWT, PAT, etc.). Env var `MCP_AUTH_TOKEN` supported. Enables scanning GitHub MCP (`https://api.githubcopilot.com/mcp/`), internal services, etc.

- **Differential scanning**
  - `--baseline FILE` — Compare current scan to saved baseline
  - `--save-baseline FILE` — Save current scan as baseline for future comparison
  - Reports added/removed/modified tools, resources, prompts
  - New tools flagged as MEDIUM findings for security review
  - `mcp_attack/diff.py` — `load_baseline`, `save_baseline`, `diff_against_baseline`, `print_diff_report`

- **New security checks**
  - `check_rate_limit` — Flags tools that suggest unbounded or unthrottled usage (e.g. "unlimited requests", "no rate limit")
  - `check_prompt_leakage` — Flags tools that may echo, log, or expose user prompts or internal instructions
  - `check_supply_chain` — Flags tools that install packages from user-controlled or dynamic URLs (e.g. `curl | bash`, "user-provided URL")

- **New pattern sets**
  - `RATE_LIMIT_PATTERNS` — 5 patterns for rate-limit abuse
  - `PROMPT_LEAKAGE_PATTERNS` — 8 patterns for prompt exposure
  - `SUPPLY_CHAIN_PATTERNS` — 9 patterns for supply-chain risks

- **CLI options**
  - `--targets-file FILE` — Read target URLs from file (one per line, `#` comments ignored)
  - `--public-targets` — Use built-in list in `data/public_targets.txt` (DVMCP localhost URLs)

- **Data**
  - `data/public_targets.txt` — Built-in targets for DVMCP (localhost:9001–9005)

- **Test suite**
  - `tests/` — Pytest suite (38 tests) for checks, CLI, patterns, diff, and integration

### Changed

- `parse_args()` now accepts optional `args` for testability
- **Streamable HTTP support** — Scanner now handles MCP servers using Streamable HTTP (e.g. DeepWiki at `https://mcp.deepwiki.com/mcp`). Accepts `application/json` and `text/event-stream` responses; parses SSE-formatted POST responses.

---

## Planned

### Quick wins

- **DVMCP scoreboard** — Auto-run all 10 DVMCP challenges, report pass/fail per challenge, optional JSON output
- **Batch scan** — `scan_mcp url1 url2` or `scan_mcp_batch urls.txt` from main Agent Smith

### Medium effort

- ~~**Differential MCP scanning**~~ — ✓ Done. `--baseline` and `--save-baseline`
- ~~**Fuzzing / live probing**~~ — ✓ Done. Behavioral probe engine with safe tool invocation
- **AI-powered MCP description analysis** — Use Claude to detect subtle tool poisoning, hidden instructions, misleading descriptions
- **SARIF export** — Export findings as SARIF for IDE/CI (VS Code, GitHub Code Scanning)

### Larger investments

- **Docker image** — Official `agentsmith-mcp` image for easy deployment
- **Metrics endpoint** — Prometheus `/metrics` for request counts, scan latency, tool usage
- ~~**Attack chain profiling**~~ — ✓ Done. 17 attack chain patterns with aggregate detection
- **MCP registry** — Curated list of public MCP servers for periodic scanning
- **Active exploitation mode** — Controlled, opt-in exploit verification (beyond safe probing)
