# SCRYNET Quick Start Guide

Get started with SCRYNET in 30 seconds using smart presets!

## 🚀 One-Command Scanning

### CTF Challenges (Fastest Path to Flag)
```bash
export CLAUDE_API_KEY="your-key"
python3 scrynet.py hybrid <ctf-challenge> ./scanner --preset ctf -v
```

**What you get:**
- AI prioritizes top 15 most vulnerable files
- CTF + OWASP profiles for maximum coverage
- Payloads generated for top 5 findings
- Code annotations showing exploits
- HTML + JSON + Markdown reports
- Auto-deduplication of similar findings

### Quick Security Check (CI/CD)
```bash
python3 scrynet.py hybrid <repo> ./scanner --preset quick
```

**What you get:**
- Fast scan (top 10 files only)
- OWASP profile focused on real threats
- JSON output for automation
- Parallel execution for speed

### Comprehensive Audit
```bash
python3 scrynet.py hybrid <repo> ./scanner --preset security-audit -v
```

**What you get:**
- Scans ALL files (no prioritization)
- OWASP + Code Review profiles
- Payloads + annotations for top 10
- All export formats (JSON, CSV, HTML, MD)

### Penetration Testing
```bash
python3 scrynet.py hybrid <target> ./scanner --preset pentest -v
```

**What you get:**
- Attack chain analysis
- Threat modeling included
- 3 profiles: CTF + OWASP + Attacker
- Comprehensive payload generation

## 📋 All Available Presets

| Preset | Files | Profiles | Payloads | Annotations | Use Case |
|--------|-------|----------|----------|-------------|----------|
| `quick` | 10 (prioritized) | owasp | No | No | CI/CD, fast checks |
| `ctf-fast` | 8 (prioritized) | ctf | Yes | No | Quick CTF recon |
| `ctf` | 15 (prioritized) | ctf, owasp | Yes | Yes | Full CTF analysis |
| `security-audit` | All files | owasp, code_review | Yes | Yes | Comprehensive review |
| `pentest` | 20 (prioritized) | ctf, owasp, attacker | Yes | Yes | Pentest + threat model |
| `compliance` | 25 (prioritized) | owasp, soc2, compliance | No | Yes | Regulatory compliance |

## 💡 Smart Defaults (Auto-Enabled)

SCRYNET automatically optimizes your scan:

✅ **Large repo** (>50 files)? → Auto-prioritizes
✅ **Multiple profiles**? → Auto-deduplicates
✅ **Payloads/annotations**? → Adds HTML export
✅ **Framework detected**? → Passes context to AI

Disable with `--no-smart-defaults` if you want full manual control.

## 🎯 Before & After

### Old Way (Complex)
```bash
python3 scrynet.py hybrid ~/ctf ./scanner \
  --profile ctf,owasp \
  --prioritize --prioritize-top 15 \
  --question "find exploitable vulns" \
  --deduplicate --dedupe-threshold 0.7 --dedupe-strategy keep_highest_severity \
  --generate-payloads --annotate-code --top-n 5 \
  --export-format json html markdown \
  --output-dir ./reports \
  --verbose
# 13 flags! 😰
```

### New Way (Simple)
```bash
python3 scrynet.py hybrid ~/ctf ./scanner --preset ctf -v
# 2 flags! 🎉
```

## 🧠 Enhanced Analysis

With enhanced prompts, you now get:

**Before:**
```
Finding: SQL injection at line 45
Severity: HIGH
Fix: Use parameterized queries
```

**After:**
```
Finding: SQL Injection in User Search Endpoint
Severity: CRITICAL
Exploitability: 9/10 (Trivial - single HTTP request)
Line: 45

Data Flow:
  HTTP GET /search?q=<input> 
  → request.args['q'] 
  → search_users(query) 
  → f"SELECT * FROM users WHERE name = '{query}'"
  → cursor.execute() ← SINK (no parameterization)

Attack Scenario:
  1. Send: /search?q=' OR '1'='1
  2. Query becomes: SELECT * FROM users WHERE name = '' OR '1'='1'
  3. Returns all users → authentication bypass

Impact: CRITICAL
  - 10,000 user records at risk
  - Enables account takeover
  - GDPR fines up to 4% annual revenue
  - Class-action lawsuit risk

Defenses: None detected
  - No input validation
  - No parameterized queries
  - No WAF rules

Fix: cursor.execute('SELECT * FROM users WHERE name = ?', (query,))

Time to Exploit: < 1 minute
Confidence: VERY HIGH
```

## 📚 Next Steps

1. **List available presets**: `python3 orchestrator.py --list-presets`
2. **List available profiles**: `python3 orchestrator.py --list-profiles`
3. **Run a quick test**: `python3 scrynet.py static <target> --severity HIGH`
4. **Full scan**: `python3 scrynet.py hybrid <target> ./scanner --preset ctf -v`

## 💰 Cost Estimation

```bash
# See estimated cost before running
python3 orchestrator.py <target> ./scanner --preset ctf --estimate-cost
```

## 🎉 You're Ready!

Start with a preset, the rest is automatic. SCRYNET handles:
- File prioritization
- Deduplication
- Smart output formats
- Framework detection
- Exploitability analysis

Happy hunting! 🏴‍☠️

