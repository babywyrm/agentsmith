---
name: agentsmith-ctf
description: >-
  Run Agent Smith in CTF mode for Capture The Flag challenges. Use when
  doing CTF, finding flags, hunting exploitable vulnerabilities, or
  analyzing challenge code for quick wins.
---

# Agent Smith CTF Mode

## When to Use

User is working on a CTF challenge and needs to find vulnerabilities fast.

## Quick Start

```bash
# Fast recon (8 files, ~2 min, ~$0.03)
python3 agentsmith.py hybrid ./challenge ./scanner --preset ctf-fast

# Full CTF analysis with attack chains (15 files, ~5 min, ~$0.10)
python3 agentsmith.py hybrid ./challenge ./scanner --preset ctf --show-chains

# Targeted hunt
python3 agentsmith.py hybrid ./challenge ./scanner --preset ctf \
  --question "find SQL injection and command injection" \
  --show-chains --generate-payloads --top 5
```

## CTF Presets

| Preset | Files | Payloads | Chains | Use when |
|--------|-------|----------|--------|----------|
| `ctf-fast` | 8 | No | No | First look, time pressure |
| `ctf` | 15 | Yes | Yes | Full analysis, want exploits |

## CTF-Specific Features

### Attack chains (`--show-chains`)
Traces data flow from user input to dangerous sinks across files.
Shows the complete exploitation path, not just individual findings.

### Payloads (`--generate-payloads`)
Generates working exploit payloads for top findings.
Includes: injection strings, bypass techniques, flag extraction commands.

### Focused questions
Direct the AI at specific vulnerability classes:

```bash
--question "find deserialization vulnerabilities"
--question "find SSTI and template injection"
--question "find authentication bypass"
--question "find file upload vulnerabilities"
--question "find command injection in user input handlers"
```

## CTF Workflow

1. **Recon**: `--preset ctf-fast` to get a quick overview
2. **Focus**: Read findings, identify promising attack surface
3. **Deep dive**: `--preset ctf --question "focus area" --show-chains --generate-payloads`
4. **Exploit**: Use generated payloads, check chain paths
5. **Iterate**: Narrow question based on what you learned

## Via MCP Shell

```
mcp> scan_hybrid preset=ctf-fast
mcp> summary
mcp> findings 10
mcp> scan_hybrid preset=ctf question="find the flag" generate_payloads=true
mcp> payloads
```

## CTF vs Hybrid Mode

Use `ctf` subcommand for standalone AI analysis (no static scanner):

```bash
python3 agentsmith.py ctf ./challenge "find all vulnerabilities and flags" \
  --top-n 10 --generate-payloads
```

Use `hybrid --preset ctf` for static + AI combined (more thorough):

```bash
python3 agentsmith.py hybrid ./challenge ./scanner --preset ctf --show-chains
```

Hybrid is better when you have time. CTF subcommand is faster when you don't.
