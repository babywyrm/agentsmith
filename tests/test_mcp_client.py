"""
Tests for MCP interactive client — key=value parsing, etc.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mcp_server.test_client import _parse_key_value_args


def test_parse_simple_key_value():
    """Simple key=value pairs."""
    r = _parse_key_value_args("profile=owasp preset=quick")
    assert r == {"profile": "owasp", "preset": "quick"}


def test_parse_quoted_value_with_spaces():
    """Quoted values with spaces (the bug case)."""
    r = _parse_key_value_args('profile=owasp prioritize_top=20 question="find SQL injection"')
    assert r == {"profile": "owasp", "prioritize_top": 20, "question": "find SQL injection"}


def test_parse_single_quoted_value():
    """Single key=value with quoted string."""
    r = _parse_key_value_args('question="find all vulnerabilities"')
    assert r == {"question": "find all vulnerabilities"}


def test_parse_boolean_values():
    """Boolean-like values."""
    r = _parse_key_value_args("verbose=true prioritize=false")
    assert r == {"verbose": True, "prioritize": False}


def test_parse_integer_value():
    """Integer values."""
    r = _parse_key_value_args("prioritize_top=20")
    assert r == {"prioritize_top": 20}


def test_parse_json_like_returns_none():
    """JSON-like input should return None (use json.loads instead)."""
    r = _parse_key_value_args('{"profile": "owasp"}')
    assert r is None


def test_parse_empty_returns_none():
    """Empty or whitespace returns None."""
    assert _parse_key_value_args("") is None
    assert _parse_key_value_args("   ") is None
