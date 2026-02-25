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
from rich.console import Console
from rich.panel import Panel

console = Console()


def main():
    args = parse_args()
    urls = build_url_list(args)

    console.print(
        Panel(
            f"[bold cyan]mcp-audit v{__version__}[/bold cyan]\n"
            f"Targets : {len(urls)}\n"
            f"Workers : {args.workers}\n"
            f"Timeout : {args.timeout}s\n"
            f"Verbose : {args.verbose}  Debug: {args.debug}\n"
            f"Started : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
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

    print_report(results)

    if args.json_out:
        write_json(results, args.json_out, console=console)

    all_findings = [f for r in results for f in r.findings]
    if any(f.severity in ("CRITICAL", "HIGH") for f in all_findings):
        sys.exit(1)


if __name__ == "__main__":
    main()
