"""Tests for K8s discovery and scanner modules."""

import pytest

from mcp_attack.cli import parse_args
from mcp_attack.k8s.discovery import (
    DiscoveredEndpoint,
    discover_services,
    _get_sa_token,
)
from mcp_attack.k8s.scanner import (
    GLOBAL_K8S_FINDINGS,
    _check_pod_security,
    _check_configmap_leaks,
)
from mcp_attack.core.models import Finding


def test_discover_services_no_sa_token():
    """Outside a pod, discovery should return empty list."""
    results = discover_services()
    assert results == []


def test_discovered_endpoint_fields():
    ep = DiscoveredEndpoint(
        url="http://my-svc.default:8080/mcp",
        service_name="my-svc",
        namespace="default",
        port=8080,
        transport_hint="sse",
        path_hint="/mcp",
        source="annotation",
    )
    assert ep.url == "http://my-svc.default:8080/mcp"
    assert ep.source == "annotation"


def test_get_sa_token_not_in_pod():
    assert _get_sa_token() is None


def test_cli_k8s_discover_flags():
    args = parse_args(["--k8s-discover"])
    assert args.k8s_discover is True
    assert args.k8s_discover_namespaces is None
    assert args.k8s_no_probe is False


def test_cli_k8s_discover_namespaces():
    args = parse_args([
        "--k8s-discover",
        "--k8s-discover-namespaces", "default", "kube-system",
        "--k8s-no-probe",
    ])
    assert args.k8s_discover_namespaces == ["default", "kube-system"]
    assert args.k8s_no_probe is True


class TestPodSecurityChecks:
    def setup_method(self):
        GLOBAL_K8S_FINDINGS.clear()

    def test_privileged_container(self):
        pod = {
            "metadata": {"name": "bad-pod"},
            "spec": {
                "containers": [{
                    "name": "evil",
                    "securityContext": {"privileged": True},
                }],
            },
        }
        _check_pod_security(pod, "default")
        assert any("Privileged" in f.title for f in GLOBAL_K8S_FINDINGS)
        assert any(f.severity == "CRITICAL" for f in GLOBAL_K8S_FINDINGS)

    def test_host_network(self):
        pod = {
            "metadata": {"name": "host-net-pod"},
            "spec": {
                "hostNetwork": True,
                "containers": [{"name": "c1"}],
            },
        }
        _check_pod_security(pod, "default")
        assert any("hostNetwork" in f.title for f in GLOBAL_K8S_FINDINGS)

    def test_dangerous_capabilities(self):
        pod = {
            "metadata": {"name": "cap-pod"},
            "spec": {
                "containers": [{
                    "name": "c1",
                    "securityContext": {
                        "capabilities": {"add": ["SYS_ADMIN", "NET_RAW"]},
                    },
                }],
            },
        }
        _check_pod_security(pod, "default")
        assert any("capabilities" in f.title.lower() for f in GLOBAL_K8S_FINDINGS)

    def test_no_resource_limits(self):
        pod = {
            "metadata": {"name": "no-limits"},
            "spec": {
                "containers": [{"name": "c1"}],
            },
        }
        _check_pod_security(pod, "default")
        assert any("resource limits" in f.title.lower() for f in GLOBAL_K8S_FINDINGS)

    def test_host_path_mount(self):
        pod = {
            "metadata": {"name": "hostpath-pod"},
            "spec": {
                "containers": [{
                    "name": "c1",
                    "volumeMounts": [{"name": "data", "mountPath": "/data"}],
                }],
                "volumes": [{
                    "name": "data",
                    "hostPath": {"path": "/etc/shadow"},
                }],
            },
        }
        _check_pod_security(pod, "default")
        assert any("hostPath" in f.title for f in GLOBAL_K8S_FINDINGS)

    def test_clean_pod_no_findings(self):
        pod = {
            "metadata": {"name": "clean-pod"},
            "spec": {
                "containers": [{
                    "name": "app",
                    "securityContext": {
                        "runAsUser": 1000,
                        "allowPrivilegeEscalation": False,
                    },
                    "resources": {
                        "limits": {"memory": "128Mi", "cpu": "100m"},
                    },
                }],
            },
        }
        _check_pod_security(pod, "default")
        critical_or_high = [f for f in GLOBAL_K8S_FINDINGS
                           if f.severity in ("CRITICAL", "HIGH")]
        assert len(critical_or_high) == 0


class TestConfigMapLeaks:
    def setup_method(self):
        GLOBAL_K8S_FINDINGS.clear()

    def test_private_key_in_configmap(self):
        cm = {
            "metadata": {"name": "leaked-cm"},
            "data": {"ssh_key": "-----BEGIN RSA PRIVATE KEY-----\nfoo\n-----END RSA PRIVATE KEY-----"},
        }
        _check_configmap_leaks(cm, "default")
        assert any("Private key" in f.title for f in GLOBAL_K8S_FINDINGS)

    def test_password_field_in_configmap(self):
        cm = {
            "metadata": {"name": "cred-cm"},
            "data": {"db_password": "hunter2"},
        }
        _check_configmap_leaks(cm, "default")
        assert any("credential" in f.title.lower() for f in GLOBAL_K8S_FINDINGS)

    def test_clean_configmap(self):
        cm = {
            "metadata": {"name": "clean-cm"},
            "data": {"app_name": "myapp", "log_level": "debug"},
        }
        _check_configmap_leaks(cm, "default")
        assert len(GLOBAL_K8S_FINDINGS) == 0
