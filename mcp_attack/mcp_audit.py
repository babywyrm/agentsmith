#!/usr/bin/env python3
"""
mcp-audit — MCP Red Teaming / Security Scanner

Run from anywhere:
    python3 mcp_audit.py --targets http://localhost:2266
    python3 mcp_audit.py --port-range localhost:9001-9010 --verbose

From project root:
    python3 mcp_attack/mcp_audit.py --targets http://localhost:2266
    python3 -m mcp_attack --targets http://localhost:2266

Requires: pip install httpx rich (or use project venv: source .venv/bin/activate)
"""

import sys
from pathlib import Path

# Ensure parent (agentsmith) is on path so mcp_attack can be imported
_here = Path(__file__).resolve().parent
_parent = _here.parent
if str(_parent) not in sys.path:
    sys.path.insert(0, str(_parent))

from mcp_attack.__main__ import main

if __name__ == "__main__":
    main()
