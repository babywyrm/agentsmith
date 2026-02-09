"""
MCP Tool Definitions and Handlers

Nine core tools that call into Agent Smith's scanning and analysis pipeline.
"""

import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Ensure project root is on the Python path so we can import lib/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mcp_server.config import (
    ALLOWED_PATHS,
    MAX_OUTPUT_FINDINGS,
    MAX_PATH_LENGTH,
    MAX_QUESTION_LENGTH,
    OUTPUT_DIR,
    RULES_DIR,
    SCANNER_BIN,
)

# Maximum file size for single-file operations (1 MB)
MAX_FILE_SIZE = 1_000_000
# Maximum code context to send to AI (100 KB)
MAX_CODE_CONTEXT = 100_000


# ---------------------------------------------------------------------------
# Input validation helpers
# ---------------------------------------------------------------------------

def _validate_path(repo_path: str) -> Path:
    """Validate and resolve a repo path, preventing traversal attacks."""
    if not repo_path or len(repo_path) > MAX_PATH_LENGTH:
        raise ValueError(f"repo_path must be 1-{MAX_PATH_LENGTH} characters")

    resolved = Path(repo_path).resolve()

    if not resolved.is_dir():
        raise ValueError(f"Path does not exist or is not a directory: {resolved}")

    # Check against allowed base paths
    allowed = any(
        resolved == base or resolved.is_relative_to(base)
        for base in ALLOWED_PATHS
    )
    if not allowed:
        raise ValueError(
            f"Path '{resolved}' is outside allowed directories. "
            f"Set AGENTSMITH_ALLOWED_PATHS to expand access."
        )

    return resolved


def _validate_severity(severity: str | None) -> str | None:
    """Validate severity parameter."""
    if severity is None:
        return None
    severity = severity.upper().strip()
    if severity not in {"CRITICAL", "HIGH", "MEDIUM", "LOW"}:
        raise ValueError(f"Invalid severity: {severity}. Must be CRITICAL, HIGH, MEDIUM, or LOW.")
    return severity


def _find_output_dir(output_dir: str | None = None) -> Path:
    """Find the output directory, defaulting to the most recent one."""
    if output_dir:
        p = Path(output_dir).resolve()
        if not p.is_dir():
            raise ValueError(f"Output directory not found: {p}")
        return p

    if not OUTPUT_DIR.is_dir():
        raise ValueError("No output/ directory found. Run a scan first.")

    dirs = sorted(
        [d for d in OUTPUT_DIR.iterdir() if d.is_dir()],
        key=lambda d: d.stat().st_mtime,
        reverse=True,
    )
    if not dirs:
        raise ValueError("No scan results found in output/. Run a scan first.")

    return dirs[0]


def _validate_file_path(file_path: str) -> Path:
    """Validate and resolve a single file path, preventing traversal attacks."""
    if not file_path or len(file_path) > MAX_PATH_LENGTH:
        raise ValueError(f"file_path must be 1-{MAX_PATH_LENGTH} characters")

    resolved = Path(file_path).resolve()

    if not resolved.is_file():
        raise ValueError(f"Path does not exist or is not a file: {resolved}")

    if resolved.stat().st_size > MAX_FILE_SIZE:
        raise ValueError(
            f"File too large ({resolved.stat().st_size} bytes). "
            f"Maximum is {MAX_FILE_SIZE} bytes."
        )

    # Check against allowed base paths
    allowed = any(
        resolved == base or resolved.is_relative_to(base)
        for base in ALLOWED_PATHS
    )
    if not allowed:
        raise ValueError(
            f"Path '{resolved}' is outside allowed directories. "
            f"Set AGENTSMITH_ALLOWED_PATHS to expand access."
        )

    return resolved


