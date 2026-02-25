"""Rug pull and protocol robustness checks."""

import time

from mcp_attack.core.models import TargetResult
from mcp_attack.core.constants import MCP_INIT_PARAMS
from mcp_attack.checks.base import time_check


def check_rug_pull(session, result: TargetResult):
    with time_check("rug_pull", result):
        first = session.call("tools/list", timeout=15)
        time.sleep(2)
        second = session.call("tools/list", timeout=15)

        if not first or not second:
            return

        t1 = {t["name"]: t for t in first.get("result", {}).get("tools", [])}
        t2 = {
            t["name"]: t for t in second.get("result", {}).get("tools", [])
        }

        added = set(t2) - set(t1)
        removed = set(t1) - set(t2)

        if added:
            result.add(
                "rug_pull",
                "HIGH",
                f"Rug pull: {len(added)} tool(s) appeared after initial listing",
                f"New: {sorted(added)}",
            )
        if removed:
            result.add(
                "rug_pull",
                "HIGH",
                f"Rug pull: {len(removed)} tool(s) disappeared",
                f"Removed: {sorted(removed)}",
            )

        for name in set(t1) & set(t2):
            if t1[name].get("description") != t2[name].get("description"):
                result.add(
                    "rug_pull",
                    "CRITICAL",
                    f"Rug pull: tool '{name}' description changed between calls",
                    f"Before: {t1[name].get('description','')[:150]}\n"
                    f"After:  {t2[name].get('description','')[:150]}",
                )


def check_protocol_robustness(session, result: TargetResult):
    with time_check("protocol_robustness", result):
        resp = session.call("nonexistent/method/xyz", timeout=8)
        if resp and "error" not in resp:
            result.add(
                "protocol_robustness",
                "MEDIUM",
                "Server returned success for unknown JSON-RPC method",
                "Should return -32601 Method Not Found",
            )
        resp = session.call("tools/call", timeout=8)
        if resp and "result" in resp:
            result.add(
                "protocol_robustness",
                "MEDIUM",
                "Server returned result for tools/call with no params",
            )
