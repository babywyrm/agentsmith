#!/usr/bin/env python3
"""
Agent Smith MCP Test Client

Full-featured client for testing, interacting with, and validating
the Agent Smith MCP server.

Modes:
    test       Run automated test suite against the server (default)
    interact   Interactive REPL to call tools manually
    list       List available tools with full schemas
    benchmark  Time each tool call and report latency

Usage:
    python3 -m mcp_server.test_client                             # run all tests
    python3 -m mcp_server.test_client test --tool scan_static     # test one tool
    python3 -m mcp_server.test_client interact                    # interactive REPL
    python3 -m mcp_server.test_client list                        # list tools + schemas
    python3 -m mcp_server.test_client benchmark                   # latency benchmarks
    python3 -m mcp_server.test_client test --all                  # include scan_hybrid
    python3 -m mcp_server.test_client test --json                 # JSON output for CI
    python3 -m mcp_server.test_client test --quiet                # minimal output
"""

import argparse
import asyncio
import json
import sys
import threading
import time
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[0;32m"
RED = "\033[0;31m"
YELLOW = "\033[0;33m"
CYAN = "\033[0;36m"
MAGENTA = "\033[0;35m"
WHITE = "\033[1;37m"
RESET = "\033[0m"

_no_color = False


def c(text, color):
    if _no_color:
        return str(text)
    return f"{color}{text}{RESET}"


# ---------------------------------------------------------------------------
# Spinner
# ---------------------------------------------------------------------------

class Spinner:
    """Animated spinner for long-running operations."""
    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, message: str = ""):
        self._message = message
        self._stop = threading.Event()
        self._thread = None
        self._start_time = 0.0

    def start(self, message: str = ""):
        if message:
            self._message = message
        self._start_time = time.monotonic()
        self._stop.clear()
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def _spin(self):
        i = 0
        while not self._stop.is_set():
            elapsed = time.monotonic() - self._start_time
            frame = self.FRAMES[i % len(self.FRAMES)]
            msg = f"\r    {c(frame, CYAN)} {self._message} {c(f'({elapsed:.0f}s)', DIM)}"
            sys.stdout.write(msg)
            sys.stdout.flush()
            i += 1
            self._stop.wait(0.1)

    def stop(self, clear: bool = True):
        self._stop.set()
        if self._thread:
            self._thread.join()
        if clear:
            sys.stdout.write("\r" + " " * 80 + "\r")
            sys.stdout.flush()


# ---------------------------------------------------------------------------
# Connection helper
# ---------------------------------------------------------------------------

async def connect(url: str, retries: int = 2, delay: float = 1.0):
    """Connect to MCP server with retry logic and fast failure."""
    import httpx

    # Quick pre-check: is the server even reachable?
    health_url = url.rsplit("/", 1)[0] + "/health"
    try:
        async with httpx.AsyncClient() as http:
            resp = await http.get(health_url, timeout=3.0)
            if resp.status_code != 200:
                raise ConnectionError(
                    f"Server at {health_url} returned status {resp.status_code}"
                )
    except httpx.ConnectError:
        raise ConnectionError(
            f"Server not reachable at {health_url}\n"
            f"  Start it with: python3 -m mcp_server --no-auth"
        )
    except httpx.TimeoutException:
        raise ConnectionError(
            f"Server at {health_url} timed out\n"
            f"  Start it with: python3 -m mcp_server --no-auth"
        )

    from mcp.client.sse import sse_client
    from mcp import ClientSession

    last_err = None
    for attempt in range(1, retries + 1):
        try:
            ctx = sse_client(url)
            read_stream, write_stream = await ctx.__aenter__()
            session = ClientSession(read_stream, write_stream)
            await session.__aenter__()
            await session.initialize()
            return ctx, session
        except (ConnectionRefusedError, OSError) as e:
            last_err = e
            if attempt < retries:
                await asyncio.sleep(delay * attempt)
        except Exception as e:
            last_err = e
            break

    raise ConnectionError(
        f"Cannot connect to {url} after {retries} attempts: {last_err}\n"
        f"  Make sure the server is running: python3 -m mcp_server --no-auth"
    )


