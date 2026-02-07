#!/usr/bin/env python3
"""
Tests for the centralized model registry.

Tests model resolution, pricing, validation, environment variable support,
and backwards compatibility with legacy model IDs.
"""

import os
import unittest
import sys
from pathlib import Path
from unittest.mock import patch

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.model_registry import (
    resolve_model,
    get_model_def,
    get_default_model,
    get_model_pricing,
    get_pricing_dict,
    list_models,
    model_help_text,
    model_cli_help,
    ModelDef,
    ALL_MODELS,
    CURRENT_MODELS,
    DEFAULT_MODEL_ID,
    MODEL_CHOICES,
    CLAUDE_OPUS_4_6,
    CLAUDE_SONNET_4_5,
    CLAUDE_HAIKU_4_5,
)


class TestModelResolution(unittest.TestCase):
    """Test that model names, aliases, and IDs resolve correctly."""

    def test_resolve_full_model_id(self):
        """Test resolving full model IDs."""
        self.assertEqual(resolve_model("claude-opus-4-6"), "claude-opus-4-6")
        self.assertEqual(resolve_model("claude-sonnet-4-5-20250929"), "claude-sonnet-4-5-20250929")
        self.assertEqual(resolve_model("claude-haiku-4-5-20251001"), "claude-haiku-4-5-20251001")

    def test_resolve_short_names(self):
        """Test resolving short alias names."""
        self.assertEqual(resolve_model("opus"), "claude-opus-4-6")
        self.assertEqual(resolve_model("sonnet"), "claude-sonnet-4-5-20250929")
        self.assertEqual(resolve_model("haiku"), "claude-haiku-4-5-20251001")

    def test_resolve_versioned_aliases(self):
        """Test resolving versioned short names."""
        self.assertEqual(resolve_model("opus-4.6"), "claude-opus-4-6")
        self.assertEqual(resolve_model("sonnet-4.5"), "claude-sonnet-4-5-20250929")
        self.assertEqual(resolve_model("haiku-4.5"), "claude-haiku-4-5-20251001")

    def test_resolve_case_insensitive(self):
        """Test that resolution is case-insensitive."""
        self.assertEqual(resolve_model("OPUS"), "claude-opus-4-6")
        self.assertEqual(resolve_model("Sonnet"), "claude-sonnet-4-5-20250929")
        self.assertEqual(resolve_model("HAIKU"), "claude-haiku-4-5-20251001")

    def test_resolve_with_whitespace(self):
        """Test that whitespace is stripped."""
        self.assertEqual(resolve_model("  opus  "), "claude-opus-4-6")
        self.assertEqual(resolve_model("\tsonnet\n"), "claude-sonnet-4-5-20250929")

    def test_resolve_legacy_models(self):
        """Test resolving legacy model IDs."""
        self.assertEqual(resolve_model("claude-3-5-haiku-20241022"), "claude-3-5-haiku-20241022")
        self.assertEqual(resolve_model("claude-3-5-sonnet-20241022"), "claude-3-5-sonnet-20241022")
        self.assertEqual(resolve_model("claude-3-opus-20240229"), "claude-3-opus-20240229")

    def test_resolve_legacy_short_names(self):
        """Test resolving legacy short names."""
        self.assertEqual(resolve_model("haiku-3.5"), "claude-3-5-haiku-20241022")
        self.assertEqual(resolve_model("sonnet-3.5"), "claude-3-5-sonnet-20241022")
        self.assertEqual(resolve_model("opus-3"), "claude-3-opus-20240229")

    def test_resolve_unknown_model_raises(self):
        """Test that unknown models raise ValueError."""
        with self.assertRaises(ValueError):
            resolve_model("gpt-4")

        with self.assertRaises(ValueError):
            resolve_model("nonexistent-model")

        with self.assertRaises(ValueError):
            resolve_model("")


class TestModelDef(unittest.TestCase):
    """Test ModelDef structure and properties."""

    def test_get_model_def(self):
        """Test getting full model definition."""
        model_def = get_model_def("opus")
        self.assertIsInstance(model_def, ModelDef)
        self.assertEqual(model_def.model_id, "claude-opus-4-6")
        self.assertEqual(model_def.tier, "opus")

    def test_model_def_fields(self):
        """Test that all ModelDef fields are populated."""
        for model in ALL_MODELS:
            self.assertIsInstance(model.model_id, str)
            self.assertGreater(len(model.model_id), 0)
            self.assertIsInstance(model.aliases, tuple)
            self.assertGreater(len(model.aliases), 0)
            self.assertIn(model.tier, ("opus", "sonnet", "haiku"))
            self.assertIsInstance(model.generation, str)
            self.assertGreater(model.input_price, 0)
            self.assertGreater(model.output_price, 0)
            self.assertGreater(model.max_output_tokens, 0)
            self.assertGreater(model.context_window, 0)
            self.assertIsInstance(model.description, str)

    def test_current_models_not_deprecated(self):
        """Test that current models are not marked deprecated."""
        for model in CURRENT_MODELS:
            self.assertFalse(model.deprecated, f"{model.model_id} should not be deprecated")

    def test_legacy_models_are_deprecated(self):
        """Test that legacy models are marked deprecated."""
        legacy = [m for m in ALL_MODELS if m not in CURRENT_MODELS]
        for model in legacy:
            self.assertTrue(model.deprecated, f"{model.model_id} should be deprecated")


