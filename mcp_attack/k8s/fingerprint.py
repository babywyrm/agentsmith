"""Internal service fingerprinting for non-MCP endpoints.

Probes cluster services to identify frameworks, exposed debug endpoints,
and unauthenticated admin interfaces. Complements MCP-specific discovery
by mapping the broader internal attack surface.
"""

import json
from dataclasses import dataclass

from mcp_attack.core.models import Finding

_ACTUATOR_PATHS = [
    "/actuator", "/actuator/env", "/actuator/health", "/actuator/beans",
    "/actuator/configprops", "/actuator/mappings", "/actuator/info",
]

_DEBUG_PATHS = [
    "/metrics", "/debug/pprof", "/debug/vars",
    "/_cluster/health", "/_cat/indices",
    "/server-info", "/server-status",
    "/.well-known/openid-configuration",
    "/swagger-ui.html", "/swagger-ui/", "/api-docs", "/openapi.json",
    "/graphql", "/graphiql",
    "/console", "/admin", "/dashboard",
]

_FRAMEWORK_SIGNATURES = {
    "Spring Boot": [("X-Application-Context", None), (None, "Whitelabel Error Page")],
    "Express": [("X-Powered-By", "Express")],
    "FastAPI": [(None, '"openapi"'), (None, "FastAPI")],
    "Flask": [("Server", "Werkzeug")],
    "Django": [("X-Frame-Options", "DENY"), (None, "Django")],
    "ASP.NET": [("X-Powered-By", "ASP.NET"), ("X-AspNet-Version", None)],
    "Go net/http": [("Content-Type", "text/plain; charset=utf-8")],
    "Nginx": [("Server", "nginx")],
    "Envoy": [("Server", "envoy"), ("x-envoy-upstream-service-time", None)],
}


@dataclass
class ServiceFingerprint:
    service_name: str
    namespace: str
    port: int
    framework: str = ""
    exposed_paths: list[str] | None = None
    findings: list[Finding] | None = None

    def __post_init__(self):
        if self.exposed_paths is None:
            self.exposed_paths = []
        if self.findings is None:
            self.findings = []


def _http_probe(url: str, timeout: float = 3.0) -> tuple[int, dict, str]:
    """Quick HTTP GET, returns (status, headers_dict, body_snippet)."""
    import httpx
    try:
        with httpx.Client(verify=False, timeout=timeout, follow_redirects=True) as c:
            r = c.get(url)
            headers = dict(r.headers)
            body = r.text[:2048]
            return r.status_code, headers, body
    except Exception:
        return 0, {}, ""


def _detect_framework(headers: dict, body: str) -> str:
    """Match response against known framework signatures."""
    for framework, sigs in _FRAMEWORK_SIGNATURES.items():
        for header_key, match_val in sigs:
            if header_key and header_key.lower() in {k.lower() for k in headers}:
                if match_val is None:
                    return framework
                actual = headers.get(header_key, "")
                for k, v in headers.items():
                    if k.lower() == header_key.lower():
                        actual = v
                        break
                if match_val.lower() in actual.lower():
                    return framework
            if header_key is None and match_val and match_val.lower() in body.lower():
                return framework
    return ""


def fingerprint_services(
    namespace: str,
    token: str,
    console=None,
) -> list[ServiceFingerprint]:
    """Fingerprint all services in a namespace for frameworks and exposed endpoints."""
    from mcp_attack.k8s.scanner import _k8s_get, GLOBAL_K8S_FINDINGS

    svc_data = _k8s_get(f"/api/v1/namespaces/{namespace}/services", token)
    if not svc_data:
        return []

    results: list[ServiceFingerprint] = []

    if console:
        console.print(f"\n[bold]── Service Fingerprinting (ns={namespace}) ──[/bold]")

    for svc in svc_data.get("items", []):
        name = svc.get("metadata", {}).get("name", "")
        spec = svc.get("spec", {})
        cluster_ip = spec.get("clusterIP", "")
        if not cluster_ip or cluster_ip == "None":
            continue

        for sp in spec.get("ports", []):
            port = sp.get("port", 0)
            if not port:
                continue

            dns = f"{name}.{namespace}"
            base_url = f"http://{dns}:{port}"

            status, headers, body = _http_probe(base_url)
            if status == 0:
                continue

            fp = ServiceFingerprint(
                service_name=name, namespace=namespace, port=port,
            )

            fp.framework = _detect_framework(headers, body)
            if fp.framework and console:
                console.print(f"  [cyan]•[/] {dns}:{port} → {fp.framework}")

            sensitive_paths = _ACTUATOR_PATHS + _DEBUG_PATHS
            for path in sensitive_paths:
                url = f"{base_url}{path}"
                s, h, b = _http_probe(url, timeout=2.0)
                if s in (200, 301, 302) and len(b) > 10:
                    fp.exposed_paths.append(path)

            if fp.exposed_paths:
                actuator_exposed = [p for p in fp.exposed_paths if "actuator" in p]
                debug_exposed = [p for p in fp.exposed_paths if p not in actuator_exposed]

                if actuator_exposed:
                    sev = "HIGH" if any(p in ("/actuator/env", "/actuator/configprops") for p in actuator_exposed) else "MEDIUM"
                    finding = Finding(
                        target="k8s", check="service_fingerprint", severity=sev,
                        title=f"Spring Actuator exposed on {dns}:{port}",
                        detail=f"Paths: {', '.join(actuator_exposed[:8])}",
                    )
                    fp.findings.append(finding)
                    GLOBAL_K8S_FINDINGS.append(finding)

                if any(p in ("/debug/pprof", "/debug/vars") for p in debug_exposed):
                    finding = Finding(
                        target="k8s", check="service_fingerprint", severity="MEDIUM",
                        title=f"Debug profiling endpoint on {dns}:{port}",
                        detail=f"Paths: {', '.join(p for p in debug_exposed if 'debug' in p)}",
                    )
                    fp.findings.append(finding)
                    GLOBAL_K8S_FINDINGS.append(finding)

                if any(p in ("/swagger-ui.html", "/swagger-ui/", "/api-docs",
                             "/openapi.json", "/graphiql") for p in debug_exposed):
                    finding = Finding(
                        target="k8s", check="service_fingerprint", severity="LOW",
                        title=f"API documentation exposed on {dns}:{port}",
                        detail=f"Paths: {', '.join(p for p in debug_exposed if any(s in p for s in ('swagger', 'api-doc', 'openapi', 'graphi')))}",
                    )
                    fp.findings.append(finding)
                    GLOBAL_K8S_FINDINGS.append(finding)

                if console:
                    for f in fp.findings:
                        from mcp_attack.core.constants import SEV_COLOR
                        color = SEV_COLOR.get(f.severity, "dim")
                        console.print(f"    [{color}]{f.severity}[/] {f.title}")

            results.append(fp)

    if console:
        console.print(f"  [bold]Fingerprinted {len(results)} service(s)[/bold]")

    return results
