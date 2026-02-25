"""
mcp_attack — MCP Red Teaming / Security Scanner

Standalone module for MCP server security auditing. Not yet integrated
into the main Agent Smith codebase. Use with DVMCP or any MCP server.

Usage:
    python -m mcp_attack --targets http://localhost:2266
    python -m mcp_attack --port-range localhost:9001-9010 --verbose
"""

__version__ = "4.1"