def _get_ai_client():
    """Get an AI client, raising a clear error if credentials are missing."""
    api_key = os.environ.get("CLAUDE_API_KEY")
    bedrock = os.environ.get("AGENTSMITH_PROVIDER", "").lower() == "bedrock"

    if not api_key and not bedrock:
        raise ValueError(
            "AI tools require CLAUDE_API_KEY or AGENTSMITH_PROVIDER=bedrock. "
            "Set the appropriate environment variable."
        )

    from lib.ai_provider import create_client
    return create_client()


def _count_by_key(items: list[dict], key: str, top_n: int | None = None) -> dict[str, int]:
    """Count occurrences of a field value across a list of dicts."""
    counts: dict[str, int] = {}
    for item in items:
        val = item.get(key, "unknown")
        counts[val] = counts.get(val, 0) + 1
    if top_n:
        counts = dict(sorted(counts.items(), key=lambda x: x[1], reverse=True)[:top_n])
    return counts


# ---------------------------------------------------------------------------
# Tool definitions (MCP schema)
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS = [
    {
        "name": "scan_static",
        "description": (
            "Run Agent Smith's static security scanner on a repository. "
            "Uses 70+ OWASP rules to find vulnerabilities without AI. "
            "Fast, free, and requires no API key."
        ),
        "input_schema": {
            "type": "object",
            "required": ["repo_path"],
            "properties": {
                "repo_path": {
                    "type": "string",
                    "description": "Absolute path to the repository to scan",
                },
                "severity": {
                    "type": "string",
                    "enum": ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
                    "description": "Minimum severity to report (default: all)",
                },
            },
        },
    },
    {
        "name": "scan_hybrid",
        "description": (
            "Run a full hybrid scan combining static analysis with AI-powered "
            "vulnerability detection. Requires CLAUDE_API_KEY or Bedrock credentials. "
            "Generates findings, payloads, annotations, and cost tracking."
        ),
        "input_schema": {
            "type": "object",
            "required": ["repo_path"],
            "properties": {
                "repo_path": {
                    "type": "string",
                    "description": "Absolute path to the repository to scan",
                },
                "profile": {
                    "type": "string",
                    "description": "AI analysis profile (default: owasp). Options: owasp, ctf, code_review, modern, attacker, soc2, pci, compliance, performance",
                    "default": "owasp",
                },
                "preset": {
                    "type": "string",
                    "enum": ["quick", "ctf", "ctf-fast", "security-audit", "pentest", "compliance"],
                    "description": "Use a preset configuration (overrides other options)",
                },
                "prioritize_top": {
                    "type": "integer",
                    "description": "Number of top files for AI to prioritize (default: 15)",
                    "default": 15,
                    "minimum": 1,
                    "maximum": 100,
                },
                "question": {
                    "type": "string",
                    "description": "Focus question for AI prioritization (e.g., 'find SQL injection vulnerabilities')",
                },
                "top_n": {
                    "type": "integer",
                    "description": "Number of top findings to generate payloads/annotations for (default: 5, max: 20)",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 20,
                },
            },
        },
    },
    {
        "name": "detect_tech_stack",
        "description": (
            "Detect the technology stack of a repository: languages, frameworks, "
            "entry points, security-critical files, and framework-specific risks."
        ),
        "input_schema": {
            "type": "object",
            "required": ["repo_path"],
            "properties": {
                "repo_path": {
                    "type": "string",
                    "description": "Absolute path to the repository to analyze",
                },
            },
        },
    },
    {
        "name": "summarize_results",
        "description": (
            "Get a summary of existing scan results: finding counts by severity, "
            "top rules, AI findings, cost breakdown, and tech stack info."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "output_dir": {
                    "type": "string",
                    "description": "Path to scan output directory (default: most recent in output/)",
                },
            },
        },
    },
    {
        "name": "list_findings",
        "description": (
            "List individual findings from a scan, optionally filtered by severity "
            "or source. Returns structured finding data."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "output_dir": {
                    "type": "string",
                    "description": "Path to scan output directory (default: most recent in output/)",
                },
                "severity": {
                    "type": "string",
                    "enum": ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
                    "description": "Filter by minimum severity",
                },
                "source": {
                    "type": "string",
                    "description": "Filter by source (e.g., 'agentsmith', 'claude-owasp')",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of findings to return (default: 50)",
                    "default": 50,
                    "minimum": 1,
                    "maximum": 500,
                },
            },
        },
    },
    {
        "name": "list_presets",
        "description": (
            "List all available scan preset configurations with their descriptions "
            "and settings. Presets are one-command configurations for common workflows."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "scan_file",
        "description": (
            "Scan a single file for security vulnerabilities using Agent Smith's "
            "static analysis rules. Fast and focused — ideal for checking the file "
            "you're currently editing. No API key required."
        ),
        "input_schema": {
            "type": "object",
            "required": ["file_path"],
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Absolute path to the file to scan",
                },
                "severity": {
                    "type": "string",
                    "enum": ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
                    "description": "Minimum severity to report (default: all)",
                },
            },
        },
    },
    {
        "name": "explain_finding",
        "description": (
            "Get a detailed AI-powered explanation of a security finding. "
            "Provides attack scenarios, real-world impact, CWE details, and "
            "educational context. Requires CLAUDE_API_KEY."
        ),
        "input_schema": {
            "type": "object",
            "required": ["file_path", "description"],
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Absolute path to the file containing the vulnerability",
                },
                "line_number": {
                    "type": "integer",
                    "description": "Line number of the vulnerability (optional but improves accuracy)",
                    "minimum": 1,
                },
                "description": {
                    "type": "string",
                    "description": "Description of the finding to explain (e.g., 'SQL injection in login query')",
                },
                "severity": {
                    "type": "string",
                    "enum": ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
                    "description": "Severity of the finding",
                },
                "cwe": {
                    "type": "string",
                    "description": "CWE identifier if known (e.g., 'CWE-89')",
                },
            },
        },
    },
    {
        "name": "get_fix",
        "description": (
            "Get an AI-generated code fix for a specific security vulnerability. "
            "Returns before/after code, explanation, and a ready-to-apply patch. "
            "Requires CLAUDE_API_KEY."
        ),
        "input_schema": {
            "type": "object",
            "required": ["file_path", "description"],
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Absolute path to the file containing the vulnerability",
                },
                "line_number": {
                    "type": "integer",
                    "description": "Line number of the vulnerability (optional but improves accuracy)",
                    "minimum": 1,
                },
                "description": {
                    "type": "string",
                    "description": "Description of the vulnerability to fix (e.g., 'SQL injection in user lookup')",
                },
                "recommendation": {
                    "type": "string",
                    "description": "Existing recommendation or fix guidance, if available",
                },
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------

async def handle_scan_static(arguments: dict[str, Any]) -> str:
    """Run static analysis with the Go scanner binary."""
    repo_path = _validate_path(arguments["repo_path"])
    severity = _validate_severity(arguments.get("severity"))

    if not SCANNER_BIN.is_file():
        return json.dumps({"error": "Scanner binary not found. Run ./setup.sh to build it."})

    # Build command - auto-load rules from rules/ directory
    cmd = [str(SCANNER_BIN), "--dir", str(repo_path), "--output", "json"]
    if severity:
        cmd.extend(["--severity", severity])

    rule_files = sorted(RULES_DIR.glob("*.json")) if RULES_DIR.is_dir() else []
    if rule_files:
        cmd.extend(["--rules", ",".join(str(f) for f in rule_files)])

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        output = proc.stdout
    except subprocess.TimeoutExpired:
        return json.dumps({"error": "Static scan timed out after 5 minutes"})
    except Exception as e:
        return json.dumps({"error": f"Scanner failed: {e}"})

    # Parse JSON from output
    start = output.find("[")
    end = output.rfind("]") + 1
    if start < 0 or end <= start:
        return json.dumps({"findings": [], "count": 0})

    try:
        findings = json.loads(output[start:end])
    except json.JSONDecodeError:
        return json.dumps({"error": "Failed to parse scanner output"})

    return json.dumps({
        "findings": findings[:MAX_OUTPUT_FINDINGS],
        "count": len(findings),
        "truncated": len(findings) > MAX_OUTPUT_FINDINGS,
        "rules_loaded": len(rule_files),
    })


async def handle_scan_hybrid(arguments: dict[str, Any]) -> str:
    """Run a full hybrid scan via the orchestrator."""
    repo_path = _validate_path(arguments["repo_path"])
    profile = arguments.get("profile", "owasp")
    preset = arguments.get("preset")
    prioritize_top = min(arguments.get("prioritize_top", 10), 50)  # cap at 50 via MCP
    top_n = min(arguments.get("top_n", 5), 20)  # cap payloads/annotations
    question = arguments.get("question", "find the most critical security vulnerabilities")

    if question and len(question) > MAX_QUESTION_LENGTH:
        question = question[:MAX_QUESTION_LENGTH]

    if not SCANNER_BIN.is_file():
        return json.dumps({"error": "Scanner binary not found. Run ./setup.sh to build it."})

    # Build orchestrator command
    # When a preset is specified, let the preset control all settings.
    # Only add extra flags when running without a preset.
    cmd = [
        sys.executable, str(PROJECT_ROOT / "orchestrator.py"),
        str(repo_path), str(SCANNER_BIN),
        "--verbose",
    ]

    if preset:
        # Preset controls everything — only override prioritize_top if explicitly set
        cmd.extend(["--preset", preset])
        if arguments.get("prioritize_top"):
            cmd.extend(["--prioritize-top", str(prioritize_top)])
        if arguments.get("question"):
            cmd.extend(["--question", question])
    else:
        # No preset — use explicit flags
        cmd.extend([
            "--profile", profile,
            "--prioritize",
            "--prioritize-top", str(prioritize_top),
            "--question", question,
            "--generate-payloads",
            "--annotate-code",
            "--top-n", str(top_n),
            "--export-format", "json", "csv", "markdown", "html",
        ])

    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=180,
            cwd=str(PROJECT_ROOT),
        )
    except subprocess.TimeoutExpired:
        return json.dumps({"error": "Hybrid scan timed out after 3 minutes. Try reducing prioritize_top or using --preset quick."})
    except Exception as e:
        return json.dumps({"error": f"Orchestrator failed: {e}"})

    if proc.returncode != 0:
        return json.dumps({
            "error": "Scan failed",
            "stderr": proc.stderr[-2000:] if proc.stderr else "",
        })

    # Find the output directory (most recent)
    try:
        out_dir = _find_output_dir()
        combined = out_dir / "combined_findings.json"
        if combined.is_file():
            findings = json.loads(combined.read_text())
            return json.dumps({
                "status": "completed",
                "output_dir": str(out_dir),
                "total_findings": len(findings),
                "by_severity": _count_by_key(findings, "severity"),
                "by_source": _count_by_key(findings, "source"),
            })
    except Exception:
        pass

    return json.dumps({
        "status": "completed",
        "message": "Scan finished. Check output/ directory for results.",
    })


