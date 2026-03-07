"""Kubernetes internal checks and MCP service discovery."""

from mcp_attack.k8s.scanner import run_k8s_checks
from mcp_attack.k8s.discovery import discover_services, DiscoveredEndpoint

__all__ = ["run_k8s_checks", "discover_services", "DiscoveredEndpoint"]
