"""Kubernetes RBAC and Helm secrets scanning."""

import base64
import gzip
import json
import os
from typing import Any

from mcp_attack.core.models import Finding, TargetResult

GLOBAL_K8S_FINDINGS: list[Finding] = []


def _k8s_get(path: str, token: str) -> dict | None:
    import ssl
    import urllib.request

    req = urllib.request.Request(
        f"https://kubernetes.default{path}",
        headers={"Authorization": f"Bearer {token}"},
    )
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
            return json.loads(r.read())
    except Exception:
        return None


def _scan_helm(sname: str, obj: Any, path: str):
    if isinstance(obj, dict):
        for k, v in obj.items():
            np = f"{path}.{k}" if path else k
            if isinstance(v, str):
                if "PRIVATE KEY" in v:
                    GLOBAL_K8S_FINDINGS.append(
                        Finding(
                            target="k8s",
                            check="helm_secrets",
                            severity="CRITICAL",
                            title=f"Private key in Helm values: {sname} → {np}",
                        )
                    )
                elif any(
                    s in k.lower()
                    for s in ["password", "secret", "token", "apikey"]
                ):
                    GLOBAL_K8S_FINDINGS.append(
                        Finding(
                            target="k8s",
                            check="helm_secrets",
                            severity="HIGH",
                            title=f"Credential in Helm values: {sname} → {np}",
                        )
                    )
            else:
                _scan_helm(sname, v, np)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            _scan_helm(sname, item, f"{path}[{i}]")


def run_k8s_checks(namespace: str, console=None):
    """Run K8s internal checks (requires running inside a pod)."""
    token_path = "/var/run/secrets/kubernetes.io/serviceaccount/token"
    if not os.path.exists(token_path):
        if console:
            console.print("[dim]  No SA token — skipping K8s checks[/dim]")
        return

    with open(token_path) as f:
        token = f.read().strip()

    if console:
        console.print(f"\n[bold]── K8s Internal Checks (ns={namespace}) ──[/bold]")

    for name, path in [
        ("secrets", f"/api/v1/namespaces/{namespace}/secrets"),
        ("configmaps", f"/api/v1/namespaces/{namespace}/configmaps"),
        ("pods", f"/api/v1/namespaces/{namespace}/pods"),
    ]:
        data = _k8s_get(path, token)
        if data:
            count = len(data.get("items", []))
            sev = "HIGH" if name == "secrets" else "INFO"
            GLOBAL_K8S_FINDINGS.append(
                Finding(
                    target="k8s",
                    check="rbac",
                    severity=sev,
                    title=f"SA can read {name} ({count} items) in {namespace}",
                )
            )

    secrets_data = _k8s_get(
        f"/api/v1/namespaces/{namespace}/secrets", token
    )
    if secrets_data:
        for secret in secrets_data.get("items", []):
            if secret.get("type") != "helm.sh/release.v1":
                continue
            sname = secret["metadata"]["name"]
            b64 = secret.get("data", {}).get("release", "")
            if not b64:
                continue
            try:
                decoded = gzip.decompress(
                    base64.b64decode(base64.b64decode(b64))
                )
                _scan_helm(
                    sname,
                    json.loads(decoded).get("chart", {}).get("values", {}),
                    "",
                )
            except Exception:
                pass