async def handle_detect_tech_stack(arguments: dict[str, Any]) -> str:
    """Detect technology stack of a repository."""
    repo_path = _validate_path(arguments["repo_path"])

    from lib.universal_detector import UniversalTechDetector

    try:
        result = UniversalTechDetector.detect_all(repo_path)
    except Exception as e:
        return json.dumps({"error": f"Tech stack detection failed: {e}"})

    return json.dumps(result, default=str)


async def handle_summarize_results(arguments: dict[str, Any]) -> str:
    """Summarize existing scan results."""
    out_dir = _find_output_dir(arguments.get("output_dir"))

    summary: dict[str, Any] = {"output_dir": str(out_dir)}

    # Static findings
    static_file = out_dir / "static_findings.json"
    if static_file.is_file():
        static = json.loads(static_file.read_text())
        summary["static"] = {
            "count": len(static),
            "by_severity": _count_by_key(static, "severity"),
            "top_rules": _count_by_key(static, "rule_name", top_n=10),
        }

    # AI findings
    ai_file = out_dir / "ai_findings.json"
    if ai_file.is_file():
        ai = json.loads(ai_file.read_text())
        summary["ai"] = {
            "count": len(ai),
            "by_severity": _count_by_key(ai, "severity"),
            "findings": [
                {
                    "severity": f.get("severity"),
                    "title": f.get("title", f.get("rule_name", "unknown")),
                    "file": Path(f.get("file_path", f.get("file", "?"))).name,
                    "line": f.get("line", f.get("line_number")),
                }
                for f in ai[:20]
            ],
        }

    # Combined
    combined_file = out_dir / "combined_findings.json"
    if combined_file.is_file():
        combined = json.loads(combined_file.read_text())
        summary["combined"] = {
            "count": len(combined),
            "by_severity": _count_by_key(combined, "severity"),
            "by_source": _count_by_key(combined, "source"),
        }

    # Cost
    cost_file = out_dir / "cost_tracking.json"
    if cost_file.is_file():
        cost = json.loads(cost_file.read_text())
        s = cost.get("summary", {})
        summary["cost"] = {
            "api_calls": s.get("total_calls", 0),
            "total_tokens": s.get("total_tokens", 0),
            "cost_usd": s.get("total_cost", 0),
        }

    # Tech stack
    tech_file = out_dir / "tech_stack.json"
    if tech_file.is_file():
        summary["tech_stack"] = json.loads(tech_file.read_text())

    # Artifacts
    payloads_dir = out_dir / "payloads"
    annotations_dir = out_dir / "annotations"
    summary["artifacts"] = {
        "payloads": len(list(payloads_dir.glob("*.json"))) if payloads_dir.is_dir() else 0,
        "annotations": len(list(annotations_dir.glob("*.md"))) if annotations_dir.is_dir() else 0,
    }

    return json.dumps(summary, default=str)