def _detect_repo_path() -> str | None:
    """Auto-detect a test target repo path."""
    project_root = Path(__file__).resolve().parent.parent
    candidates = [
        project_root / "tests" / "test_targets" / "DVWA",
        project_root / "tests" / "test_targets" / "WebGoat",
        project_root / "tests" / "test_targets" / "juice-shop",
        project_root,
    ]
    for candidate in candidates:
        if candidate.is_dir():
            return str(candidate)
    return None


# ---------------------------------------------------------------------------
# Mode: test
# ---------------------------------------------------------------------------

async def mode_test(url: str, tool_filter: str | None = None,
                    include_all: bool = False, repo_path: str | None = None,
                    json_output: bool = False, quiet: bool = False):
    """Run automated test suite against the MCP server."""
    results = []
    repo_path = repo_path or _detect_repo_path()

    if not json_output:
        print(f"\n{c('Agent Smith MCP Test Suite', BOLD)}")
        print(f"{'=' * 60}")
        print(f"  Server:    {c(url, CYAN)}")
        print(f"  Repo:      {c(repo_path or 'none', DIM)}")
        print()

    try:
        ctx, session = await connect(url)
    except ConnectionError as e:
        if json_output:
            print(json.dumps({"error": str(e), "passed": 0, "failed": 1}))
        else:
            print(f"{c('ERROR', RED)}: {e}")
        return False

    spinner = Spinner()

    try:
        tools_result = await session.list_tools()
        tools = tools_result.tools
        tool_names = [t.name for t in tools]

        if not json_output:
            print(f"{c('Connected', GREEN)} - {len(tools)} tools available")
            print()

        # Build test cases
        test_cases = _build_test_cases(repo_path, tool_filter, include_all, tool_names)

        for tc in test_cases:
            name = tc["name"]
            tool = tc["tool"]
            args = tc["args"]
            checks = tc.get("checks", [])
            is_slow = tool in ("scan_static", "scan_hybrid", "detect_tech_stack")

            if not json_output:
                print(f"  {c('TEST', BOLD)}: {c(name, WHITE)}")
                if not quiet:
                    print(f"    {c('tool', DIM)}: {tool}")
                    if args:
                        _print_args(args)

            # Start spinner for slow operations with time estimates
            if is_slow and not json_output and not quiet:
                if tool == "scan_hybrid":
                    spinner.start(f"Running {tool} (expect 30-90s for AI calls)...")
                else:
                    spinner.start(f"Running {tool}...")

            t0 = time.monotonic()
            try:
                result = await session.call_tool(tool, args)
                elapsed_ms = (time.monotonic() - t0) * 1000

                if is_slow:
                    spinner.stop()

                text = result.content[0].text
                data = json.loads(text)

                # Run assertion checks
                ok = True
                messages = []
                has_error = "error" in data

                if has_error and not tc.get("expect_error"):
                    ok = False
                    messages.append(f"unexpected error: {data['error']}")
                elif has_error and tc.get("expect_error"):
                    ok = True
                    messages.append(f"got expected error")
                else:
                    for check in checks:
                        check_ok, msg = check(data)
                        if not check_ok:
                            ok = False
                        messages.append(msg)

                status = "PASS" if ok else "FAIL"
                results.append({
                    "name": name, "tool": tool, "status": status,
                    "elapsed_ms": round(elapsed_ms, 1),
                    "messages": messages,
                    "data": data,
                })

                if not json_output:
                    icon = c("PASS", GREEN) if ok else c("FAIL", RED)
                    check_summary = "; ".join(messages)
                    print(f"    {icon} {c(f'({elapsed_ms:.0f}ms)', DIM)} {check_summary}")

                    # Always show rich detail (unless quiet)
                    if not quiet:
                        if has_error and tc.get("expect_error"):
                            print(f"    {c('blocked', DIM)}: {data['error'][:70]}")
                        elif not has_error:
                            _print_result_detail(tool, data)

            except Exception as e:
                spinner.stop()
                elapsed_ms = (time.monotonic() - t0) * 1000
                results.append({
                    "name": name, "tool": tool, "status": "ERROR",
                    "elapsed_ms": round(elapsed_ms, 1),
                    "messages": [f"{type(e).__name__}: {e}"],
                })
                if not json_output:
                    print(f"    {c('ERROR', RED)} {c(f'({elapsed_ms:.0f}ms)', DIM)} "
                          f"{type(e).__name__}: {e}")

            if not json_output:
                print()

    finally:
        await session.__aexit__(None, None, None)
        await ctx.__aexit__(None, None, None)

    # Summary
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] in ("FAIL", "ERROR"))
    total = len(results)
    total_ms = sum(r["elapsed_ms"] for r in results)

    if json_output:
        print(json.dumps({
            "passed": passed, "failed": failed, "total": total,
            "total_ms": round(total_ms, 1),
            "results": results,
        }, indent=2, default=str))
    else:
        print(f"{c('Results', BOLD)}")
        print(f"{'=' * 60}")
        print(f"  Passed:     {c(str(passed), GREEN)}")
        if failed:
            print(f"  Failed:     {c(str(failed), RED)}")
        print(f"  Total:      {total}")
        print(f"  Total time: {_format_duration(total_ms)}")
        print()

    return failed == 0


