---
name: agentsmith-extend-rules
description: >-
  Add new static analysis rules to Agent Smith's rule engine. Use when
  creating detection rules, adding regex patterns for vulnerabilities,
  or extending the static scanner.
---

# Extend Agent Smith Rules

## When to Use

User wants to add new static analysis detection rules.

## Rule File Locations

```
rules/
├── rules_core.json           # Core vulnerability patterns
├── rules_secrets.json        # Secret/credential detection
├── rules_infra.json          # Infrastructure misconfigs
├── rules_cicd.json           # CI/CD pipeline risks
├── rules_supplychain.json    # Supply chain patterns
├── rules_node.json           # Node.js specific
└── rules_python.json         # Python specific
```

## Rule Format

Each rule in the JSON array:

```json
{
  "id": "CATEGORY-NNN",
  "title": "Short finding title",
  "description": "Detailed explanation of the risk",
  "severity": "CRITICAL|HIGH|MEDIUM|LOW",
  "pattern": "regex_pattern_here",
  "file_pattern": "*.py",
  "tags": ["owasp", "injection", "cwe-89"],
  "cwe": "CWE-89",
  "fix": "How to remediate this issue"
}
```

### Field Reference

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | Unique ID: `CORE-001`, `SEC-001`, `NODE-001`, etc. |
| `title` | Yes | Short title shown in findings |
| `description` | Yes | Full explanation of the vulnerability |
| `severity` | Yes | CRITICAL / HIGH / MEDIUM / LOW |
| `pattern` | Yes | Regex pattern (Go syntax) to match |
| `file_pattern` | Yes | Glob for which files to scan (`*.py`, `*.java`, `*`) |
| `tags` | No | Array of tags for filtering |
| `cwe` | No | CWE identifier |
| `fix` | No | Remediation guidance |

## Adding a Rule

1. Choose the right rule file based on category
2. Add the rule object to the JSON array
3. Validate: `python3 scripts/validate_rules.py`
4. Test: `python3 agentsmith.py static /path/to/test-code --severity LOW`

## Pattern Tips

- Patterns use Go regex syntax (RE2)
- Use `(?i)` for case-insensitive
- Use `\b` for word boundaries
- Escape special chars: `\.`, `\(`, `\{`
- Test patterns at regex101.com (select Go flavor)

## Example: Add a new secret detection rule

In `rules/rules_secrets.json`:

```json
{
  "id": "SEC-050",
  "title": "Hardcoded Slack webhook URL",
  "description": "Slack webhook URL found in source code. These can be used to send messages to Slack channels.",
  "severity": "HIGH",
  "pattern": "hooks\\.slack\\.com/services/T[A-Z0-9]+/B[A-Z0-9]+/[a-zA-Z0-9]+",
  "file_pattern": "*",
  "tags": ["secrets", "slack", "webhook"],
  "cwe": "CWE-798",
  "fix": "Move Slack webhook URLs to environment variables or a secrets manager."
}
```

## Go Rule Source

Rules are also defined in `rules.go` (Go source of truth). If modifying Go rules, regenerate JSON with:

```bash
go run gen_rule_json.go
```