async def handle_list_findings(arguments: dict[str, Any]) -> str:
    """List findings with optional filtering."""
    out_dir = _find_output_dir(arguments.get("output_dir"))
    severity = _validate_severity(arguments.get("severity"))
    source_filter = arguments.get("source")
    limit = min(arguments.get("limit", 50), MAX_OUTPUT_FINDINGS)

    combined_file = out_dir / "combined_findings.json"
    if not combined_file.is_file():
        return json.dumps({"error": "No combined_findings.json found. Run a scan first."})

    findings = json.loads(combined_file.read_text())

    # Apply filters
    sev_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    if severity:
        threshold = sev_order.get(severity, 3)
        findings = [
            f for f in findings
            if sev_order.get(f.get("severity", "LOW"), 3) <= threshold
        ]

    if source_filter:
        findings = [f for f in findings if f.get("source") == source_filter]

    # Sort by severity
    findings.sort(key=lambda f: sev_order.get(f.get("severity", "LOW"), 3))

    total_matched = len(findings)
    findings = findings[:limit]

    # Slim down for transport
    slim = []
    for f in findings:
        slim.append({
            "severity": f.get("severity"),
            "title": f.get("title", f.get("rule_name", "unknown")),
            "file": f.get("file_path", f.get("file", "?")),
            "line": f.get("line", f.get("line_number")),
            "category": f.get("category", ""),
            "source": f.get("source", ""),
            "recommendation": (
                f.get("recommendation", f.get("fix", f.get("remediation", "")))[:200]
            ),
        })

    return json.dumps({
        "findings": slim,
        "returned": len(slim),
        "total_matched": total_matched,
        "filters": {"severity": severity, "source": source_filter},
    })


