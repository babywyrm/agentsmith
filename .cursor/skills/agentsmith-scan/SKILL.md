---
name: agentsmith-scan
description: >-
  Run Agent Smith security scans with the right mode, preset, and flags.
  Use when scanning code for vulnerabilities, running security audits,
  or when the user mentions agentsmith, security scan, or vulnerability analysis.
---

# Agent Smith Scan Runner

## When to Use

User wants to scan code for security vulnerabilities using Agent Smith.

## Prerequisites

```bash
cd ~/agentsmith
./scripts/setup.sh && source scripts/activate.sh
export CLAUDE_API_KEY="sk-ant-..."  # required for AI modes (hybrid, analyze, ctf)
```

## Modes

| Mode | Command | What it does | Needs API key |
|------|---------|-------------|---------------|
| **static** | `python3 agentsmith.py static .` | Go regex scanner, fast, free | No |
| **analyze** | `python3 agentsmith.py analyze . "question"` | AI-only deep analysis | Yes |
| **ctf** | `python3 agentsmith.py ctf . "find vulns"` | CTF-optimized AI analysis | Yes |
| **hybrid** | `python3 agentsmith.py hybrid . ./scanner` | Static + AI combined | Yes |

**hybrid** is the recommended mode for most use cases.

## Presets (hybrid mode)

| Preset | Files | Time | Cost | Use case |
|--------|-------|------|------|----------|
| `mcp` | 2 | ~1 min | ~$0.01 | MCP/Cursor integration, quick check |
| `quick` | 10 | ~1 min | ~$0.02 | CI/CD gates, pre-commit |
| `ctf-fast` | 8 | ~2 min | ~$0.03 | CTF quick recon |
| `ctf` | 15 | ~3-5 min | ~$0.10 | Full CTF analysis with chains |
| `security-audit` | ALL | ~10-20 min | ~$0.30 | Production security audit |
| `pentest` | 20 | ~5-10 min | ~$0.25 | Penetration test prep |

## Common Patterns

### Quick static scan (no API key)
```bash
python3 agentsmith.py static /path/to/repo --severity HIGH
```

### Hybrid scan with preset
```bash
python3 agentsmith.py hybrid /path/to/repo ./scanner --preset quick
```

### Targeted vulnerability hunt
```bash
python3 agentsmith.py hybrid /path/to/repo ./scanner --profile ctf,owasp \
  --question "find SQL injection in database queries" \
  --prioritize --prioritize-top 8 --generate-payloads --top-n 5
```

### Production security audit
```bash
python3 agentsmith.py hybrid /path/to/repo ./scanner \
  --profile owasp --prioritize --prioritize-top 30 \
  --generate-payloads --annotate-code --output-dir ./reports
```

### Framework-specific scan
```bash
# Spring Boot
python3 agentsmith.py hybrid ./app ./scanner --profile springboot,owasp --prioritize

# Flask
python3 agentsmith.py hybrid ./app ./scanner --profile flask,owasp --prioritize

# C++ / Conan
python3 agentsmith.py hybrid ./app ./scanner --profile cpp_conan --prioritize
```

### CI/CD gate
```bash
python3 agentsmith.py hybrid ./src ./scanner --profile owasp --prioritize \
  --prioritize-top 10 --severity HIGH --output-dir ./reports
```

**Note:** `--preset` is available in the MCP shell (`mcp> scan_hybrid preset=quick`),
not on the CLI. On the CLI, set profile/prioritize/flags directly.

## Key Flags

| Flag | What it does |
|------|-------------|
| `--preset NAME` | Apply a preset configuration |
| `--profile NAME` | AI analysis profile(s), comma-separated |
| `--question "..."` | Focus the AI on specific vulnerability types |
| `--top N` | Number of findings to get payloads/annotations for |
| `--prioritize` | Use AI to select the most interesting files first |
| `--prioritize-top N` | Number of files for AI to analyze |
| `--generate-payloads` | Generate exploit payloads for top findings |
| `--annotate-code` | Add inline annotations to source code |
| `--show-chains` | Enable cross-file taint tracking |
| `--severity HIGH` | Filter findings by minimum severity |
| `--output-dir DIR` | Write reports to directory |
| `--detect-tech-stack` | Auto-detect frameworks and suggest profiles |

## After Scanning

```bash
# Via MCP shell
./scripts/run_mcp_shell.sh
mcp> summary
mcp> findings 20
mcp> annotations
mcp> payloads
```

## Choosing the Right Approach

1. **First time on a codebase?** → `--detect-tech-stack` then `--preset quick`
2. **CTF challenge?** → `--preset ctf --show-chains`
3. **Need it fast and free?** → `static` mode
4. **Production audit?** → `--preset security-audit`
5. **Specific vuln type?** → `--question "find XSS" --preset ctf`
