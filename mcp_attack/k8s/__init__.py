"""Kubernetes internal checks (runs inside a pod)."""

from mcp_attack.k8s.scanner import run_k8s_checks

__all__ = ["run_k8s_checks"]
