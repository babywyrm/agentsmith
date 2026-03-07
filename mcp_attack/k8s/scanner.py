"""Kubernetes RBAC, Helm secrets, and pod security scanning."""

import base64
import gzip
import json
import os
from typing import Any

from mcp_attack.core.models import Finding, TargetResult

GLOBAL_K8S_FINDINGS: list[Finding] = []

_SENSITIVE_VALUE_PATTERNS = ["password", "secret", "token", "apikey", "api_key",
                             "private_key", "privatekey", "credential", "passphrase"]

_DANGEROUS_CAPABILITIES = {"NET_RAW", "SYS_ADMIN", "SYS_PTRACE", "NET_ADMIN",
                           "SYS_MODULE", "DAC_OVERRIDE", "SETUID", "SETGID"}


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
                elif any(s in k.lower() for s in _SENSITIVE_VALUE_PATTERNS):
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


def _check_pod_security(pod: dict, namespace: str):
    """Analyze a pod spec for security misconfigurations."""
    meta = pod.get("metadata", {})
    pod_name = meta.get("name", "?")
    spec = pod.get("spec", {})

    if spec.get("hostNetwork"):
        GLOBAL_K8S_FINDINGS.append(Finding(
            target="k8s", check="pod_security", severity="HIGH",
            title=f"Pod {pod_name} uses hostNetwork",
            detail="Host networking bypasses network policies and exposes host interfaces",
        ))

    if spec.get("hostPID"):
        GLOBAL_K8S_FINDINGS.append(Finding(
            target="k8s", check="pod_security", severity="HIGH",
            title=f"Pod {pod_name} uses hostPID",
            detail="Host PID namespace allows process inspection and ptrace attacks",
        ))

    for c in spec.get("containers", []) + spec.get("initContainers", []):
        cname = c.get("name", "?")
        sc = c.get("securityContext", {})

        if sc.get("privileged"):
            GLOBAL_K8S_FINDINGS.append(Finding(
                target="k8s", check="pod_security", severity="CRITICAL",
                title=f"Privileged container: {pod_name}/{cname}",
                detail="Privileged containers have full host access",
            ))

        if sc.get("runAsUser") == 0 or sc.get("runAsGroup") == 0:
            GLOBAL_K8S_FINDINGS.append(Finding(
                target="k8s", check="pod_security", severity="MEDIUM",
                title=f"Container runs as root: {pod_name}/{cname}",
            ))

        caps = sc.get("capabilities", {})
        added = set(caps.get("add", []))
        dangerous = added & _DANGEROUS_CAPABILITIES
        if dangerous:
            GLOBAL_K8S_FINDINGS.append(Finding(
                target="k8s", check="pod_security", severity="HIGH",
                title=f"Dangerous capabilities on {pod_name}/{cname}: {dangerous}",
            ))

        for vm in c.get("volumeMounts", []):
            if vm.get("mountPath", "").startswith("/var/run/secrets"):
                continue
            mount_name = vm.get("name", "")
            for vol in spec.get("volumes", []):
                if vol.get("name") == mount_name and vol.get("hostPath"):
                    hp = vol["hostPath"].get("path", "")
                    GLOBAL_K8S_FINDINGS.append(Finding(
                        target="k8s", check="pod_security", severity="HIGH",
                        title=f"hostPath mount on {pod_name}/{cname}: {hp}",
                        detail=f"Volume {mount_name} mounts host path {hp}",
                    ))

        resources = c.get("resources", {})
        if not resources.get("limits"):
            GLOBAL_K8S_FINDINGS.append(Finding(
                target="k8s", check="pod_security", severity="LOW",
                title=f"No resource limits on {pod_name}/{cname}",
                detail="Missing limits can lead to resource exhaustion",
            ))


def _check_configmap_leaks(cm: dict, namespace: str):
    """Scan ConfigMap data for leaked secrets."""
    name = cm.get("metadata", {}).get("name", "?")
    for key, value in cm.get("data", {}).items():
        if not isinstance(value, str):
            continue
        if "PRIVATE KEY" in value:
            GLOBAL_K8S_FINDINGS.append(Finding(
                target="k8s", check="configmap_secrets", severity="CRITICAL",
                title=f"Private key in ConfigMap: {name}/{key}",
            ))
        if any(s in key.lower() for s in _SENSITIVE_VALUE_PATTERNS):
            GLOBAL_K8S_FINDINGS.append(Finding(
                target="k8s", check="configmap_secrets", severity="MEDIUM",
                title=f"Possible credential in ConfigMap: {name}/{key}",
            ))


def _check_network_policies(namespace: str, token: str):
    """Check if network policies exist in the namespace."""
    data = _k8s_get(
        f"/apis/networking.k8s.io/v1/namespaces/{namespace}/networkpolicies",
        token,
    )
    if data is None:
        return
    policies = data.get("items", [])
    if not policies:
        GLOBAL_K8S_FINDINGS.append(Finding(
            target="k8s", check="network_policy", severity="MEDIUM",
            title=f"No NetworkPolicies in namespace {namespace}",
            detail="All pod-to-pod traffic is unrestricted without network policies",
        ))
    else:
        GLOBAL_K8S_FINDINGS.append(Finding(
            target="k8s", check="network_policy", severity="INFO",
            title=f"{len(policies)} NetworkPolicy(ies) in {namespace}",
        ))


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

    # RBAC enumeration
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
            if console:
                tag = "[red]!" if name == "secrets" else "[dim]*"
                console.print(f"  {tag}[/] SA can list {name}: {count} items")

    # Helm release secret scanning
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

    # Pod security checks
    pods_data = _k8s_get(f"/api/v1/namespaces/{namespace}/pods", token)
    if pods_data:
        for pod in pods_data.get("items", []):
            _check_pod_security(pod, namespace)

    # ConfigMap leak scanning
    cm_data = _k8s_get(f"/api/v1/namespaces/{namespace}/configmaps", token)
    if cm_data:
        for cm in cm_data.get("items", []):
            _check_configmap_leaks(cm, namespace)

    # Network policy checks
    _check_network_policies(namespace, token)

    if console:
        sev_counts = {}
        for f in GLOBAL_K8S_FINDINGS:
            sev_counts[f.severity] = sev_counts.get(f.severity, 0) + 1
        console.print(f"  [bold]K8s findings: {len(GLOBAL_K8S_FINDINGS)}[/bold] "
                      f"({', '.join(f'{s}={c}' for s, c in sorted(sev_counts.items()))})")