def _print_args(args: dict):
    """Print tool arguments in a readable format."""
    for k, v in args.items():
        val = str(v)
        if len(val) > 60:
            val = val[:60] + "..."
        print(f"      {c(k, CYAN)}: {val}")


def _format_duration(ms: float) -> str:
    """Format milliseconds into a human-readable duration."""
    if ms < 1000:
        return f"{ms:.0f}ms"
    elif ms < 60_000:
        return f"{ms / 1000:.1f}s"
    else:
        mins = int(ms / 60_000)
        secs = (ms % 60_000) / 1000
        return f"{mins}m {secs:.0f}s"


def _build_test_cases(repo_path, tool_filter, include_all, available_tools):
    """Build the list of test cases to run."""
    cases = []

    def add(name, tool, args, checks=None, expect_error=False):
        if tool_filter and tool != tool_filter:
            return
        if tool not in available_tools:
            return
        cases.append({
            "name": name, "tool": tool, "args": args,
            "checks": checks or [], "expect_error": expect_error,
        })

    # --- list_presets ---
    add("list all presets", "list_presets", {}, [
        lambda d: (d.get("count", 0) >= 4, f"{d.get('count', 0)} presets found"),
        lambda d: (
            any(p["name"] == "ctf" for p in d.get("presets", [])),
            "ctf preset present" if any(p["name"] == "ctf" for p in d.get("presets", []))
            else "ctf preset missing"
        ),
    ])

    # --- summarize_results ---
    add("summarize latest results", "summarize_results", {}, [
        lambda d: ("combined" in d or "static" in d, "has findings data"),
    ])

    # --- list_findings ---
    add("list critical findings", "list_findings", {"severity": "CRITICAL", "limit": 5}, [
        lambda d: (isinstance(d.get("findings"), list), "findings is a list"),
        lambda d: (d.get("returned", 0) <= 5, f"limit respected: {d.get('returned', 0)} <= 5"),
        lambda d: (
            all(f.get("severity") == "CRITICAL" for f in d.get("findings", [])),
            "all findings are CRITICAL"
        ),
    ])

    add("list high+ findings with limit", "list_findings", {"severity": "HIGH", "limit": 10}, [
        lambda d: (d.get("returned", 0) <= 10, f"limit respected: {d.get('returned', 0)} <= 10"),
        lambda d: (
            all(f.get("severity") in ("CRITICAL", "HIGH") for f in d.get("findings", [])),
            "severity filter correct"
        ),
    ])

    add("list findings by source", "list_findings",
        {"source": "agentsmith", "limit": 3}, [
        lambda d: (
            all(f.get("source") == "agentsmith" for f in d.get("findings", [])),
            "source filter correct"
        ),
    ])

    # --- detect_tech_stack ---
    if repo_path:
        add("detect tech stack", "detect_tech_stack", {"repo_path": repo_path}, [
            lambda d: ("languages" in d, "languages detected"),
            lambda d: ("frameworks" in d, "frameworks detected"),
        ])

    # --- scan_static ---
    if repo_path:
        add("static scan (HIGH+)", "scan_static",
            {"repo_path": repo_path, "severity": "HIGH"}, [
            lambda d: (d.get("count", 0) > 0, f"{d.get('count', 0)} findings"),
            lambda d: (d.get("rules_loaded", 0) > 0, f"{d.get('rules_loaded', 0)} rule files loaded"),
        ])

        add("static scan (CRITICAL only)", "scan_static",
            {"repo_path": repo_path, "severity": "CRITICAL"}, [
            lambda d: (isinstance(d.get("findings"), list), "findings returned"),
        ])

    # --- Input validation / security tests ---
    add("reject invalid path", "scan_static",
        {"repo_path": "/nonexistent/fakepath"}, expect_error=True)

    add("reject traversal attack", "scan_static",
        {"repo_path": "/etc/passwd/../../../tmp"}, expect_error=True)

    add("reject missing repo_path", "detect_tech_stack",
        {"repo_path": ""}, expect_error=True)

    # --- scan_hybrid (only if --all) ---
    # Uses tight defaults: prioritize top 5 files, quick preset to keep it fast
    if include_all and repo_path:
        add("hybrid scan (quick preset, top 5)", "scan_hybrid",
            {"repo_path": repo_path, "preset": "quick", "prioritize_top": 5,
             "question": "find the top 5 most critical vulnerabilities"}, [
            lambda d: (d.get("status") == "completed", f"status: {d.get('status')}"),
        ])

    return cases


