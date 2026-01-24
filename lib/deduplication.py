#!/usr/bin/env python3
"""
Finding deduplication utilities.

Provides intelligent deduplication of findings from multiple profiles
that may identify the same vulnerability with slightly different descriptions.
"""

from typing import List, Dict, Any, Tuple, Set
from pathlib import Path
import difflib


def are_findings_similar(
    finding1: Dict[str, Any],
    finding2: Dict[str, Any],
    similarity_threshold: float = 0.7
) -> bool:
    """
    Determine if two findings represent the same vulnerability.
    
    Args:
        finding1: First finding dictionary
        finding2: Second finding dictionary
        similarity_threshold: Minimum similarity score (0.0-1.0) to consider findings similar
        
    Returns:
        True if findings are similar enough to be considered duplicates
    """
    # Must be in the same file
    file1 = Path(finding1.get('file', '')).as_posix()
    file2 = Path(finding2.get('file', '')).as_posix()
    if file1 != file2:
        return False
    
    # Must be on the same line (or very close - within 5 lines)
    line1 = finding1.get('line_number', finding1.get('line', 0))
    line2 = finding2.get('line_number', finding2.get('line', 0))
    try:
        line1 = int(line1) if line1 else 0
        line2 = int(line2) if line2 else 0
        if abs(line1 - line2) > 5:
            return False
    except (ValueError, TypeError):
        # If we can't parse line numbers, require exact match
        if str(line1) != str(line2):
            return False
    
    # Check title similarity
    title1 = str(finding1.get('title', finding1.get('rule_name', ''))).lower().strip()
    title2 = str(finding2.get('title', finding2.get('rule_name', ''))).lower().strip()
    
    if not title1 or not title2:
        return False
    
    # Exact match on title
    if title1 == title2:
        return True
    
    # Check similarity using sequence matcher
    title_similarity = difflib.SequenceMatcher(None, title1, title2).ratio()
    if title_similarity >= similarity_threshold:
        return True
    
    # Check if titles contain similar keywords (for cases like "SQL Injection" vs "SQLi")
    # Extract key security terms
    security_terms1 = _extract_security_terms(title1)
    security_terms2 = _extract_security_terms(title2)
    
    if security_terms1 and security_terms2:
        # If they share significant security terms, check category
        common_terms = security_terms1.intersection(security_terms2)
        if len(common_terms) >= 2:  # At least 2 common security terms
            # Also check category similarity
            cat1 = str(finding1.get('category', '')).lower().strip()
            cat2 = str(finding2.get('category', '')).lower().strip()
            if cat1 and cat2:
                cat_similarity = difflib.SequenceMatcher(None, cat1, cat2).ratio()
                if cat_similarity >= 0.6:  # Categories are similar
                    return True
    
    return False


def _extract_security_terms(text: str) -> Set[str]:
    """Extract security-related terms from text."""
    # Common security vulnerability terms
    security_keywords = {
        'sql', 'injection', 'sqli', 'xss', 'cross-site', 'csrf', 'authentication',
        'authorization', 'access', 'control', 'bypass', 'privilege', 'escalation',
        'hardcoded', 'secret', 'password', 'credential', 'token', 'key', 'api',
        'deserialization', 'serialization', 'path', 'traversal', 'directory',
        'command', 'execution', 'code', 'injection', 'ssrf', 'xxe', 'xxs',
        'crypto', 'encryption', 'hash', 'weak', 'vulnerable', 'exposure',
        'misconfiguration', 'security', 'vulnerability', 'flaw', 'weakness'
    }
    
    text_lower = text.lower()
    found_terms = set()
    
    for keyword in security_keywords:
        if keyword in text_lower:
            found_terms.add(keyword)
    
    return found_terms


def deduplicate_findings(
    findings: List[Dict[str, Any]],
    similarity_threshold: float = 0.7,
    merge_strategy: str = "keep_highest_severity"
) -> List[Dict[str, Any]]:
    """
    Deduplicate findings by merging similar ones.
    
    Args:
        findings: List of finding dictionaries
        similarity_threshold: Minimum similarity to consider duplicates (0.0-1.0)
        merge_strategy: How to merge duplicates
            - "keep_highest_severity": Keep finding with highest severity
            - "keep_first": Keep first occurrence
            - "merge": Merge all information
        
    Returns:
        Deduplicated list of findings
    """
    if not findings:
        return []
    
    # Severity ordering for merge strategies
    severity_order = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "INFO": 0}
    
    deduplicated: List[Dict[str, Any]] = []
    processed_indices: Set[int] = set()
    
    for i, finding1 in enumerate(findings):
        if i in processed_indices:
            continue
        
        # Find all similar findings
        similar_findings = [finding1]
        similar_indices = [i]
        
        for j, finding2 in enumerate(findings[i+1:], start=i+1):
            if j in processed_indices:
                continue
            
            if are_findings_similar(finding1, finding2, similarity_threshold):
                similar_findings.append(finding2)
                similar_indices.append(j)
        
        # Mark all similar findings as processed
        processed_indices.update(similar_indices)
        
        # Merge similar findings based on strategy
        if len(similar_findings) == 1:
            # No duplicates, just add it
            deduplicated.append(finding1)
        else:
            # Merge duplicates
            if merge_strategy == "keep_highest_severity":
                # Find highest severity
                best_finding = max(
                    similar_findings,
                    key=lambda f: severity_order.get(
                        str(f.get('severity', 'LOW')).upper(), 0
                    )
                )
                # Add profile sources
                sources = [f.get('source', '') for f in similar_findings if f.get('source')]
                if sources:
                    best_finding = best_finding.copy()
                    if len(set(sources)) > 1:
                        best_finding['source'] = ', '.join(sorted(set(sources)))
                        best_finding['profiles'] = sources  # Track which profiles found it
                deduplicated.append(best_finding)
                
            elif merge_strategy == "keep_first":
                deduplicated.append(finding1)
                
            elif merge_strategy == "merge":
                # Merge all information
                merged = finding1.copy()
                # Combine sources
                sources = [f.get('source', '') for f in similar_findings if f.get('source')]
                if sources:
                    merged['source'] = ', '.join(sorted(set(sources)))
                    merged['profiles'] = sources
                # Use highest severity
                merged['severity'] = max(
                    (f.get('severity', 'LOW') for f in similar_findings),
                    key=lambda s: severity_order.get(str(s).upper(), 0)
                )
                # Combine recommendations (take longest/most detailed)
                recommendations = [
                    f.get('recommendation') or f.get('fix') or f.get('explanation') or ''
                    for f in similar_findings
                ]
                recommendations = [r for r in recommendations if r and r != 'N/A']
                if recommendations:
                    merged['recommendation'] = ' | '.join(sorted(set(recommendations)))
                deduplicated.append(merged)
    
    return deduplicated



