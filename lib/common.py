#!/usr/bin/env python3
"""
Common utilities shared across Agent Smith analyzers.
Reduces code duplication and provides consistent behavior.
"""

from __future__ import annotations

import functools
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Optional, Callable, TypeVar

T = TypeVar('T')

# Shared constants
SKIP_DIRS = {".git", "node_modules", "__pycache__", "vendor", "build", "dist"}
CODE_EXTS = {".py", ".go", ".java", ".js", ".ts", ".php", ".rb", ".jsx", ".tsx"}
YAML_EXTS = {".yaml", ".yml"}
HELM_EXTS = {".tpl", ".gotmpl"}

# JSON parsing regex (matches code fences)
_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def get_api_key() -> str:
    """Retrieves the Claude API key from environment variable."""
    try:
        api_key = os.environ["CLAUDE_API_KEY"]
    except KeyError:
        logging.error("CLAUDE_API_KEY environment variable must be set")
        sys.exit(1)
    return api_key


def parse_json_response(response_text: str, max_size: int = 1_000_000) -> Optional[dict]:
    """
    Safely parses a JSON object from API response text.
    Handles code fences and extracts JSON from unstructured text.
    
    Args:
        response_text: Raw API response text
        max_size: Maximum response size in bytes to prevent memory exhaustion
    
    Returns:
        Parsed JSON dict or None if parsing fails
    """
    if not response_text:
        return None
    
    if len(response_text) > max_size:
        logging.warning(f"Response too large: {len(response_text)} bytes, max {max_size}")
        return None
    
    # Remove markdown code fences if present
    cleaned = _CODE_FENCE_RE.sub("", response_text).strip()
    
    # Find JSON object boundaries
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError:
            # Try with regex for nested objects
            match = re.search(r'\{.*\}', cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    return None
            return None
    return None


def scan_repo_files(
    repo_path: str | Path,
    include_yaml: bool = False,
    include_helm: bool = False,
    max_file_bytes: int = 500_000,
    max_files: int = 400,
    skip_dirs: Optional[set[str]] = None,
) -> list[Path]:
    """
    Scans a repository for code files suitable for analysis.
    
    Args:
        repo_path: Path to repository root
        include_yaml: Whether to include YAML files
        include_helm: Whether to include Helm template files
        max_file_bytes: Maximum file size to analyze
        max_files: Maximum number of files to return
        skip_dirs: Additional directories to skip (merged with default SKIP_DIRS)
    
    Returns:
        Sorted list of file paths to analyze
    """
    repo = Path(repo_path)
    if not repo.is_dir():
        raise ValueError(f"Repository path '{repo_path}' is not a directory")
    
    allowed_exts = set(CODE_EXTS)
    if include_yaml:
        allowed_exts |= YAML_EXTS
    if include_helm:
        allowed_exts |= HELM_EXTS
    
    skip_patterns = SKIP_DIRS | (skip_dirs or set())
    
    results: list[Path] = []
    for file_path in repo.rglob("*"):
        if len(results) >= max_files:
            break
        
        if not file_path.is_file():
            continue
        
        # Skip excluded directories
        if any(skip in file_path.parts for skip in skip_patterns):
            continue
        
        # Check extension
        if file_path.suffix.lower() not in allowed_exts:
            continue
        
        # Check file size with proper error handling
        try:
            file_stat = file_path.stat()
            if file_stat.st_size > max_file_bytes:
                continue
        except (OSError, PermissionError):
            continue
        
        # Use resolved paths for canonical representation
        results.append(file_path.resolve())
    
    # Sort by extension and full path for consistent ordering
    return sorted(results, key=lambda p: (p.suffix, str(p).lower()))


def validate_repo_path(path: str | Path) -> Path:
    """Validates that a repository path exists and is a directory."""
    repo_path = Path(path).resolve()
    if not repo_path.exists():
        raise ValueError(f"Repository path does not exist: {path}")
    if not repo_path.is_dir():
        raise ValueError(f"Repository path is not a directory: {path}")
    return repo_path


def estimate_api_cost(input_tokens: int, output_tokens: int, model: str = "haiku") -> float:
    """
    Estimates API cost based on token usage.
    
    Pricing (as of 2024):
    - Haiku: $0.25/$1.25 per 1M input/output tokens
    - Sonnet: $3/$15 per 1M input/output tokens
    
    Args:
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        model: Model name ('haiku' or 'sonnet')
    
    Returns:
        Estimated cost in USD
    """
    pricing = {
        "haiku": (0.25 / 1_000_000, 1.25 / 1_000_000),
        "sonnet": (3.0 / 1_000_000, 15.0 / 1_000_000),
    }
    
    input_price, output_price = pricing.get(model.lower(), pricing["haiku"])
    return (input_tokens * input_price) + (output_tokens * output_price)


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for retrying function calls with exponential backoff.
    
    Handles API errors gracefully:
    - Client errors (4xx): No retry, raise immediately
    - Server errors (5xx): Retry with exponential backoff
    - Rate limits (429): Retry with longer delay
    
    Works with anthropic.APIStatusError and other exceptions that have status_code attribute.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds for exponential backoff
        max_delay: Maximum delay in seconds
    
    Returns:
        Decorator function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception: Optional[Exception] = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    # Check if it's an APIStatusError (from anthropic) or similar
                    status_code = getattr(e, 'status_code', None)
                    
                    # Don't retry on client errors (4xx) - these are permanent failures
                    if status_code and 400 <= status_code < 500:
                        raise
                    
                    # Retry on server errors (5xx) and rate limits (429)
                    if attempt < max_retries - 1:
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        if status_code == 429:
                            delay = max(delay, 5.0)  # Longer delay for rate limits
                        time.sleep(delay)
                    else:
                        # Last attempt failed, raise the exception
                        raise
            
            # Should never reach here, but handle it just in case
            if last_exception:
                raise last_exception
            raise RuntimeError("Unexpected retry loop exit")
        return wrapper
    return decorator


# ============================================================================
# Finding Normalization Utilities
# ============================================================================

def normalize_finding(
    finding: dict,
    file_path: Optional[Path | str] = None,
    source: Optional[str] = None
) -> dict:
    """
    Normalize a finding dictionary to ensure consistent field names and values.
    
    Handles:
    - Recommendation field normalization (fix/explanation/recommendation/description)
    - Description field normalization
    - File path normalization (Path or string)
    - Line number normalization (line_number vs line)
    - Source field assignment
    - Title/rule_name normalization
    - Severity normalization (uppercase)
    
    Args:
        finding: Finding dictionary to normalize
        file_path: Optional file path to set/override
        source: Optional source identifier (e.g., 'claude-owasp', 'agentsmith')
    
    Returns:
        Normalized finding dictionary (new dict, doesn't modify original)
    """
    normalized = finding.copy()
    
    # Normalize file path
    if file_path:
        normalized['file'] = str(file_path)
    elif 'file' in normalized:
        # Ensure file is a string, not Path object
        normalized['file'] = str(normalized['file'])
    
    # Normalize line number (prefer 'line_number' over 'line')
    if 'line_number' not in normalized and 'line' in normalized:
        normalized['line_number'] = normalized['line']
    elif 'line_number' in normalized and 'line' not in normalized:
        normalized['line'] = normalized['line_number']
    
    # Normalize recommendation field (priority: recommendation > fix > explanation > description)
    if 'recommendation' not in normalized or not normalized.get('recommendation'):
        normalized['recommendation'] = (
            normalized.get('fix') or 
            normalized.get('explanation') or 
            normalized.get('description') or 
            'N/A'
        )
    
    # Ensure description exists (priority: description > explanation > recommendation)
    if 'description' not in normalized or not normalized.get('description'):
        normalized['description'] = (
            normalized.get('explanation') or 
            normalized.get('recommendation') or 
            'N/A'
        )
    
    # Ensure explanation exists (for backward compatibility)
    if 'explanation' not in normalized or not normalized.get('explanation'):
        normalized['explanation'] = normalized.get('description', 'N/A')
    
    # Set source if provided
    if source:
        normalized['source'] = source
    
    # Ensure title exists (fallback to rule_name)
    if 'title' not in normalized and 'rule_name' in normalized:
        normalized['title'] = normalized['rule_name']
    elif 'title' not in normalized:
        normalized['title'] = normalized.get('category', 'Unknown Issue')
    
    # Ensure rule_name exists (for backward compatibility)
    if 'rule_name' not in normalized and 'title' in normalized:
        normalized['rule_name'] = normalized['title']
    
    # Ensure category exists
    if 'category' not in normalized:
        normalized['category'] = 'Security'
    
    # Ensure severity exists and is uppercase
    if 'severity' in normalized:
        normalized['severity'] = str(normalized['severity']).upper()
    else:
        normalized['severity'] = 'MEDIUM'  # Default severity
    
    return normalized


def get_recommendation_text(finding: dict) -> str:
    """
    Extract recommendation text from a finding using fallback logic.
    
    Args:
        finding: Finding dictionary
    
    Returns:
        Recommendation text or 'N/A' if not found
    """
    return (
        finding.get('recommendation') or 
        finding.get('fix') or 
        finding.get('explanation') or 
        finding.get('description') or 
        'N/A'
    )


def get_line_number(finding: dict) -> int | str:
    """
    Extract line number from a finding, handling both 'line' and 'line_number' fields.
    
    Args:
        finding: Finding dictionary
    
    Returns:
        Line number as int or string, or 0 if not found
    """
    line = finding.get('line_number') or finding.get('line', 0)
    try:
        return int(line) if line else 0
    except (ValueError, TypeError):
        return str(line) if line else 0


# ============================================================================
# Error Handling Utilities
# ============================================================================

class AgentSmithError(Exception):
    """Base exception for Agent Smith errors."""
    pass


class APIError(AgentSmithError):
    """Exception for API-related errors."""
    def __init__(self, message: str, status_code: Optional[int] = None, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.status_code = status_code
        self.original_error = original_error


class FileAnalysisError(AgentSmithError):
    """Exception for file analysis errors."""
    def __init__(self, file_path: Path | str, message: str, original_error: Optional[Exception] = None):
        super().__init__(f"Error analyzing {file_path}: {message}")
        self.file_path = str(file_path)
        self.original_error = original_error


def handle_api_error(
    error: Exception,
    file_path: Optional[Path | str] = None,
    max_retries: int = 3,
    attempt: int = 0
) -> tuple[bool, Optional[float]]:
    """
    Handle API errors and determine if retry is appropriate.
    
    Args:
        error: The exception that occurred
        file_path: Optional file path for context
        max_retries: Maximum number of retries allowed
        attempt: Current attempt number (0-indexed)
    
    Returns:
        Tuple of (should_retry: bool, wait_time: Optional[float])
        - should_retry: True if operation should be retried
        - wait_time: Seconds to wait before retry (None if no retry)
    
    Raises:
        APIError: For non-retryable errors or after max retries
    """
    import anthropic
    
    # Handle Anthropic API errors
    if isinstance(error, anthropic.APIStatusError):
        status_code = error.status_code
        
        # Rate limit (429) or overloaded (529) - retry with backoff
        if status_code in (429, 529):
            if attempt < max_retries - 1:
                wait_time = min(2.0 ** (attempt + 1), 60.0)  # Exponential backoff, max 60s
                return True, wait_time
            else:
                raise APIError(
                    f"API rate limit exceeded after {max_retries} attempts",
                    status_code=status_code,
                    original_error=error
                )
        
        # Client errors (4xx except 429) - don't retry
        elif 400 <= status_code < 500:
            raise APIError(
                f"API client error: {error.message or str(error)}",
                status_code=status_code,
                original_error=error
            )
        
        # Server errors (5xx) - retry
        elif 500 <= status_code < 600:
            if attempt < max_retries - 1:
                wait_time = min(2.0 ** (attempt + 1), 30.0)  # Shorter backoff for server errors
                return True, wait_time
            else:
                raise APIError(
                    f"API server error after {max_retries} attempts: {error.message or str(error)}",
                    status_code=status_code,
                    original_error=error
                )
    
    # Handle other API errors
    elif isinstance(error, anthropic.APIError):
        # Network errors, timeouts, etc. - retry
        if attempt < max_retries - 1:
            wait_time = min(2.0 ** (attempt + 1), 30.0)
            return True, wait_time
        else:
            raise APIError(
                f"API error after {max_retries} attempts: {str(error)}",
                original_error=error
            )
    
    # Unknown error - don't retry
    raise APIError(
        f"Unexpected API error: {str(error)}",
        original_error=error
    )


def safe_file_read(file_path: Path, max_size: int = 10_000_000) -> str:
    """
    Safely read a file with size and error checking.
    
    Args:
        file_path: Path to file to read
        max_size: Maximum file size in bytes (default 10MB)
    
    Returns:
        File contents as string
    
    Raises:
        FileAnalysisError: If file cannot be read
    """
    try:
        file_stat = file_path.stat()
        if file_stat.st_size > max_size:
            raise FileAnalysisError(
                file_path,
                f"File too large: {file_stat.st_size} bytes (max {max_size})"
            )
        
        return file_path.read_text(encoding="utf-8", errors="replace")
    
    except (OSError, IOError, PermissionError) as e:
        raise FileAnalysisError(file_path, f"File read error: {str(e)}", original_error=e)
    except Exception as e:
        raise FileAnalysisError(file_path, f"Unexpected error reading file: {str(e)}", original_error=e)



