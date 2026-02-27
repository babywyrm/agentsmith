#!/usr/bin/env python3
"""
Tests for the modular prompt composer.
"""

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.prompt_composer import (
    get_base_prompt,
    get_profile_section,
    compose_prompt,
    has_composed_support,
)


class TestPromptComposer(unittest.TestCase):
    """Test prompt composition logic."""

    def test_base_prompt_loads(self):
        """Base prompt should load and contain placeholders."""
        base = get_base_prompt()
        self.assertGreater(len(base), 100)
        self.assertIn("{file_path}", base)
        self.assertIn("{language}", base)
        self.assertIn("{app_context}", base)

    def test_profile_sections_exist(self):
        """Key profiles should have section files."""
        for profile in ["owasp", "springboot", "ctf", "flask"]:
            section = get_profile_section(profile)
            self.assertIsNotNone(section, f"{profile} section should exist")
            self.assertGreater(len(section), 20)

    def test_compose_single_profile(self):
        """Compose with one profile returns valid prompt."""
        composed = compose_prompt(["owasp"], use_legacy_fallback=True)
        self.assertIsNotNone(composed)
        self.assertIn("{code}", composed)
        self.assertIn("OWASP", composed)

    def test_compose_multiple_profiles(self):
        """Compose with multiple profiles merges sections."""
        composed = compose_prompt(["owasp", "springboot"], use_legacy_fallback=True)
        self.assertIsNotNone(composed)
        self.assertIn("OWASP", composed)
        self.assertIn("Spring", composed)

    def test_has_composed_support(self):
        """has_composed_support returns True when base + sections exist."""
        self.assertTrue(has_composed_support(["owasp"]))
        self.assertTrue(has_composed_support(["owasp", "springboot"]))
        self.assertTrue(has_composed_support(["compliance"]))

    def test_composed_format_works(self):
        """Composed prompt can be formatted with standard placeholders."""
        composed = compose_prompt(["owasp"], use_legacy_fallback=True)
        self.assertIsNotNone(composed)
        result = composed.format(
            file_path="test.py",
            language="python",
            code="print(1)",
            app_context="Flask app",
        )
        self.assertIn("test.py", result)
        self.assertIn("print(1)", result)
        self.assertIn("Flask app", result)


if __name__ == "__main__":
    unittest.main()
