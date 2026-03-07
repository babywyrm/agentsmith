"""Kubernetes MCP service discovery.

Auto-discovers MCP endpoints inside a cluster by scanning:
  1. Service annotations (mcp.io/enabled, mcp.io/transport, mcp.io/path)
  2. Well-known MCP ports (configurable)
  3. Endpoint health probes on common MCP paths (/sse, /mcp, /messages)

Requires a service account with `get`/`list` permissions on services
and optionally endpoints in the target namespace(s).
"""

import json
import os
import ssl
import urllib.request
from dataclasses import dataclass, field

MCP_ANNOTATION_ENABLED = "mcp.io/enabled"
MCP_ANNOTATION_TRANSPORT = "mcp.io/transport"
MCP_ANNOTATION_PATH = "mcp.io/path"
MCP_ANNOTATION_PORT = "mcp.io/port"

DEFAULT_MCP_PORTS = {2266, 3000, 5000, 8080, 8443, 9090}

PROBE_PATHS = ["/sse", "/mcp", "/messages", "/v1/sse", "/rpc", "/jsonrpc", ""]

SA_TOKEN_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/token"
SA_NS_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/namespace"
K8S_API = "https://kubernetes.default"


@dataclass
class DiscoveredEndpoint:
    url: str
    service_name: str
    namespace: str
    port: int
    transport_hint: str = ""
    path_hint: str = ""
    source: str = ""


def _k8s_api(path: str, token: str) -> dict | None:
    req = urllib.request.Request(
        f"{K8S_API}{path}",
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


def _get_sa_token() -> str | None:
    if not os.path.exists(SA_TOKEN_PATH):
        return None
    with open(SA_TOKEN_PATH) as f:
        return f.read().strip()


def _get_current_namespace() -> str:
    if os.path.exists(SA_NS_PATH):
        with open(SA_NS_PATH) as f:
            return f.read().strip()
    return "default"


def _probe_mcp_endpoint(host: str, port: int, paths: list[str] | None = None) -> str | None:
    """Quick HTTP probe to check if a port speaks MCP. Returns working path or None."""
    import httpx

    for path in (paths or PROBE_PATHS):
        url = f"http://{host}:{port}{path}"
        try:
            with httpx.Client(verify=False, timeout=3.0) as c:
                r = c.post(
                    url,
                    json={"jsonrpc": "2.0", "id": 1, "method": "initialize",
                          "params": {"protocolVersion": "2024-11-05",
                                     "capabilities": {},
                                     "clientInfo": {"name": "k8s-probe", "version": "1.0"}}},
                    headers={"Content-Type": "application/json",
                             "Accept": "application/json, text/event-stream"},
                )
                if r.status_code in (200, 202) and "jsonrpc" in r.text:
                    return path
                if r.status_code in (400, 422) and ("jsonrpc" in r.text or "method" in r.text):
                    return path
        except Exception:
            pass

        try:
            with httpx.Client(verify=False, timeout=3.0) as c:
                with c.stream("GET", url, headers={"Accept": "text/event-stream"}) as resp:
                    if resp.status_code == 200 and "text/event-stream" in resp.headers.get("content-type", ""):
                        return path
        except Exception:
            pass

    return None


def discover_services(
    namespaces: list[str] | None = None,
    probe: bool = True,
    extra_ports: set[int] | None = None,
    console=None,
) -> list[DiscoveredEndpoint]:
    """Discover MCP endpoints in the cluster.

    Args:
        namespaces: Namespaces to scan. None = current namespace only.
        probe: If True, actively probe discovered ports for MCP protocol.
        extra_ports: Additional ports to check beyond the defaults.
        console: Rich console for output (optional).

    Returns:
        List of discovered MCP endpoints.
    """
    token = _get_sa_token()
    if not token:
        if console:
            console.print("[dim]  No SA token -- skipping K8s discovery[/dim]")
        return []

    if namespaces is None:
        namespaces = [_get_current_namespace()]

    check_ports = DEFAULT_MCP_PORTS | (extra_ports or set())
    endpoints: list[DiscoveredEndpoint] = []

    if console:
        console.print(f"\n[bold]── K8s MCP Discovery (ns={','.join(namespaces)}) ──[/bold]")

    for ns in namespaces:
        svc_data = _k8s_api(f"/api/v1/namespaces/{ns}/services", token)
        if not svc_data:
            if console:
                console.print(f"  [red]✗[/red] Cannot list services in {ns}")
            continue

        for svc in svc_data.get("items", []):
            meta = svc.get("metadata", {})
            spec = svc.get("spec", {})
            name = meta.get("name", "")
            annotations = meta.get("annotations", {}) or {}

            is_annotated = annotations.get(MCP_ANNOTATION_ENABLED, "").lower() in ("true", "1", "yes")
            transport_hint = annotations.get(MCP_ANNOTATION_TRANSPORT, "")
            path_hint = annotations.get(MCP_ANNOTATION_PATH, "")
            port_hint = annotations.get(MCP_ANNOTATION_PORT, "")

            cluster_ip = spec.get("clusterIP", "")
            if not cluster_ip or cluster_ip == "None":
                continue

            svc_ports = spec.get("ports", [])

            if is_annotated:
                target_port = int(port_hint) if port_hint else (svc_ports[0]["port"] if svc_ports else 80)
                ep = DiscoveredEndpoint(
                    url=f"http://{name}.{ns}:{target_port}{path_hint}",
                    service_name=name,
                    namespace=ns,
                    port=target_port,
                    transport_hint=transport_hint,
                    path_hint=path_hint,
                    source="annotation",
                )
                endpoints.append(ep)
                if console:
                    console.print(f"  [green]✓[/green] {ep.url} (annotated)")
                continue

            for sp in svc_ports:
                port_num = sp.get("port", 0)
                port_name = sp.get("name", "")
                if port_num in check_ports or "mcp" in port_name.lower():
                    if probe:
                        dns_name = f"{name}.{ns}"
                        working_path = _probe_mcp_endpoint(dns_name, port_num, [path_hint] if path_hint else None)
                        if working_path is not None:
                            ep = DiscoveredEndpoint(
                                url=f"http://{dns_name}:{port_num}{working_path}",
                                service_name=name,
                                namespace=ns,
                                port=port_num,
                                path_hint=working_path,
                                source="probe",
                            )
                            endpoints.append(ep)
                            if console:
                                console.print(f"  [green]✓[/green] {ep.url} (probed)")
                        elif console:
                            console.print(f"  [dim]  {dns_name}:{port_num} -- not MCP[/dim]")
                    else:
                        ep = DiscoveredEndpoint(
                            url=f"http://{name}.{ns}:{port_num}",
                            service_name=name,
                            namespace=ns,
                            port=port_num,
                            source="port-match",
                        )
                        endpoints.append(ep)
                        if console:
                            console.print(f"  [yellow]?[/yellow] {ep.url} (port match, unprobed)")

    if console:
        console.print(f"  [bold]Found {len(endpoints)} MCP endpoint(s)[/bold]")

    return endpoints