# ---------------------------------------------------------------------------
# Result detail printing (always shown unless --quiet)
# ---------------------------------------------------------------------------

def _print_result_detail(tool_name: str, data: dict):
    """Print detailed, informative result for each tool."""
    if tool_name == "list_presets":
        for p in data.get("presets", []):
            profiles = ", ".join(p.get("profiles", [])) or "default"
            print(f"      {c(p['name'], CYAN):>20}: {p.get('description', '')[:55]}")

    elif tool_name == "summarize_results":
        combined = data.get("combined", {})
        cost = data.get("cost", {})
        static = data.get("static", {})
        ai = data.get("ai", {})
        artifacts = data.get("artifacts", {})

        print(f"    {c('Findings:', BOLD)}")
        print(f"      Static:     {static.get('count', 0)}")
        print(f"      AI:         {ai.get('count', 0)}")
        print(f"      Combined:   {combined.get('count', 0)}")

        by_sev = combined.get("by_severity", {})
        if by_sev:
            parts = []
            for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
                if sev in by_sev:
                    color = {"CRITICAL": RED, "HIGH": RED, "MEDIUM": YELLOW, "LOW": CYAN}.get(sev, DIM)
                    parts.append(f"{c(sev, color)}: {by_sev[sev]}")
            print(f"      Severity:   {', '.join(parts)}")

        by_source = combined.get("by_source", {})
        if by_source:
            print(f"      Sources:    {', '.join(f'{k} ({v})' for k, v in by_source.items())}")

        if cost:
            cost_usd = cost.get('cost_usd', 0)
            print(f"    {c('Cost:', BOLD)}")
            print(f"      API calls:  {cost.get('api_calls', 0)}")
            print(f"      Tokens:     {cost.get('total_tokens', 0):,}")
            print(f"      Cost:       {c(f'${cost_usd:.3f}', GREEN)}")

        if artifacts.get("payloads") or artifacts.get("annotations"):
            print(f"    {c('Artifacts:', BOLD)}")
            print(f"      Payloads:   {artifacts.get('payloads', 0)}")
            print(f"      Annotations: {artifacts.get('annotations', 0)}")

        # Top rules from static
        top_rules = static.get("top_rules", {})
        if top_rules:
            print(f"    {c('Top static rules:', BOLD)}")
            for rule, cnt in list(top_rules.items())[:5]:
                print(f"      {cnt:>5}x  {rule}")

        # AI findings summary
        ai_findings = ai.get("findings", [])
        if ai_findings:
            print(f"    {c('AI findings:', BOLD)}")
            for f in ai_findings[:5]:
                sev = f.get("severity", "?")
                color = {"CRITICAL": RED, "HIGH": RED, "MEDIUM": YELLOW}.get(sev, DIM)
                title = f.get("title", "?")[:50]
                loc = f"{f.get('file', '?')}:{f.get('line', '?')}"
                print(f"      {c(f'[{sev}]', color):>22} {title} {c(loc, DIM)}")

    elif tool_name == "list_findings":
        returned = data.get("returned", 0)
        total = data.get("total_matched", 0)
        filters = data.get("filters", {})
        print(f"    {c(f'{returned} of {total} matched', DIM)} "
              f"(severity>={filters.get('severity', 'any')}, "
              f"source={filters.get('source', 'any')})")
        for f in data.get("findings", [])[:8]:
            sev = f.get("severity", "?")
            color = {"CRITICAL": RED, "HIGH": RED, "MEDIUM": YELLOW, "LOW": CYAN}.get(sev, DIM)
            title = f.get("title", "?")[:50]
            fname = Path(f.get("file", "?")).name
            line = f.get("line", "")
            loc = f"{fname}:{line}" if line else fname
            rec = f.get("recommendation", "")
            print(f"      {c(f'[{sev}]', color):>22} {title}")
            print(f"      {'':>14} {c(loc, DIM)}")
            if rec:
                print(f"      {'':>14} {c(rec[:65], GREEN)}")
        if returned > 8:
            print(f"      {c(f'... and {returned - 8} more', DIM)}")

    elif tool_name == "detect_tech_stack":
        langs = data.get("languages", [])
        if isinstance(langs, dict):
            langs = list(langs.keys())
        fws = data.get("frameworks", {})
        entries = data.get("entry_points", [])
        sec_files = data.get("security_critical_files", data.get("security_files", []))
        risks = data.get("framework_specific_risks", data.get("risks", []))

        print(f"    {c('Languages:', BOLD)}  {', '.join(langs)}")

        if isinstance(fws, dict):
            fw_items = sorted(fws.items(), key=lambda x: x[1], reverse=True)
            confirmed = [(n, s) for n, s in fw_items if s >= 0.8]
            possible = [(n, s) for n, s in fw_items if s < 0.8]

            if confirmed:
                print(f"    {c('Confirmed:', BOLD)}")
                for name, conf in confirmed[:6]:
                    bar_len = int(conf * 20)
                    bar = c("█" * bar_len, GREEN) + c("░" * (20 - bar_len), DIM)
                    print(f"      {name:>15} {bar} {int(conf * 100)}%")
            if possible:
                names = ", ".join(n for n, _ in possible[:8])
                print(f"    {c('Possible:', DIM)}   {names}")
        elif isinstance(fws, list):
            print(f"    {c('Frameworks:', BOLD)} {', '.join(str(f) for f in fws[:6])}")

        if entries:
            print(f"    {c('Entry points:', BOLD)} ({len(entries)})")
            for ep in entries[:5]:
                ep_name = ep if isinstance(ep, str) else ep.get("file", str(ep))
                print(f"      {c('>', CYAN)} {Path(ep_name).name}")
            if len(entries) > 5:
                print(f"      {c(f'... and {len(entries) - 5} more', DIM)}")

        if sec_files:
            print(f"    {c('Security files:', BOLD)} ({len(sec_files)})")
            for sf in sec_files[:5]:
                sf_name = sf if isinstance(sf, str) else sf.get("file", str(sf))
                print(f"      {c('!', YELLOW)} {Path(sf_name).name}")

        if risks:
            print(f"    {c('Risks:', BOLD)} ({len(risks)})")
            for r in risks[:4]:
                print(f"      {c('⚠', YELLOW)} {r}")

    elif tool_name == "scan_static":
        count = data.get("count", 0)
        rules = data.get("rules_loaded", 0)
        truncated = data.get("truncated", False)
        print(f"    {c(f'{count} findings from {rules} rule files', DIM)}"
              f"{'  (truncated to 500)' if truncated else ''}")

        # Show severity breakdown from findings
        findings = data.get("findings", [])
        if findings:
            sevs: dict[str, int] = {}
            rule_counts: dict[str, int] = {}
            for f in findings:
                s = f.get("severity", "?")
                sevs[s] = sevs.get(s, 0) + 1
                rn = f.get("rule_name", "?")
                rule_counts[rn] = rule_counts.get(rn, 0) + 1

            parts = []
            for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
                if sev in sevs:
                    color = {"CRITICAL": RED, "HIGH": RED, "MEDIUM": YELLOW, "LOW": CYAN}.get(sev, DIM)
                    parts.append(f"{c(sev, color)}: {sevs[sev]}")
            print(f"    {c('Severity:', BOLD)}  {', '.join(parts)}")

            print(f"    {c('Top rules:', BOLD)}")
            top = sorted(rule_counts.items(), key=lambda x: x[1], reverse=True)[:6]
            for rule, cnt in top:
                print(f"      {cnt:>5}x  {rule}")

    elif tool_name == "scan_hybrid":
        status = data.get("status", "?")
        total = data.get("total_findings", "?")
        by_sev = data.get("by_severity", {})
        by_source = data.get("by_source", {})
        outdir = data.get("output_dir", "")
        print(f"    {c('Status:', BOLD)}    {c(status, GREEN)}")
        print(f"    {c('Findings:', BOLD)}  {total}")
        if by_sev:
            parts = []
            for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
                if sev in by_sev:
                    color = {"CRITICAL": RED, "HIGH": RED, "MEDIUM": YELLOW, "LOW": CYAN}.get(sev, DIM)
                    parts.append(f"{c(sev, color)}: {by_sev[sev]}")
            print(f"    {c('Severity:', BOLD)}  {', '.join(parts)}")
        if by_source:
            print(f"    {c('Sources:', BOLD)}   {', '.join(f'{k} ({v})' for k, v in by_source.items())}")
        if outdir:
            print(f"    {c('Output:', BOLD)}    {outdir}")

    else:
        keys = list(data.keys())
        print(f"    {c('Response keys:', DIM)} {keys}")


