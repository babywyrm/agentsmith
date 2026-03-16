---
name: agentsmith-profiles
description: >-
  Choose and combine AI analysis profiles for Agent Smith scans.
  Use when selecting profiles, combining multiple profiles, or
  understanding which profile fits a target codebase.
---

# Agent Smith Profile Selection

## When to Use

User needs to pick the right AI profile(s) for their target codebase.

## Available Profiles

| Profile | Best for | What it checks |
|---------|----------|---------------|
| `owasp` | Any web app | OWASP Top 10: injection, XSS, CSRF, auth, crypto, SSRF |
| `ctf` | CTF challenges | Exploitable vulns, flags, quick wins, attack chains |
| `springboot` | Java/Spring | SpEL injection, actuator exposure, bean manipulation, JDBC |
| `flask` | Python/Flask | SSTI (Jinja2), SQLAlchemy injection, debug mode, pickle |
| `cpp_conan` | C++/Conan | Buffer overflow, use-after-free, format string, supply chain |
| `pci` | Payment systems | PCI-DSS compliance: cardholder data, encryption, access control |
| `soc2` | SaaS/enterprise | SOC2: logging, access control, change management |
| `code_review` | General | Code quality, maintainability, best practices |

## Combining Profiles

Profiles can be combined with commas. The deduplication engine merges findings.

```bash
# Web app with OWASP + framework-specific checks
python3 agentsmith.py hybrid ./app ./scanner --profile owasp,flask

# CTF with OWASP coverage
python3 agentsmith.py hybrid ./challenge ./scanner --profile ctf,owasp

# Compliance + security
python3 agentsmith.py hybrid ./app ./scanner --profile pci,owasp
```

## Detect and Suggest

```bash
python3 agentsmith.py hybrid ./app --detect-tech-stack
```

Returns detected languages, frameworks, and suggests matching profiles.

## Profile vs Preset

- **Preset** = scanning configuration (how many files, what features)
- **Profile** = AI analysis focus (what vulnerabilities to look for)

Combine them: `--preset ctf --profile ctf,owasp`

## Quick Decision Tree

1. **Don't know the stack?** → `--detect-tech-stack`
2. **Web app?** → `owasp` + framework profile (`flask`, `springboot`)
3. **CTF?** → `ctf` (or `ctf,owasp` for broader coverage)
4. **C++ native code?** → `cpp_conan`
5. **Compliance?** → `pci` or `soc2` (+ `owasp` for security)
6. **Code review?** → `code_review,owasp`
