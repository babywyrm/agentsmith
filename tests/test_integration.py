#!/usr/bin/env python3
"""
Integration tests for normalization in orchestrator.

Tests that the orchestrator correctly uses normalization utilities.
"""

import unittest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.common import normalize_finding, get_recommendation_text, get_line_number


class TestNormalizationIntegration(unittest.TestCase):
    """Test normalization integration scenarios."""
    
    def test_finding_from_different_sources(self):
        """Test normalizing findings from different sources."""
        # Simulate finding from static scanner
        static_finding = {
            'file': '/test/vuln.php',
            'line': 42,
            'rule_name': 'SQL Injection',
            'severity': 'HIGH',
            'category': 'A03',
        }
        
        normalized = normalize_finding(static_finding, source='agentsmith')
        
        # Verify normalization
        self.assertEqual(normalized['source'], 'agentsmith')
        self.assertEqual(normalized['file'], '/test/vuln.php')
        self.assertEqual(normalized['line_number'], 42)
        self.assertEqual(normalized['line'], 42)
        self.assertEqual(normalized['title'], 'SQL Injection')
        self.assertEqual(normalized['severity'], 'HIGH')
        
    def test_finding_from_ai_scanner(self):
        """Test normalizing findings from AI scanner."""
        # Simulate finding from Claude
        ai_finding = {
            'file': Path('/test/xss.js'),
            'line_number': 100,
            'title': 'XSS Vulnerability',
            'severity': 'high',
            'category': 'A03',
            'fix': 'Sanitize user input before rendering',
            'explanation': 'User input is rendered without sanitization',
        }
        
        normalized = normalize_finding(ai_finding, source='claude-owasp')
        
        # Verify normalization
        self.assertEqual(normalized['source'], 'claude-owasp')
        self.assertEqual(normalized['file'], '/test/xss.js')
        self.assertIsInstance(normalized['file'], str)
        self.assertEqual(normalized['line_number'], 100)
        self.assertEqual(normalized['severity'], 'HIGH')
        self.assertEqual(normalized['recommendation'], 'Sanitize user input before rendering')
        
    def test_recommendation_extraction_priority(self):
        """Test that recommendation extraction follows correct priority."""
        # Test with all fields present
        finding = {
            'recommendation': 'Use parameterized queries',
            'fix': 'Alternative fix',
            'explanation': 'SQL injection found',
            'description': 'Vulnerable code'
        }
        
        # Should prefer 'recommendation' over others
        self.assertEqual(get_recommendation_text(finding), 'Use parameterized queries')
        
        # Test with only 'fix'
        finding2 = {'fix': 'Use parameterized queries'}
        self.assertEqual(get_recommendation_text(finding2), 'Use parameterized queries')
        
        # Test with only 'explanation'
        finding3 = {'explanation': 'SQL injection found'}
        self.assertEqual(get_recommendation_text(finding3), 'SQL injection found')
        
    def test_line_number_extraction(self):
        """Test line number extraction from different field names."""
        # From 'line' field
        finding1 = {'line': 42}
        self.assertEqual(get_line_number(finding1), 42)
        
        # From 'line_number' field
        finding2 = {'line_number': 100}
        self.assertEqual(get_line_number(finding2), 100)
        
        # Priority: line_number over line
        finding3 = {'line': 10, 'line_number': 20}
        self.assertEqual(get_line_number(finding3), 20)
        
    def test_complete_workflow(self):
        """Test a complete finding normalization workflow."""
        # Simulate a raw finding from AI
        raw_finding = {
            'file': Path('/app/login.php'),
            'line': 25,
            'title': 'Hardcoded Password',
            'severity': 'critical',
            'category': 'A02',
            'fix': 'Use environment variables for credentials',
            'explanation': 'Password is hardcoded in source code',
        }
        
        # Normalize it (as orchestrator would)
        normalized = normalize_finding(raw_finding, source='claude-owasp')
        
        # Extract values (as CSV/MD export would)
        recommendation = get_recommendation_text(normalized)
        line_num = get_line_number(normalized)
        
        # Verify complete workflow
        self.assertEqual(normalized['source'], 'claude-owasp')
        self.assertEqual(normalized['file'], '/app/login.php')
        self.assertIsInstance(normalized['file'], str)
        self.assertEqual(normalized['severity'], 'CRITICAL')
        self.assertEqual(normalized['title'], 'Hardcoded Password')
        self.assertEqual(normalized['recommendation'], 'Use environment variables for credentials')
        self.assertEqual(recommendation, 'Use environment variables for credentials')
        self.assertEqual(line_num, 25)
        self.assertEqual(normalized['line_number'], 25)
        self.assertEqual(normalized['line'], 25)


if __name__ == "__main__":
    unittest.main()