# ---------------------------------------------------------------------------
# Mode: interact
# ---------------------------------------------------------------------------

async def mode_interact(url: str, repo_path: str | None = None):
    """Interactive REPL for calling MCP tools."""
    repo_path = repo_path or _detect_repo_path()

    print(f"\n{c('Agent Smith MCP Interactive Client', BOLD)}")
    print(f"{'=' * 60}")
    print(f"  Server: {c(url, CYAN)}")
    print()

    try:
        ctx, session = await connect(url)
    except ConnectionError as e:
        print(f"{c('ERROR', RED)}: {e}")
        return False

    spinner = Spinner()

    try:
        tools_result = await session.list_tools()
        tools = {t.name: t for t in tools_result.tools}

        print(f"{c('Connected', GREEN)} - {len(tools)} tools available")
        print(f"Type a tool name to call it, 'help' for commands, 'quit' to exit.")
        print()

        last_result = None

        while True:
            try:
                line = input(f"{c('mcp', MAGENTA)}> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            if not line:
                continue

            if line in ("quit", "exit", "q"):
                break

            if line == "help":
                print(f"  {c('Commands:', BOLD)}")
                print(f"    help                  Show this help")
                print(f"    tools                 List available tools")
                print(f"    <tool_name>           Call a tool (prompts for args)")
                print(f"    <tool_name> {{json}}    Call with inline JSON args")
                print(f"    last                  Show last result (full JSON)")
                print(f"    quit                  Exit")
                print()
                continue

            if line == "tools":
                for name, t in tools.items():
                    desc = t.description[:55] + "..." if len(t.description) > 55 else t.description
                    print(f"  {c(name, CYAN):>30}  {desc}")
                print()
                continue

            if line == "last":
                if last_result is not None:
                    print(json.dumps(last_result, indent=2, default=str))
                else:
                    print(f"  {c('No previous result', DIM)}")
                print()
                continue

            # Parse tool name and optional inline JSON args
            parts = line.split(None, 1)
            tool_name = parts[0]
            inline_args = parts[1] if len(parts) > 1 else None

            if tool_name not in tools:
                print(f"  {c('Unknown tool', RED)}: {tool_name}")
                print(f"  Type 'tools' to see available tools")
                print()
                continue

            # Build arguments
            tool = tools[tool_name]
            if inline_args:
                try:
                    args = json.loads(inline_args)
                except json.JSONDecodeError:
                    print(f"  {c('Invalid JSON', RED)}: {inline_args}")
                    continue
            else:
                args = _prompt_for_args(tool, repo_path)

            print(f"  {c('Calling', DIM)}: {tool_name}")
            spinner.start(f"Running {tool_name}...")
            t0 = time.monotonic()
            try:
                result = await session.call_tool(tool_name, args)
                elapsed_ms = (time.monotonic() - t0) * 1000
                spinner.stop()
                text = result.content[0].text
                data = json.loads(text)
                last_result = data

                if "error" in data:
                    print(f"  {c('Error', YELLOW)}: {data['error']}")
                else:
                    _print_result_detail(tool_name, data)
                print(f"  {c(f'({elapsed_ms:.0f}ms)', DIM)}")

            except Exception as e:
                spinner.stop()
                print(f"  {c('FAIL', RED)}: {type(e).__name__}: {e}")

            print()

    finally:
        await session.__aexit__(None, None, None)
        await ctx.__aexit__(None, None, None)

    return True


def _prompt_for_args(tool, default_repo: str | None) -> dict:
    """Prompt user for tool arguments based on the schema."""
    schema = tool.inputSchema or {}
    props = schema.get("properties", {})
    required = set(schema.get("required", []))
    args = {}

    for name, prop in props.items():
        ptype = prop.get("type", "string")
        desc = prop.get("description", "")
        enum_vals = prop.get("enum")
        default = prop.get("default")

        if name == "repo_path" and default_repo:
            default = default_repo

        hint = f" [{default}]" if default else ""
        req_mark = c("*", RED) if name in required else " "
        if enum_vals:
            hint = f" ({'/'.join(enum_vals)}){hint}"

        try:
            val = input(f"    {req_mark}{c(name, CYAN)}{hint}: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return args

        if not val and default is not None:
            val = str(default)
        if not val:
            continue

        if ptype == "integer":
            val = int(val)
        elif ptype == "boolean":
            val = val.lower() in ("true", "1", "yes")

        args[name] = val

    return args


# ---------------------------------------------------------------------------
# Mode: list
# ---------------------------------------------------------------------------

async def mode_list(url: str):
    """List all tools with full schemas."""
    print(f"\n{c('Agent Smith MCP Tools', BOLD)}")
    print(f"{'=' * 60}")

    try:
        ctx, session = await connect(url)
    except ConnectionError as e:
        print(f"{c('ERROR', RED)}: {e}")
        return False

    try:
        tools_result = await session.list_tools()
        for t in tools_result.tools:
            print(f"\n{c(t.name, CYAN)}")
            print(f"  {t.description}")
            schema = t.inputSchema or {}
            props = schema.get("properties", {})
            required = set(schema.get("required", []))
            if props:
                print(f"  {c('Parameters:', DIM)}")
                for name, prop in props.items():
                    req = c("required", RED) if name in required else c("optional", DIM)
                    ptype = prop.get("type", "string")
                    desc = prop.get("description", "")[:60]
                    enum_vals = prop.get("enum")
                    default = prop.get("default")
                    parts = [f"{ptype}", req]
                    if enum_vals:
                        parts.append(f"enum: {enum_vals}")
                    if default is not None:
                        parts.append(f"default: {default}")
                    print(f"    {c(name, WHITE):>25}: {', '.join(parts)}")
                    if desc:
                        print(f"    {'':>25}  {c(desc, DIM)}")
            else:
                print(f"  {c('No parameters', DIM)}")
        print()

    finally:
        await session.__aexit__(None, None, None)
        await ctx.__aexit__(None, None, None)

    return True


# ---------------------------------------------------------------------------
# Mode: benchmark
# ---------------------------------------------------------------------------

async def mode_benchmark(url: str, repo_path: str | None = None, iterations: int = 3):
    """Benchmark tool latency."""
    repo_path = repo_path or _detect_repo_path()

    print(f"\n{c('Agent Smith MCP Benchmark', BOLD)}")
    print(f"{'=' * 60}")
    print(f"  Server:     {c(url, CYAN)}")
    print(f"  Iterations: {iterations}")
    print()

    try:
        ctx, session = await connect(url)
    except ConnectionError as e:
        print(f"{c('ERROR', RED)}: {e}")
        return False

    try:
        bench_tools = [
            ("list_presets", {}),
            ("summarize_results", {}),
            ("list_findings", {"severity": "CRITICAL", "limit": 10}),
        ]
        if repo_path:
            bench_tools.extend([
                ("detect_tech_stack", {"repo_path": repo_path}),
                ("scan_static", {"repo_path": repo_path, "severity": "HIGH"}),
            ])

        print(f"  {'Tool':<25} {'Min':>8} {'Avg':>8} {'Max':>8} {'Status':>8}")
        print(f"  {'-' * 25} {'-' * 8} {'-' * 8} {'-' * 8} {'-' * 8}")

        for tool_name, args in bench_tools:
            times = []
            errors = 0
            for _ in range(iterations):
                t0 = time.monotonic()
                try:
                    result = await session.call_tool(tool_name, args)
                    elapsed = (time.monotonic() - t0) * 1000
                    text = result.content[0].text
                    data = json.loads(text)
                    if "error" in data:
                        errors += 1
                    times.append(elapsed)
                except Exception:
                    errors += 1
                    times.append((time.monotonic() - t0) * 1000)

            if times:
                min_t = min(times)
                avg_t = sum(times) / len(times)
                max_t = max(times)
                status = c("OK", GREEN) if errors == 0 else c(f"{errors}err", YELLOW)
                print(f"  {tool_name:<25} {min_t:>7.0f}ms {avg_t:>7.0f}ms {max_t:>7.0f}ms {status:>8}")

        print()

    finally:
        await session.__aexit__(None, None, None)
        await ctx.__aexit__(None, None, None)

    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Agent Smith MCP Test Client",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "mode", nargs="?", default="test",
        choices=["test", "interact", "list", "benchmark"],
        help="Client mode (default: test)",
    )
    parser.add_argument("--url", default="http://localhost:2266/sse",
                        help="MCP server SSE URL (default: http://localhost:2266/sse)")
    parser.add_argument("--tool", type=str, help="Test a specific tool only")
    parser.add_argument("--repo", type=str, help="Repository path for scanning tools")
    parser.add_argument("--all", action="store_true", help="Include slow tools (scan_hybrid)")
    parser.add_argument("--json", action="store_true", help="JSON output (for CI/CD)")
    parser.add_argument("--quiet", "-q", action="store_true", help="Minimal output (pass/fail only)")
    parser.add_argument("--no-color", action="store_true", help="Disable color output")
    parser.add_argument("--iterations", type=int, default=3, help="Benchmark iterations (default: 3)")
    args = parser.parse_args()

    global _no_color
    _no_color = args.no_color or args.json

    if args.mode == "test":
        ok = asyncio.run(mode_test(
            args.url, args.tool, args.all, args.repo, args.json, args.quiet
        ))
    elif args.mode == "interact":
        ok = asyncio.run(mode_interact(args.url, args.repo))
    elif args.mode == "list":
        ok = asyncio.run(mode_list(args.url))
    elif args.mode == "benchmark":
        ok = asyncio.run(mode_benchmark(args.url, args.repo, args.iterations))
    else:
        ok = False

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
