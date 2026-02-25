#!/usr/bin/env python3
"""
mcp-audit — MCP Red Teaming / Security Scanner

Install:
    pip install httpx rich

Usage:
    python -m mcp_attack --targets http://localhost:2266
    python -m mcp_attack --port-range localhost:9001-9010 --verbose
    python -m mcp_attack --port-range localhost:9001-9010 --debug --json report.json
"""

import sys
from datetime import datetime

from mcp_attack import __version__
from mcp_attack.cli import parse_args, build_url_list
from mcp_attack.scanner import scan_target, run_parallel, detect_cross_shadowing
from mcp_attack.reporting import print_report, write_json
from mcp_attack.k8s import run_k8s_checks
from mcp_attack.diff import (
    load_baseline,
    save_baseline,
    diff_against_baseline,
    print_diff_report,
)
from rich.console import Console
from rich.panel import Panel

console = Console()


def main():
    args = parse_args()
    urls = build_url_list(args)

    baseline = {}
    if args.baseline:
        baseline = load_baseline(args.baseline)
        if not baseline:
            console.print(f"[yellow]Baseline empty or not found: {args.baseline}[/yellow]")

    panel_lines = [
        f"[bold cyan]mcp-audit v{__version__}[/bold cyan]",
        f"Targets : {len(urls)}",
        f"Workers : {args.workers}",
        f"Timeout : {args.timeout}s",
        f"Verbose : {args.verbose}  Debug: {args.debug}",
        f"Started : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    ]
    if args.baseline:
        panel_lines.append(f"Baseline: {args.baseline}")
    if args.save_baseline:
        panel_lines.append(f"Save baseline: {args.save_baseline}")

    console.print(
        Panel(
            "\n".join(panel_lines),
            title="MCP Security Scanner",
            border_style="cyan",
        )
    )

    if not args.no_k8s:
        run_k8s_checks(args.k8s_namespace, console=console)

    if len(urls) == 1:
        results = [scan_target(urls[0], [], timeout=args.timeout, verbose=args.verbose)]
    else:
        results = run_parallel(
            urls,
            timeout=args.timeout,
            workers=args.workers,
            verbose=args.verbose,
        )

    detect_cross_shadowing(results)

    # Differential scan: compare to baseline and add findings
    diff_results = []
    if args.baseline and baseline:
        for r in results:
            base = baseline.get(r.url, {})
            if base:
                diff = diff_against_baseline(
                    r.tools,
                    r.resources,
                    r.prompts,
                    base.get("tools", []),
                    base.get("resources", []),
                    base.get("prompts", []),
                    url=r.url,
                )
                diff_results.append(diff)
                # Add findings for new tools (security regression)
                for t in diff.added_tools:
                    r.add(
                        "differential",
                        "MEDIUM",
                        f"Added tool: {t.get('name', '?')}",
                        "New tool since baseline — review for security impact",
                    )
        print_diff_report(diff_results, args.baseline, console=console)

    print_report(results)

    if args.save_baseline:
        save_baseline(results, args.save_baseline, console=console)

    if args.json_out:
        write_json(results, args.json_out, console=console)

    all_findings = [f for r in results for f in r.findings]
    if any(f.severity in ("CRITICAL", "HIGH") for f in all_findings):
        sys.exit(1)


if __name__ == "__main__":
    main()
