#!/usr/bin/env python3
"""
SCRYNET Model Registry

Single source of truth for all Claude model definitions, pricing, aliases,
and selection logic. Every part of SCRYNET that references a model should
import from here instead of hardcoding model strings.

Usage:
    from lib.model_registry import (
        get_default_model,
        resolve_model,
        get_model_pricing,
        list_models,
        MODEL_CHOICES,
    )

    model = get_default_model()          # respects CLAUDE_MODEL env var
    model = resolve_model("opus")        # -> "claude-opus-4-6"
    pricing = get_model_pricing(model)   # -> (5.00, 25.00)

Environment Variables:
    CLAUDE_MODEL  - Override the default model (e.g. "opus", "sonnet", or full ID)
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


# ============================================================================
# Model Definitions
# ============================================================================

@dataclass(frozen=True, slots=True)
class ModelDef:
    """Definition of a Claude model."""
    model_id: str               # Canonical API model ID
    aliases: Tuple[str, ...]    # Short names and alternate IDs
    tier: str                   # "opus", "sonnet", "haiku"
    generation: str             # e.g. "4.6", "4.5", "3.5"
    input_price: float          # USD per 1M input tokens
    output_price: float         # USD per 1M output tokens
    max_output_tokens: int      # Maximum output tokens
    context_window: int         # Standard context window size
    description: str            # Human-readable description
    deprecated: bool = False    # Whether this model is deprecated


# --- Current generation models (Claude 4.x) ---

CLAUDE_OPUS_4_6 = ModelDef(
    model_id="claude-opus-4-6",
    aliases=("opus", "opus-4.6", "claude-opus-4-6"),
    tier="opus",
    generation="4.6",
    input_price=5.00,
    output_price=25.00,
    max_output_tokens=128_000,
    context_window=200_000,
    description="Most intelligent model - best for complex analysis, agents, and coding",
)

CLAUDE_SONNET_4_5 = ModelDef(
    model_id="claude-sonnet-4-5-20250929",
    aliases=("sonnet", "sonnet-4.5", "claude-sonnet-4-5", "claude-sonnet-4-5-20250929"),
    tier="sonnet",
    generation="4.5",
    input_price=3.00,
    output_price=15.00,
    max_output_tokens=64_000,
    context_window=200_000,
    description="Best balance of speed and intelligence",
)

CLAUDE_HAIKU_4_5 = ModelDef(
    model_id="claude-haiku-4-5-20251001",
    aliases=("haiku", "haiku-4.5", "claude-haiku-4-5", "claude-haiku-4-5-20251001"),
    tier="haiku",
    generation="4.5",
    input_price=1.00,
    output_price=5.00,
    max_output_tokens=64_000,
    context_window=200_000,
    description="Fastest model - best for cost-efficient bulk analysis",
)


# --- Legacy models (Claude 3.x) ---

CLAUDE_SONNET_3_5 = ModelDef(
    model_id="claude-3-5-sonnet-20241022",
    aliases=("sonnet-3.5", "claude-3-5-sonnet", "claude-3-5-sonnet-20241022"),
    tier="sonnet",
    generation="3.5",
    input_price=3.00,
    output_price=15.00,
    max_output_tokens=8_192,
    context_window=200_000,
    description="Legacy Sonnet 3.5 (use sonnet-4.5 instead)",
    deprecated=True,
)

CLAUDE_HAIKU_3_5 = ModelDef(
    model_id="claude-3-5-haiku-20241022",
    aliases=("haiku-3.5", "claude-3-5-haiku", "claude-3-5-haiku-20241022"),
    tier="haiku",
    generation="3.5",
    input_price=0.80,
    output_price=4.00,
    max_output_tokens=8_192,
    context_window=200_000,
    description="Legacy Haiku 3.5 (use haiku-4.5 instead)",
    deprecated=True,
)

CLAUDE_OPUS_3 = ModelDef(
    model_id="claude-3-opus-20240229",
    aliases=("opus-3", "claude-3-opus", "claude-3-opus-20240229"),
    tier="opus",
    generation="3.0",
    input_price=15.00,
    output_price=75.00,
    max_output_tokens=4_096,
    context_window=200_000,
    description="Legacy Opus 3 (use opus-4.6 instead)",
    deprecated=True,
)

CLAUDE_HAIKU_3 = ModelDef(
    model_id="claude-3-haiku-20240307",
    aliases=("haiku-3", "claude-3-haiku", "claude-3-haiku-20240307"),
    tier="haiku",
    generation="3.0",
    input_price=0.25,
    output_price=1.25,
    max_output_tokens=4_096,
    context_window=200_000,
    description="Legacy Haiku 3 (use haiku-4.5 instead)",
    deprecated=True,
)

CLAUDE_SONNET_3 = ModelDef(
    model_id="claude-3-sonnet-20240229",
    aliases=("sonnet-3", "claude-3-sonnet", "claude-3-sonnet-20240229"),
    tier="sonnet",
    generation="3.0",
    input_price=3.00,
    output_price=15.00,
    max_output_tokens=4_096,
    context_window=200_000,
    description="Legacy Sonnet 3 (use sonnet-4.5 instead)",
    deprecated=True,
)


# ============================================================================
# Registry
# ============================================================================

# All known models, ordered by preference (latest first)
ALL_MODELS: Tuple[ModelDef, ...] = (
    CLAUDE_OPUS_4_6,
    CLAUDE_SONNET_4_5,
    CLAUDE_HAIKU_4_5,
    # Legacy
    CLAUDE_SONNET_3_5,
    CLAUDE_HAIKU_3_5,
    CLAUDE_OPUS_3,
    CLAUDE_HAIKU_3,
    CLAUDE_SONNET_3,
)

# Current-generation models only
CURRENT_MODELS: Tuple[ModelDef, ...] = tuple(m for m in ALL_MODELS if not m.deprecated)

# Build lookup tables
_MODEL_BY_ID: Dict[str, ModelDef] = {m.model_id: m for m in ALL_MODELS}
_MODEL_BY_ALIAS: Dict[str, ModelDef] = {}
for _m in ALL_MODELS:
    for _alias in _m.aliases:
        _MODEL_BY_ALIAS[_alias.lower()] = _m
    _MODEL_BY_ALIAS[_m.model_id.lower()] = _m

# Valid choices for CLI --model argument
MODEL_CHOICES: List[str] = sorted(set(
    [m.model_id for m in ALL_MODELS] +
    [a for m in ALL_MODELS for a in m.aliases]
))


# ============================================================================
# Default Model
# ============================================================================

# The default model used when nothing else is specified.
# Override via CLAUDE_MODEL env var or --model CLI flag.
DEFAULT_MODEL_ID: str = CLAUDE_HAIKU_4_5.model_id
DEFAULT_MODEL_DEF: ModelDef = CLAUDE_HAIKU_4_5


# ============================================================================
# Public API
# ============================================================================

def resolve_model(model_input: str) -> str:
    """
    Resolve a model name/alias/ID to the canonical API model ID.

    Accepts short names like "opus", "sonnet", "haiku" or full IDs.
    Returns the canonical model_id string for use with the API.

    Raises ValueError if the model is not recognized.
    """
    lookup = model_input.strip().lower()
    model_def = _MODEL_BY_ALIAS.get(lookup)

    if model_def is None:
        available = ", ".join(m.model_id for m in CURRENT_MODELS)
        raise ValueError(
            f"Unknown model: '{model_input}'. "
            f"Available models: {available}. "
            f"Short names: opus, sonnet, haiku"
        )

    if model_def.deprecated:
        import logging
        logging.getLogger(__name__).warning(
            f"Model '{model_def.model_id}' is deprecated. "
            f"Consider upgrading to a current model."
        )

    return model_def.model_id


def get_model_def(model_input: str) -> ModelDef:
    """
    Resolve a model name/alias/ID and return the full ModelDef.
    """
    model_id = resolve_model(model_input)
    return _MODEL_BY_ID[model_id]


def get_default_model() -> str:
    """
    Get the default model ID, respecting the CLAUDE_MODEL env var.

    Priority:
        1. CLAUDE_MODEL environment variable (resolved via aliases)
        2. DEFAULT_MODEL_ID constant
    """
    env_model = os.environ.get("CLAUDE_MODEL", "").strip()
    if env_model:
        try:
            return resolve_model(env_model)
        except ValueError:
            import logging
            logging.getLogger(__name__).warning(
                f"CLAUDE_MODEL env var '{env_model}' is not recognized. "
                f"Falling back to default: {DEFAULT_MODEL_ID}"
            )
    return DEFAULT_MODEL_ID


def get_model_max_tokens(model_input: str, stage: str = "analysis") -> int:
    """
    Get recommended max_tokens for a model and analysis stage.

    Larger models produce richer output and need higher token limits
    to avoid truncating structured JSON responses.

    Stages:
        - "prioritization": File selection (moderate output)
        - "analysis": Deep dive per-file analysis (largest output)
        - "synthesis": Final report synthesis (large output)
        - "payload": Payload generation (moderate output)
        - "annotation": Code annotation (moderate output)
        - "threat_modeling": Threat model report (large output)
    """
    try:
        model_def = get_model_def(model_input)
    except ValueError:
        model_def = DEFAULT_MODEL_DEF

    # Base tokens by model tier
    # These must be generous enough for full structured JSON output.
    # All current models support 64K+ output, so headroom is cheap.
    tier_base = {
        "opus":   {"prioritization": 6000, "analysis": 12000, "synthesis": 12000, "payload": 6000, "annotation": 6000, "threat_modeling": 12000},
        "sonnet": {"prioritization": 5000, "analysis": 10000, "synthesis": 10000, "payload": 5000, "annotation": 5000, "threat_modeling": 10000},
        "haiku":  {"prioritization": 4000, "analysis": 8000,  "synthesis": 8000,  "payload": 4000, "annotation": 4000, "threat_modeling": 8000},
    }

    tier_tokens = tier_base.get(model_def.tier, tier_base["haiku"])
    return tier_tokens.get(stage, 4096)


def get_model_pricing(model_input: str) -> Tuple[float, float]:
    """
    Get pricing for a model as (input_price_per_1M, output_price_per_1M).

    Falls back to default pricing if model is not recognized.
    """
    try:
        model_def = get_model_def(model_input)
        return (model_def.input_price, model_def.output_price)
    except ValueError:
        # Unknown model - return conservative default (Haiku 4.5 rates)
        return (DEFAULT_MODEL_DEF.input_price, DEFAULT_MODEL_DEF.output_price)


def get_pricing_dict() -> Dict[str, Tuple[float, float]]:
    """
    Get a dictionary of all model pricing for backwards compatibility.

    Returns: {model_id: (input_price, output_price), ...}
    """
    return {m.model_id: (m.input_price, m.output_price) for m in ALL_MODELS}


def list_models(include_deprecated: bool = False) -> List[ModelDef]:
    """List available models, optionally including deprecated ones."""
    if include_deprecated:
        return list(ALL_MODELS)
    return list(CURRENT_MODELS)


def model_help_text() -> str:
    """Generate help text for CLI --model argument."""
    lines = ["Available models:"]

    lines.append("  Current:")
    for m in CURRENT_MODELS:
        aliases = ", ".join(a for a in m.aliases if a != m.model_id)
        lines.append(f"    {m.model_id:<40} {m.description}")
        lines.append(f"      aliases: {aliases}")
        lines.append(f"      pricing: ${m.input_price:.2f}/${m.output_price:.2f} per 1M tokens (in/out)")

    lines.append("")
    lines.append("  Legacy (still supported):")
    for m in ALL_MODELS:
        if m.deprecated:
            lines.append(f"    {m.model_id:<40} {m.description}")

    lines.append("")
    lines.append(f"  Default: {DEFAULT_MODEL_ID}")
    lines.append(f"  Override: export CLAUDE_MODEL=opus  (or --model opus)")

    return "\n".join(lines)


def model_cli_help() -> str:
    """Short help string for CLI --model argument."""
    default = get_default_model()
    return (
        f"Claude model to use (default: {default}). "
        f"Shortcuts: opus, sonnet, haiku. "
        f"Env var: CLAUDE_MODEL"
    )
