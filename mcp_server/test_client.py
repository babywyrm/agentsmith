#!/usr/bin/env python3
"""
Agent Smith MCP Test Client

Connects to the MCP server over SSE and exercises all available tools.

Usage:
    python3 -m mcp_server.test_client                          # default localhost:2266
    python3 -m mcp_server.test_client --url http://host:port/sse
    python3 -m mcp_server.test_client --tool scan_static       # run one tool
    python3 -m mcp_server.test_client --list                   # just list tools
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Colors
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[0;32m"
RED = "\033[0;31m"
YELLOW = "\033[0;33m"
CYAN = "\033[0;36m"
RESET = "\033[0m"


def c(text, color):
    return f"{color}{text}{RESET}"


async def run_tests(url: str, tool_filter: str | None = None, list_only: bool = False,
                    repo_path: str | None = None):
    from mcp.client.sse import sse_client
    from mcp import ClientSession

    print(f"\n{c('Agent Smith MCP Test Client', BOLD)}")
    print(f"{'=' * 50}")
    print(f"  Server: {c(url, CYAN)}")
    print()

    # Connect
    print(f"{c('Connecting...', DIM)}")
    try:
        async with sse_client(url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print(f"{c('Connected', GREEN)}")
                print()

                # List tools
                tools_result = await session.list_tools()
                tools = tools_result.tools
                print(f"{c('Available Tools', BOLD)} ({len(tools)})")
                print(f"{'-' * 50}")
                for t in tools:
                    desc = t.description[:70] + "..." if len(t.description) > 70 else t.description
                    print(f"  {c(t.name, CYAN):>35}  {desc}")
                print()

                if list_only:
                    return True

                # Determine which tools to test
                test_tools = []
                if tool_filter:
                    matching = [t for t in tools if t.name == tool_filter]
                    if not matching:
                        print(f"{c('Error', RED)}: Tool '{tool_filter}' not found")
                        return False
                    test_tools = [tool_filter]
                else:
                    # Run safe, non-destructive tools by default
                    test_tools = ["list_presets", "summarize_results", "list_findings",
                                  "detect_tech_stack", "scan_static"]

                # Auto-detect a repo path for tools that need one
                if not repo_path:
                    project_root = Path(__file__).resolve().parent.parent
                    candidates = [
                        project_root / "tests" / "test_targets" / "DVWA",
                        project_root / "tests" / "test_targets" / "WebGoat",
                        project_root / "tests" / "test_targets" / "juice-shop",
                        project_root,
                    ]
                    for candidate in candidates:
                        if candidate.is_dir():
                            repo_path = str(candidate)
                            break

                # Test arguments for each tool
                tool_args = {
                    "list_presets": {},
                    "summarize_results": {},
                    "list_findings": {"severity": "CRITICAL", "limit": 5},
                    "detect_tech_stack": {"repo_path": repo_path},
                    "scan_static": {"repo_path": repo_path, "severity": "HIGH"},
                    "scan_hybrid": {"repo_path": repo_path, "preset": "quick"},
                }

                passed = 0
                failed = 0

                for tool_name in test_tools:
                    if tool_name not in [t.name for t in tools]:
                        continue

                    args = tool_args.get(tool_name, {})
                    print(f"{c('Testing', BOLD)}: {c(tool_name, CYAN)}")
                    if args:
                        print(f"  {c('args', DIM)}: {json.dumps(args, default=str)}")

                    try:
                        result = await session.call_tool(tool_name, args)
                        text = result.content[0].text
                        data = json.loads(text)

                        # Check for errors in response
                        if "error" in data:
                            print(f"  {c('WARN', YELLOW)}: {data['error']}")
                            # Not a failure if it's a "no results" type error
                            if "not found" in data["error"].lower() or "no scan" in data["error"].lower():
                                print(f"  {c('(expected - no prior scan data)', DIM)}")
                                passed += 1
                            else:
                                failed += 1
                        else:
                            # Print a useful summary of the result
                            _print_result_summary(tool_name, data)
                            passed += 1

                    except Exception as e:
                        print(f"  {c('FAIL', RED)}: {type(e).__name__}: {e}")
                        failed += 1

                    print()

                # Summary
                print(f"{c('Results', BOLD)}")
                print(f"{'=' * 50}")
                total = passed + failed
                print(f"  Passed: {c(str(passed), GREEN)}")
                if failed:
                    print(f"  Failed: {c(str(failed), RED)}")
                print(f"  Total:  {total}")
                print()

                return failed == 0

    except ConnectionRefusedError:
        print(f"{c('Error', RED)}: Cannot connect to {url}")
        print(f"  Make sure the server is running: python3 -m mcp_server --no-auth")
        return False
    except Exception as e:
        print(f"{c('Error', RED)}: {type(e).__name__}: {e}")
        return False


def _print_result_summary(tool_name: str, data: dict):
    """Print a concise summary of tool results."""
    if tool_name == "list_presets":
        count = data.get("count", 0)
        names = [p["name"] for p in data.get("presets", [])]
        print(f"  {c('OK', GREEN)}: {count} presets: {', '.join(names)}")

    elif tool_name == "summarize_results":
        combined = data.get("combined", {})
        cost = data.get("cost", {})
        print(f"  {c('OK', GREEN)}: {combined.get('count', '?')} findings, "
              f"${cost.get('cost_usd', 0):.3f} cost")
        by_sev = combined.get("by_severity", {})
        if by_sev:
            parts = [f"{k}: {v}" for k, v in by_sev.items()]
            print(f"  {c('severity', DIM)}: {', '.join(parts)}")

    elif tool_name == "list_findings":
        returned = data.get("returned", 0)
        total = data.get("total_matched", 0)
        print(f"  {c('OK', GREEN)}: {returned} returned of {total} matched")
        for f in data.get("findings", [])[:3]:
            print(f"    [{f.get('severity')}] {f.get('title', '?')[:50]}")

    elif tool_name == "detect_tech_stack":
        langs = data.get("languages", [])
        if isinstance(langs, dict):
            langs = list(langs.keys())
        fws = data.get("frameworks", {})
        if isinstance(fws, dict):
            fws = list(fws.keys())[:5]
        print(f"  {c('OK', GREEN)}: languages={langs}, frameworks={fws}")

    elif tool_name == "scan_static":
        count = data.get("count", 0)
        rules = data.get("rules_loaded", 0)
        print(f"  {c('OK', GREEN)}: {count} findings from {rules} rule files")

    elif tool_name == "scan_hybrid":
        status = data.get("status", "?")
        total = data.get("total_findings", "?")
        print(f"  {c('OK', GREEN)}: status={status}, findings={total}")

    else:
        # Generic: show keys and sizes
        keys = list(data.keys())
        print(f"  {c('OK', GREEN)}: keys={keys}")


def main():
    parser = argparse.ArgumentParser(description="Agent Smith MCP Test Client")
    parser.add_argument(
        "--url", default="http://localhost:2266/sse",
        help="MCP server SSE URL (default: http://localhost:2266/sse)",
    )
    parser.add_argument(
        "--tool", type=str, default=None,
        help="Test a specific tool only",
    )
    parser.add_argument(
        "--list", action="store_true", dest="list_only",
        help="Just list available tools",
    )
    parser.add_argument(
        "--repo", type=str, default=None,
        help="Repository path for scanning tools (auto-detected if not set)",
    )
    args = parser.parse_args()

    ok = asyncio.run(run_tests(args.url, args.tool, args.list_only, args.repo))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
