# Agent Smith — Roadmap & Stretch Goals

A consolidated view of improvement opportunities across the tool. Prioritized by impact and effort.

---

## Summary: What's Done

| Area | Status |
|------|--------|
| Static → Prioritization | Done (PromptFactory uses static_findings) |
| Node/Mongoose/Modern rules | Done (Prisma, React, Go, Ruby, Java, Python) |
| MCP shell (repo, findings source) | Done (scan_static persists, output_dir shown) |
| Rules validation | Done (scripts/validate_rules.py) |
| Rules changelog | Done |
| Tech-stack-aware rules | Done (rules_node/rules_python loaded when detected) |
| SARIF export | Done (--output sarif) |
| Whitelist/ignore | Done (.scannerignore, --ignore-rules) |
| Pre-commit example | Done (examples/pre-commit-hook.sh) |
| Context/cache | Done (git fingerprint, --cache-in-repo) |
| CI-friendly exit codes | Done (--fail-on HIGH/CRITICAL) |
| CTF prioritization + static | Done (CTFPromptFactory accepts static_findings) |
| Example CI config | Done (examples/ci-gate.yml) |
| DVMCP test suite | Done (test_dvmcp.sh, dvmcp shell command) |
| Differential MCP scanning | Done (mcp_attack --baseline, --save-baseline) |

---

## Tier 1 — Quick Wins (Low effort, high impact)

| Item | Description |
|------|-------------|
| **SARIF for scan_mcp** | Export scan_mcp findings as SARIF for IDE/CI (VS Code, GitHub Code Scanning) |
| **DVMCP scoreboard** | Auto-run all 10 DVMCP challenges, JSON scoreboard output for CI/regression |
| **Narrow SSRF rules** | Current rules flag every `axios.get()` / `http.Get()` — narrow to dynamic URLs to reduce false positives |
| **Orchestrator + MCP cache** | Wire API cache into hybrid/scan_hybrid for faster repeat runs (analyze/ctf already have it) |

---

## Tier 2 — Medium Effort, High Value

| Item | Description |
|------|-------------|
| **Batch scan_mcp** | `scan_mcp url1 url2` or `scan_mcp_batch urls.txt` — scan multiple MCP servers in one run |
| **More MCP auth types** | Support API key header, X-API-Key, OAuth flow hints beyond Bearer token |
| **Resource content sampling** | Optional: fetch resource content for sensitive URIs, flag exposed secrets/keys |
| **Prompt-injection patterns** | Add heuristics for "ignore previous instructions", "disregard", etc. in tool descriptions |
| **Schema drift detection** | Compare tool params across scans; flag new required params, removed params, type changes |

---

## Tier 3 — Larger Investments

| Item | Description |
|------|-------------|
| **Context-aware rules** | Source + sink rules (e.g., `req.body` → `findByIdAndUpdate`). Needs multi-line or AST analysis (Semgrep-style) |
| **AI-powered MCP analysis** | Use Claude to detect subtle tool poisoning, hidden instructions, misleading descriptions |
| **Active probing mode** | Safe, non-destructive tool calls (e.g., read-only with sandboxed args) to verify findings |
| **Attack chain profiling** | AI-driven synthesis of findings + taint flows into coherent attack paths. Multi-step chains (XSS → session theft → admin). See `lib/taint_tracker.py`, `lib/flow_visualizer.py`, `orchestrator.run_attack_chain_analysis()` |
| **Docker image** | Official `agentsmith-mcp` image for easy deployment |
| **Metrics endpoint** | Prometheus `/metrics` for request counts, scan latency, tool usage |
| **agentgateway integration** | Use [agentgateway](https://github.com/agentgateway/agentgateway) for runtime traffic analysis |

---

## Tier 4 — Research & Exploration

- Runtime behavior detection (rug-pull style attacks)
- WebSocket transport when MCP spec stabilizes
- CVE / advisory check for MCP-related vulnerabilities
- Property-based tests / fuzz scan_mcp heuristics

---

## Ideas Backlog

- Rate limiting per client on MCP server
- Request/response audit logging (opt-in, for compliance)
- VSCode extension for deeper Cursor integration
- Terraform/Pulumi module for cloud deployment
- Slack/Teams webhook on critical findings

---

## Recommended Next Steps

1. **Narrow Axios/Go SSRF rules** — Reduce false positives on static URLs
2. **Orchestrator + MCP cache** — Wire API cache into hybrid/scan_hybrid
3. **SARIF for scan_mcp** — IDE/CI integration for MCP scan results
4. **DVMCP scoreboard** — Regression testing for MCP scanner

---

## References

- [STATIC_SCANNER_STRATEGY](STATIC_SCANNER_STRATEGY.md)
- [rules/CHANGELOG](../rules/CHANGELOG.md)
- [mcp_attack/CHANGELOG](../mcp_attack/CHANGELOG.md)
