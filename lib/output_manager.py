#!/usr/bin/env python3
"""
Output formatting and export for Smart Analyzer and CTF Analyzer.

Handles console display, report export (JSON, Markdown, HTML), and
code improvement reports.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from lib.models import AnalysisReport, Finding


class OutputManager:
    """Manages output display and report export for analysis results."""

    def __init__(self, console: Console) -> None:
        self.console = console

    def display_console_summary(self, report: AnalysisReport) -> None:
        """Display analysis report summary in the console."""
        self.console.print()
        self.console.print(Panel(
            f"[bold]Analysis Report[/bold]\n"
            f"Repository: {report.repo_path}\n"
            f"Question: {report.question}\n"
            f"Files analyzed: {report.file_count}\n"
            f"Findings: {len(report.insights)}",
            title="Summary",
            border_style="cyan",
        ))
        if report.insights:
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Impact", style="cyan", width=10)
            table.add_column("File", style="green", width=30)
            table.add_column("Finding", width=50)
            for f in report.insights[:20]:
                impact_color = {"CRITICAL": "red", "HIGH": "yellow", "MEDIUM": "cyan", "LOW": "dim"}.get(f.impact, "white")
                table.add_row(
                    f"[{impact_color}]{f.impact}[/{impact_color}]",
                    Path(f.file_path).name,
                    f.finding[:80] + "..." if len(f.finding) > 80 else f.finding,
                )
            self.console.print(table)
            if len(report.insights) > 20:
                self.console.print(f"[dim]... and {len(report.insights) - 20} more findings[/dim]")
        self.console.print(Panel(report.synthesis[:2000] + ("..." if len(report.synthesis) > 2000 else ""), title="Synthesis", border_style="dim"))

    def save_reports(
        self,
        report: AnalysisReport,
        formats: List[str],
        output: Optional[Path] = None,
    ) -> None:
        """Save report to JSON, Markdown, and/or HTML."""
        if output:
            p = Path(output)
            base = p.parent / p.stem if p.suffix else p
        else:
            base = Path("report")
        for fmt in formats:
            if fmt == "json":
                path = base.with_suffix(".json")
                path.parent.mkdir(parents=True, exist_ok=True)
                data = {
                    "repo_path": report.repo_path,
                    "question": report.question,
                    "timestamp": report.timestamp,
                    "file_count": report.file_count,
                    "synthesis": report.synthesis,
                    "findings": [
                        {
                            "file_path": f.file_path,
                            "finding": f.finding,
                            "recommendation": f.recommendation,
                            "impact": f.impact,
                            "relevance": f.relevance,
                            "line_number": f.line_number,
                        }
                        for f in report.insights
                    ],
                }
                import json
                path.write_text(json.dumps(data, indent=2), encoding="utf-8")
                self.console.print(f"[green]✓[/green] JSON report: {path}")
            elif fmt == "markdown":
                path = base.with_suffix(".md")
                path.parent.mkdir(parents=True, exist_ok=True)
                lines = [
                    f"# Analysis Report",
                    f"**Repository:** {report.repo_path}",
                    f"**Question:** {report.question}",
                    f"**Files analyzed:** {report.file_count}",
                    f"**Findings:** {len(report.insights)}",
                    "",
                    "## Synthesis",
                    report.synthesis,
                    "",
                    "## Findings",
                    "| Impact | File | Finding | Recommendation |",
                    "|--------|------|---------|----------------|",
                ]
                for f in report.insights:
                    rec = f.recommendation[:40] + "..." if len(f.recommendation) > 40 else f.recommendation
                    find = f.finding[:60] + "..." if len(f.finding) > 60 else f.finding
                    lines.append(f"| {f.impact} | {Path(f.file_path).name} | {find} | {rec} |")
                path.write_text("\n".join(lines), encoding="utf-8")
                self.console.print(f"[green]✓[/green] Markdown report: {path}")
            elif fmt == "html":
                path = base.with_suffix(".html")
                path.parent.mkdir(parents=True, exist_ok=True)
                rows = "".join(
                    f"<tr><td>{f.impact}</td><td>{Path(f.file_path).name}</td><td>{f.finding[:80]}</td></tr>"
                    for f in report.insights
                )
                html = f"""<!DOCTYPE html><html><head><title>Analysis Report</title></head><body>
<h1>Analysis Report</h1><p><b>Repo:</b> {report.repo_path}</p><p><b>Question:</b> {report.question}</p>
<h2>Synthesis</h2><p>{report.synthesis[:2000]}</p>
<h2>Findings</h2><table border="1"><tr><th>Impact</th><th>File</th><th>Finding</th></tr>{rows}</table></body></html>"""
                path.write_text(html, encoding="utf-8")
                self.console.print(f"[green]✓[/green] HTML report: {path}")

    def display_code_improvements(self, improvements: Dict[str, Any]) -> None:
        """Display code improvement suggestions in the console."""
        self.console.print(Panel("[bold]Code Improvement Suggestions[/bold]", border_style="green"))
        for file_path, items in improvements.items():
            self.console.print(f"\n[cyan]{Path(file_path).name}[/cyan]")
            for item in items:
                self.console.print(f"  • {item.get('suggestion', item)}")

    def save_improvement_report(self, improvements: Dict[str, Any], output_path: Path) -> None:
        """Save code improvement report to a Markdown file."""
        lines = ["# Code Improvement Report", ""]
        for file_path, items in improvements.items():
            lines.append(f"## {Path(file_path).name}")
            for item in items:
                lines.append(f"- {item.get('suggestion', str(item))}")
            lines.append("")
        output_path.write_text("\n".join(lines), encoding="utf-8")
        self.console.print(f"[green]✓[/green] Improvement report: {output_path}")

    def write_optimized_files(
        self,
        optimized_code: Dict[str, str],
        output_path: Path,
        repo_path: Path,
        diff: bool = False,
    ) -> None:
        """Write optimized code to files."""
        output_path.mkdir(parents=True, exist_ok=True)
        for rel_path, content in optimized_code.items():
            out_file = output_path / rel_path
            out_file.parent.mkdir(parents=True, exist_ok=True)
            out_file.write_text(content, encoding="utf-8")
            self.console.print(f"[green]✓[/green] Wrote {out_file}")
