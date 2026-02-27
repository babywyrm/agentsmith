#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Composes AI prompts from base + profile sections for modular, maintainable prompts.

When multiple profiles are active, their sections are merged into a single prompt
per file — reducing API calls and cost while preserving all analysis guidance.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional


PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
BASE_DIR = PROMPTS_DIR / "base"
PROFILES_DIR = PROMPTS_DIR / "profiles"


def _read_if_exists(path: Path) -> str:
    """Read file or return empty string."""
    if path.is_file():
        return path.read_text(encoding="utf-8").strip()
    return ""


def get_base_prompt() -> str:
    """Load and concatenate base prompt components."""
    preamble = _read_if_exists(BASE_DIR / "system_preamble.txt")
    schema = _read_if_exists(BASE_DIR / "output_schema.txt")
    if not preamble and not schema:
        return ""
    parts = [p for p in [preamble, schema] if p]
    return "\n\n".join(parts)


def get_profile_section(profile: str) -> Optional[str]:
    """Load profile-specific section if it exists."""
    section_file = PROFILES_DIR / f"{profile}_sections.txt"
    content = _read_if_exists(section_file)
    return content if content else None


def compose_prompt(
    profile_names: List[str],
    use_legacy_fallback: bool = True,
) -> Optional[str]:
    """
    Compose a single prompt from base + all profile sections.

    Args:
        profile_names: List of profile names (e.g. ["owasp", "springboot"])
        use_legacy_fallback: If True, when no sections exist, return None so
            caller can use legacy full templates.

    Returns:
        Composed prompt string, or None if composition not possible
        (e.g. base missing, or all profiles use legacy only).
    """
    base = get_base_prompt()
    if not base:
        return None

    sections: List[str] = []
    for name in profile_names:
        section = get_profile_section(name)
        if section:
            sections.append(section)

    if not sections and use_legacy_fallback:
        return None

    if sections:
        profile_block = "\n\n---\n\n".join(sections)
        return f"{base}\n\n═══════════════════════════════════════════════════════════════════════════\nPROFILE-SPECIFIC GUIDANCE\n═══════════════════════════════════════════════════════════════════════════\n\n{profile_block}\n\nCODE TO ANALYZE:\n{{code}}"
    return base + "\n\nCODE TO ANALYZE:\n{code}"


def get_merged_prompt(
    profile_names: List[str],
    legacy_templates: Dict[str, str],
) -> Optional[str]:
    """
    Get merged prompt for multiple profiles, or None if should use per-profile legacy.

    When multiple profiles are active and we have composed content, returns
    a single merged prompt. Otherwise returns None — caller should iterate
    per-profile with legacy templates.
    """
    # Exclude attacker — it uses a different flow (full repo, not per-file)
    file_profiles = [p for p in profile_names if p != "attacker"]
    if not file_profiles:
        return None

    composed = compose_prompt(file_profiles, use_legacy_fallback=True)
    if composed:
        return composed

    # If only one profile and we have legacy, we'll use that in the normal flow
    # If multiple profiles but no sections, we need to merge legacy templates
    if len(file_profiles) > 1:
        # Merge legacy templates: concatenate profile-specific parts
        merged_parts = []
        for p in file_profiles:
            tpl = legacy_templates.get(p)
            if tpl:
                # Extract the "guidance" part (everything before CODE TO ANALYZE)
                if "CODE TO ANALYZE:" in tpl:
                    guidance = tpl.split("CODE TO ANALYZE:")[0].strip()
                else:
                    guidance = tpl
                merged_parts.append(guidance)
        if merged_parts:
            # Use first template's structure but combine guidance
            first = legacy_templates.get(file_profiles[0], "")
            if "{code}" in first:
                combined_guidance = "\n\n---\n\n".join(merged_parts)
                return f"{combined_guidance}\n\nCODE TO ANALYZE:\n{{code}}"
    return None


def has_composed_support(profile_names: List[str]) -> bool:
    """True if we have base + at least one profile section for these profiles."""
    if not get_base_prompt():
        return False
    file_profiles = [p for p in profile_names if p != "attacker"]
    return any(get_profile_section(p) for p in file_profiles)
