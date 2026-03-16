---
name: agentsmith-interpret
description: >-
  Interpret and triage Agent Smith scan findings. Use when reading
  scan results, understanding severity ratings, or deciding what
  to fix first.
---

# Interpret Agent Smith Findings

## When to Use

User has scan results and needs help understanding or triaging them.

## Finding Structure

Every finding has:
- **severity**: CRITICAL / HIGH / MEDIUM / LOW / INFO
- **title**: short description
- **file**: source file path
- **line**: line number (if available)
- **description**: detailed explanation
- **cwe**: CWE ID (if applicable)
- **rule_id**: static scanner rule that triggered
- **payload**: exploit payload (if `--generate-payloads`)
- **annotation**: inline code annotation (if `--annotate-code`)

## Severity Guide

| Severity | What it means | Action |
|----------|--------------|--------|
| CRITICAL | Actively exploitable, high impact | Fix immediately |
| HIGH | Exploitable with some conditions | Fix before release |
| MEDIUM | Potential risk, needs context | Review and assess |
| LOW | Minor concern, defense-in-depth | Fix when convenient |
| INFO | Informational, no direct risk | Note for awareness |

## Triage Priority

1. **CRITICAL + has payload** → verified exploitable, fix first
2. **CRITICAL without payload** → likely exploitable, validate manually
3. **HIGH + in auth/payment code** → business-critical path
4. **Attack chains** (shown with `--show-chains`) → multi-step exploits
5. **HIGH in library/utility code** → lower priority unless widely used
6. **MEDIUM** → batch fix during regular development

## Reading Attack Chains

When `--show-chains` is used, taint flows show data paths:

```
Source: user_input (line 42, api/handler.py)
  → sink: db.execute(query) (line 67, db/queries.py)
  → Impact: SQL Injection
```

This means user-controlled data reaches a dangerous function without sanitization.

## Viewing Results

### CLI output
Findings print to console with Rich formatting.

### MCP shell (after scan)
```
mcp> summary          # severity counts + cost
mcp> findings 20      # top 20 findings
mcp> annotations      # annotated source files
mcp> payloads         # exploit payloads
mcp> everything       # all of the above
```

### File output
```bash
--output-dir ./reports    # JSON, CSV, Markdown, HTML in reports/
```

## Common Questions

**"Too many findings"** → Use `--severity HIGH` to filter, or `--top 5` for payloads on the worst ones only.

**"Are these false positives?"** → Static findings (rule_id present) have ~20% FP rate. AI findings are more precise. Cross-reference both.

**"Which findings matter most?"** → Look for CRITICAL + payload, or any finding in auth, payment, or data handling code.