async def handle_list_presets(arguments: dict[str, Any]) -> str:
    """List available scan presets."""
    from lib.config import list_presets

    presets = list_presets()
    result = []
    for p in presets:
        result.append({
            "name": p.name,
            "description": p.description,
            "profiles": p.profiles if hasattr(p, "profiles") else [],
            "severity": getattr(p, "severity", None),
            "prioritize": getattr(p, "prioritize", False),
            "prioritize_top": getattr(p, "prioritize_top", None),
        })

    return json.dumps({"presets": result, "count": len(result)})


async def handle_scan_file(arguments: dict[str, Any]) -> str:
    """Scan a single file with the Go static scanner."""
    file_path = _validate_file_path(arguments["file_path"])
    severity = _validate_severity(arguments.get("severity"))

    if not SCANNER_BIN.is_file():
        return json.dumps({"error": "Scanner binary not found. Run ./setup.sh to build it."})

    # The scanner works on directories, so we scan the parent and filter
    cmd = [str(SCANNER_BIN), "--dir", str(file_path.parent), "--output", "json"]
    if severity:
        cmd.extend(["--severity", severity])

    rule_files = sorted(RULES_DIR.glob("*.json")) if RULES_DIR.is_dir() else []
    if rule_files:
        cmd.extend(["--rules", ",".join(str(f) for f in rule_files)])

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        output = proc.stdout
    except subprocess.TimeoutExpired:
        return json.dumps({"error": "Scan timed out after 2 minutes"})
    except Exception as e:
        return json.dumps({"error": f"Scanner failed: {e}"})

    # Parse and filter to just our file
    start = output.find("[")
    end = output.rfind("]") + 1
    if start < 0 or end <= start:
        return json.dumps({"findings": [], "count": 0, "file": str(file_path)})

    try:
        all_findings = json.loads(output[start:end])
    except json.JSONDecodeError:
        return json.dumps({"error": "Failed to parse scanner output"})

    # Filter findings to just the target file
    file_name = file_path.name
    file_str = str(file_path)
    findings = [
        f for f in all_findings
        if f.get("file", "").endswith(file_name)
        or file_str.endswith(f.get("file", "\x00"))
    ]

    return json.dumps({
        "file": str(file_path),
        "findings": findings[:MAX_OUTPUT_FINDINGS],
        "count": len(findings),
        "rules_loaded": len(rule_files),
    })