class TestDefaultModel(unittest.TestCase):
    """Test default model selection and env var override."""

    def test_default_model_is_set(self):
        """Test that a default model is defined."""
        self.assertIsNotNone(DEFAULT_MODEL_ID)
        self.assertGreater(len(DEFAULT_MODEL_ID), 0)

    def test_default_model_is_current_gen(self):
        """Test that default model is a current-generation model."""
        default_def = get_model_def(DEFAULT_MODEL_ID)
        self.assertFalse(default_def.deprecated)

    def test_get_default_model_without_env(self):
        """Test default model when CLAUDE_MODEL env var is not set."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove CLAUDE_MODEL if it exists
            os.environ.pop("CLAUDE_MODEL", None)
            model = get_default_model()
            self.assertEqual(model, DEFAULT_MODEL_ID)

    def test_get_default_model_with_env_full_id(self):
        """Test that CLAUDE_MODEL env var with full ID works."""
        with patch.dict(os.environ, {"CLAUDE_MODEL": "claude-opus-4-6"}):
            model = get_default_model()
            self.assertEqual(model, "claude-opus-4-6")

    def test_get_default_model_with_env_alias(self):
        """Test that CLAUDE_MODEL env var with alias works."""
        with patch.dict(os.environ, {"CLAUDE_MODEL": "opus"}):
            model = get_default_model()
            self.assertEqual(model, "claude-opus-4-6")

    def test_get_default_model_with_env_sonnet(self):
        """Test CLAUDE_MODEL=sonnet selects Sonnet 4.5."""
        with patch.dict(os.environ, {"CLAUDE_MODEL": "sonnet"}):
            model = get_default_model()
            self.assertEqual(model, "claude-sonnet-4-5-20250929")

    def test_get_default_model_with_invalid_env(self):
        """Test that invalid CLAUDE_MODEL falls back to default."""
        with patch.dict(os.environ, {"CLAUDE_MODEL": "totally-fake-model"}):
            model = get_default_model()
            self.assertEqual(model, DEFAULT_MODEL_ID)

    def test_get_default_model_with_empty_env(self):
        """Test that empty CLAUDE_MODEL env var uses default."""
        with patch.dict(os.environ, {"CLAUDE_MODEL": ""}):
            model = get_default_model()
            self.assertEqual(model, DEFAULT_MODEL_ID)


class TestPricing(unittest.TestCase):
    """Test model pricing lookups."""

    def test_opus_pricing(self):
        """Test Opus 4.6 pricing."""
        input_price, output_price = get_model_pricing("claude-opus-4-6")
        self.assertEqual(input_price, 5.00)
        self.assertEqual(output_price, 25.00)

    def test_sonnet_pricing(self):
        """Test Sonnet 4.5 pricing."""
        input_price, output_price = get_model_pricing("sonnet")
        self.assertEqual(input_price, 3.00)
        self.assertEqual(output_price, 15.00)

    def test_haiku_pricing(self):
        """Test Haiku 4.5 pricing."""
        input_price, output_price = get_model_pricing("haiku")
        self.assertEqual(input_price, 1.00)
        self.assertEqual(output_price, 5.00)

    def test_legacy_pricing(self):
        """Test legacy model pricing."""
        input_price, output_price = get_model_pricing("claude-3-5-haiku-20241022")
        self.assertEqual(input_price, 0.80)
        self.assertEqual(output_price, 4.00)

    def test_unknown_model_fallback_pricing(self):
        """Test that unknown models get fallback pricing."""
        input_price, output_price = get_model_pricing("unknown-model-xyz")
        # Should get default pricing (not crash)
        self.assertGreater(input_price, 0)
        self.assertGreater(output_price, 0)

    def test_pricing_dict(self):
        """Test get_pricing_dict returns all models."""
        pricing = get_pricing_dict()
        self.assertIsInstance(pricing, dict)
        self.assertGreater(len(pricing), 0)

        # All known models should be present
        for model in ALL_MODELS:
            self.assertIn(model.model_id, pricing)
            inp, out = pricing[model.model_id]
            self.assertEqual(inp, model.input_price)
            self.assertEqual(out, model.output_price)

    def test_output_more_expensive_than_input(self):
        """Test that output tokens are always more expensive than input."""
        for model in ALL_MODELS:
            self.assertGreater(
                model.output_price, model.input_price,
                f"{model.model_id}: output should cost more than input"
            )


class TestListModels(unittest.TestCase):
    """Test model listing."""

    def test_list_current_models(self):
        """Test listing only current models."""
        models = list_models(include_deprecated=False)
        self.assertEqual(len(models), 3)  # Opus 4.6, Sonnet 4.5, Haiku 4.5
        for m in models:
            self.assertFalse(m.deprecated)

    def test_list_all_models(self):
        """Test listing all models including deprecated."""
        models = list_models(include_deprecated=True)
        self.assertGreater(len(models), 3)
        # Should include at least some deprecated models
        deprecated = [m for m in models if m.deprecated]
        self.assertGreater(len(deprecated), 0)

    def test_model_choices_for_cli(self):
        """Test MODEL_CHOICES contains all valid choices."""
        self.assertIsInstance(MODEL_CHOICES, list)
        self.assertGreater(len(MODEL_CHOICES), 0)
        # Should include short names
        self.assertIn("opus", MODEL_CHOICES)
        self.assertIn("sonnet", MODEL_CHOICES)
        self.assertIn("haiku", MODEL_CHOICES)
        # Should include full IDs
        self.assertIn("claude-opus-4-6", MODEL_CHOICES)


class TestHelpText(unittest.TestCase):
    """Test help text generation."""

    def test_model_help_text(self):
        """Test full help text generation."""
        text = model_help_text()
        self.assertIsInstance(text, str)
        self.assertIn("opus", text.lower())
        self.assertIn("sonnet", text.lower())
        self.assertIn("haiku", text.lower())
        self.assertIn("Default:", text)

    def test_model_cli_help(self):
        """Test CLI help string generation."""
        text = model_cli_help()
        self.assertIsInstance(text, str)
        self.assertIn("opus", text.lower())
        self.assertIn("CLAUDE_MODEL", text)


class TestDeprecationWarning(unittest.TestCase):
    """Test that deprecated models emit warnings."""

    def test_legacy_model_warns(self):
        """Test that resolving a legacy model emits a warning."""
        import logging

        with self.assertLogs("lib.model_registry", level="WARNING") as cm:
            resolve_model("claude-3-5-haiku-20241022")
        
        # Should have logged a deprecation warning
        self.assertTrue(any("deprecated" in msg.lower() for msg in cm.output))

    def test_current_model_no_warning(self):
        """Test that resolving a current model does not warn."""
        import logging

        logger = logging.getLogger("lib.model_registry")
        # Resolve current model - should not produce warnings
        with self.assertNoLogs("lib.model_registry", level="WARNING"):
            resolve_model("opus")


class TestModelRegistryIntegrity(unittest.TestCase):
    """Test overall registry integrity."""

    def test_no_duplicate_model_ids(self):
        """Test that all model IDs are unique."""
        ids = [m.model_id for m in ALL_MODELS]
        self.assertEqual(len(ids), len(set(ids)))

    def test_no_conflicting_aliases(self):
        """Test that no alias maps to multiple models."""
        alias_map = {}
        for model in ALL_MODELS:
            for alias in model.aliases:
                if alias.lower() in alias_map:
                    self.assertEqual(
                        alias_map[alias.lower()], model.model_id,
                        f"Alias '{alias}' maps to both {alias_map[alias.lower()]} and {model.model_id}"
                    )
                alias_map[alias.lower()] = model.model_id

    def test_each_model_has_own_id_as_alias(self):
        """Test that each model's ID is in its aliases or resolves to itself."""
        for model in ALL_MODELS:
            resolved = resolve_model(model.model_id)
            self.assertEqual(resolved, model.model_id)

    def test_all_tiers_represented(self):
        """Test that all three tiers have at least one current model."""
        current_tiers = {m.tier for m in CURRENT_MODELS}
        self.assertIn("opus", current_tiers)
        self.assertIn("sonnet", current_tiers)
        self.assertIn("haiku", current_tiers)

    def test_models_ordered_by_generation(self):
        """Test that current models come before legacy in ALL_MODELS."""
        first_deprecated_idx = None
        for i, model in enumerate(ALL_MODELS):
            if model.deprecated and first_deprecated_idx is None:
                first_deprecated_idx = i
            elif not model.deprecated and first_deprecated_idx is not None:
                self.fail("Current model found after deprecated model in ALL_MODELS ordering")


class TestBackwardsCompatibility(unittest.TestCase):
    """Test backwards compatibility with existing codebase patterns."""

    def test_old_default_model_still_resolves(self):
        """Test that the old default model ID still works."""
        # This was the old default across the codebase
        resolved = resolve_model("claude-3-5-haiku-20241022")
        self.assertEqual(resolved, "claude-3-5-haiku-20241022")

    def test_old_sonnet_model_still_resolves(self):
        """Test that old sonnet model ID still works."""
        resolved = resolve_model("claude-3-5-sonnet-20241022")
        self.assertEqual(resolved, "claude-3-5-sonnet-20241022")

    def test_old_opus_model_still_resolves(self):
        """Test that old opus model ID still works."""
        resolved = resolve_model("claude-3-opus-20240229")
        self.assertEqual(resolved, "claude-3-opus-20240229")

    def test_pricing_dict_has_legacy_models(self):
        """Test that pricing dict includes legacy models for cost tracking."""
        pricing = get_pricing_dict()
        self.assertIn("claude-3-5-haiku-20241022", pricing)
        self.assertIn("claude-3-5-sonnet-20241022", pricing)
        self.assertIn("claude-3-opus-20240229", pricing)


if __name__ == '__main__':
    unittest.main()
