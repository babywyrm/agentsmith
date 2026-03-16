"""
mcp_attack — MCP Red Teaming / Security Scanner

DEPRECATED: This module is being replaced by mcpvenom
(https://github.com/babywyrm/mcpvenom), which has expanded coverage,
Claude AI analysis, OIDC auth, and more. This module remains for
backward compatibility. A future release will replace it with a
git submodule pointing to mcpvenom.

Usage:
    python -m mcp_attack --targets http://localhost:2266
    python -m mcp_attack --port-range localhost:9001-9010 --verbose
"""

__version__ = "4.1"