async def handle_explain_finding(arguments: dict[str, Any]) -> str:
    """Get a detailed AI explanation of a security finding."""
    file_path = _validate_file_path(arguments["file_path"])
    description = arguments["description"].strip()
    line_number = arguments.get("line_number")
    severity = arguments.get("severity", "MEDIUM")
    cwe = arguments.get("cwe", "")

    if not description or len(description) > MAX_QUESTION_LENGTH:
        raise ValueError(f"description must be 1-{MAX_QUESTION_LENGTH} characters")

    # Read the file for context
    content = file_path.read_text(encoding="utf-8", errors="replace")
    if len(content) > MAX_CODE_CONTEXT:
        # If file is too large, extract context around the line
        if line_number:
            lines = content.splitlines()
            start = max(0, line_number - 30)
            end = min(len(lines), line_number + 30)
            content = "\n".join(lines[start:end])
        else:
            content = content[:MAX_CODE_CONTEXT]

    # Build focused prompt
    line_ctx = f"\n- Line: {line_number}" if line_number else ""
    cwe_ctx = f"\n- CWE: {cwe}" if cwe else ""

    prompt = f"""You are a Principal Application Security Engineer providing a detailed explanation of a security finding to a development team.

FINDING:
- File: {file_path.name}
- Severity: {severity}{line_ctx}{cwe_ctx}
- Description: {description}

CODE CONTEXT:
```
{content}
```

Provide a thorough, educational explanation. Your entire response must be ONLY a JSON object:
{{
  "title": "Clear, specific title for this vulnerability",
  "explanation": "2-3 paragraph explanation of what this vulnerability is and why it matters",
  "attack_scenario": "Step-by-step description of how an attacker could exploit this",
  "impact": "What damage could result from successful exploitation",
  "cwe": "The most applicable CWE ID (e.g., CWE-89) with its name",
  "owasp_category": "Relevant OWASP Top 10 category (e.g., A03:2021 Injection)",
  "references": ["URL or reference 1", "URL or reference 2"],
  "severity_justification": "Why this severity rating is appropriate"
}}"""

    client = _get_ai_client()
    from lib.model_registry import get_default_model
    model = get_default_model()

    try:
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        raw = response.content[0].text
    except Exception as e:
        return json.dumps({"error": f"AI analysis failed: {type(e).__name__}: {e}"})

    from lib.common import parse_json_response
    parsed = parse_json_response(raw)

    if not parsed:
        return json.dumps({
            "error": "Failed to parse AI response",
            "raw_response": raw[:2000],
        })

    # Include metadata
    parsed["file"] = str(file_path)
    parsed["line_number"] = line_number
    parsed["model_used"] = model

    return json.dumps(parsed, default=str)


