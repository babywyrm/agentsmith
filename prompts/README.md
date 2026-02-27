# Agent Smith Prompts

**Last updated:** 2025-02  
**Schema version:** 1.0

## Overview

This directory contains AI prompt templates for security analysis. Prompts are modular: a **base** provides the core methodology and output schema, and **profile sections** add domain-specific guidance.

## Structure

```
prompts/
├── README.md                 # This file — maintenance guide
├── base/
│   ├── system_preamble.txt   # Core role, methodology, reasoning requirements
│   └── output_schema.txt     # Canonical JSON schema for findings
├── profiles/                 # Profile-specific sections (appended to base)
│   ├── owasp_sections.txt
│   ├── springboot_sections.txt
│   └── ...
└── *_profile.txt             # Legacy full templates (still supported)
```

## Maintenance: Keeping Prompts Current

Prompts can drift from reality. Update them when:

| Trigger | Action |
|---------|--------|
| **OWASP Top 10** changes (typically every 3–4 years) | Update `owasp_sections.txt` and `owasp_profile.txt` |
| **PCI-DSS** version bump | Update `pci_profile.txt` with new requirement numbers |
| **New CWE** or CVSS changes | Update schema examples in `base/output_schema.txt` |
| **Framework releases** (Spring Boot, Flask, etc.) | Update framework profiles with new APIs/patterns |
| **False positives** in production | Add clarification or negative examples to the base |

### Reference Standards (check periodically)

- [OWASP Top 10](https://owasp.org/Top10/) — current: 2021
- [CWE Top 25](https://cwe.mitre.org/top25/) — Most Dangerous Software Weaknesses
- [PCI-DSS v4.0](https://www.pcisecuritystandards.org/) — Payment card data
- [SOC 2 TSC](https://www.aicpa.org/soc2) — Trust Service Criteria

## Placeholders

All prompts support these placeholders (filled by the orchestrator):

| Placeholder | Description |
|-------------|-------------|
| `{file_path}` | Path to the file being analyzed |
| `{language}` | Detected language (python, java, go, etc.) |
| `{app_context}` | Tech stack, frameworks, architecture summary |
| `{code}` | File contents (or chunk) to analyze |

## Adding a New Profile

1. Add metadata to `lib/profile_metadata.py` (PrioritizationHints, etc.)
2. Create `prompts/profiles/<name>_sections.txt` with profile-specific checklist
3. Or create `prompts/<name>_profile.txt` for a full standalone template
4. Update `--list-profiles` output and docs

## Schema Evolution

When changing the output schema:

1. Update `base/output_schema.txt`
2. Ensure all profile sections reference the same finding structure
3. Update `normalize_finding()` in the orchestrator if new fields are added
4. Bump the schema version in this README
