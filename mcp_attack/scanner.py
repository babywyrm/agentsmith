"""Scan orchestration and cross-target analysis."""

import threading
import time
from collections import defaultdict
from urllib.parse import urlparse

from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)

from mcp_attack.core.models import TargetResult
from mcp_attack.core.session import detect_transport
from mcp_attack.core.enumerator import enumerate_server
from mcp_attack.checks import run_all_checks

console = Console()


def detect_cross_shadowing(results: list[TargetResult]):
    """Detect tool name collisions across servers."""
    tool_map: dict[str, list[str]] = defaultdict(list)
    for r in results:
        for t in r.tools:
            tool_map[t["name"]].append(r.url)
    for name, servers in tool_map.items():
        if len(servers) > 1:
            for r in results:
                if r.url in servers:
                    r.add(
                        "cross_shadowing",
                        "MEDIUM",
                        f"Tool '{name}' exists on {len(servers)} servers",
                        f"Servers: {servers}",
                    )


def scan_target(
    url: str,
    all_results: list[TargetResult],
    timeout: float = 25.0,
    verbose: bool = False,
) -> TargetResult:
    result = TargetResult(url=url)
    t_start = time.time()
    console.print(f"\n[bold cyan]▶ {url}[/bold cyan]")

    session = detect_transport(url, connect_timeout=timeout, verbose=verbose)

    if not session:
        console.print(f"  [red]✗[/red] No MCP transport found on {url}")
        result.transport = "none"
        result.add(
            "transport",
            "HIGH",
            "No MCP endpoint found",
            "Tried SSE + HTTP POST on common paths",
        )
        result.timings["total"] = time.time() - t_start
        return result

    transport_label = (
        "SSE"
        if hasattr(session, "sse_url") and session.sse_url
        else "HTTP"
    )
    result.transport = transport_label
    console.print(
        f"  [green]✓[/green] Transport={transport_label}"
        f"  post_url={session.post_url}"
    )

    base = ""
    sse_path = ""
    if hasattr(session, "sse_url") and session.sse_url:
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        sse_path = urlparse(session.sse_url).path

    enumerate_server(session, result, verbose=verbose)
    console.print(
        f"  [dim]Tools={len(result.tools)} "
        f"Resources={len(result.resources)} "
        f"Prompts={len(result.prompts)}[/dim]"
    )

    run_all_checks(
        session,
        result,
        all_results,
        base=base,
        sse_path=sse_path,
        verbose=verbose,
    )

    session.close()
    result.timings["total"] = time.time() - t_start
    console.print(
        f"  [dim]Done in {result.timings['total']:.1f}s  "
        f"findings={len(result.findings)}  score={result.risk_score()}[/dim]"
    )
    return result


def run_parallel(
    urls: list[str],
    timeout: float = 25.0,
    workers: int = 4,
    verbose: bool = False,
) -> list[TargetResult]:
    results: list[TargetResult] = []
    lock = threading.Lock()

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    )
    task = progress.add_task(
        f"Scanning {len(urls)} target(s)", total=len(urls)
    )

    with progress:

        def worker(url: str):
            with lock:
                snapshot = list(results)
            r = scan_target(url, snapshot, timeout=timeout, verbose=verbose)
            with lock:
                results.append(r)
            progress.advance(task)

        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
            futures = [ex.submit(worker, u) for u in urls]
            concurrent.futures.wait(futures)

    return results