async def handle_get_fix(arguments: dict[str, Any]) -> str:
    """Get an AI-generated code fix for a vulnerability."""
    file_path = _validate_file_path(arguments["file_path"])
    description = arguments["description"].strip()
    line_number = arguments.get("line_number")
    recommendation = arguments.get("recommendation", "")

    if not description or len(description) > MAX_QUESTION_LENGTH:
        raise ValueError(f"description must be 1-{MAX_QUESTION_LENGTH} characters")

    # Read the file
    content = file_path.read_text(encoding="utf-8", errors="replace")
    if len(content) > MAX_CODE_CONTEXT:
        if line_number:
            lines = content.splitlines()
            start = max(0, line_number - 40)
            end = min(len(lines), line_number + 40)
            content = "\n".join(lines[start:end])
        else:
            content = content[:MAX_CODE_CONTEXT]

    line_ctx = f"\n- Vulnerable Line: {line_number}" if line_number else ""
    rec_ctx = f"\n- Existing Recommendation: {recommendation}" if recommendation else ""

    prompt = f"""You are a secure coding expert. Provide a precise, production-ready fix for this security vulnerability.

VULNERABILITY:
- File: {file_path.name}
- Description: {description}{line_ctx}{rec_ctx}

CODE:
```
{content}
```

INSTRUCTIONS:
1. Identify the vulnerable code precisely
2. Provide a corrected version that eliminates the vulnerability
3. Ensure the fix maintains existing functionality
4. Use secure coding best practices for this language/framework

Your entire response must be ONLY a JSON object:
{{
  "vulnerable_code": "The exact vulnerable code snippet (5-15 lines)",
  "fixed_code": "The corrected code snippet that replaces the vulnerable code",
  "explanation": "Why this fix eliminates the vulnerability and how it works",
  "changes_summary": "One-line summary of what changed",
  "additional_recommendations": ["Any other hardening steps to consider"],
  "test_suggestion": "How to verify the fix works and the vulnerability is gone"
}}"""

    client = _get_ai_client()
    from lib.model_registry import get_default_model
    model = get_default_model()

    try:
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,  # Low temp for precise code
        )
        raw = response.content[0].text
    except Exception as e:
        return json.dumps({"error": f"AI fix generation failed: {type(e).__name__}: {e}"})

    from lib.common import parse_json_response
    parsed = parse_json_response(raw)

    if not parsed:
        return json.dumps({
            "error": "Failed to parse AI response",
            "raw_response": raw[:2000],
        })

    # Include metadata
    parsed["file"] = str(file_path)
    parsed["line_number"] = line_number
    parsed["model_used"] = model

    return json.dumps(parsed, default=str)


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

TOOL_HANDLERS = {
    "scan_static": handle_scan_static,
    "scan_hybrid": handle_scan_hybrid,
    "detect_tech_stack": handle_detect_tech_stack,
    "summarize_results": handle_summarize_results,
    "list_findings": handle_list_findings,
    "list_presets": handle_list_presets,
    "scan_file": handle_scan_file,
    "explain_finding": handle_explain_finding,
    "get_fix": handle_get_fix,
}
