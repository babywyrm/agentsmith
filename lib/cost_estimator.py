#!/usr/bin/env python3
"""
Cost estimation utility for SCRYNET scans.

Estimates API costs before running a scan based on:
- Number of files
- File sizes (approximate token counts)
- Profiles enabled
- Features enabled (prioritization, payloads, annotations)
"""

from typing import List, Dict, Optional
from pathlib import Path
from lib.cost_tracker import MODEL_PRICING, DEFAULT_PRICING


# Average tokens per line of code (approximate)
TOKENS_PER_LINE = 1.5

# Average prompt overhead (system prompt + instructions)
PROMPT_OVERHEAD = {
    "prioritization": 500,
    "analysis": 800,  # Profile-specific prompts have overhead
    "payload_generation": 600,
    "annotation": 600,
    "threat_modeling": 1000,
}

# Average output tokens per call (based on typical responses)
AVG_OUTPUT_TOKENS = {
    "prioritization": 1500,
    "analysis": 2000,  # Typical finding summaries
    "payload_generation": 1200,
    "annotation": 1500,
    "threat_modeling": 3000,
}


def estimate_file_tokens(file_path: Path) -> int:
    """Estimate input tokens for a file based on its size."""
    try:
        # Read first few lines to get average line length
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            if not lines:
                return 0
            
            # Estimate: ~1.5 tokens per line on average
            # Account for prompt overhead per file
            estimated_tokens = len(lines) * TOKENS_PER_LINE
            return int(estimated_tokens)
    except Exception:
        # Fallback: use file size in bytes / 4 (rough approximation)
        try:
            return int(file_path.stat().st_size / 4)
        except Exception:
            return 1000  # Default estimate


def estimate_scan_cost(
    files: List[Path],
    model: str,
    profiles: List[str],
    prioritize: bool = False,
    prioritize_top: int = 15,
    generate_payloads: bool = False,
    annotate_code: bool = False,
    top_n: int = 5,
    threat_model: bool = False
) -> Dict[str, any]:
    """
    Estimate total cost for a scan.
    
    Returns a dictionary with:
    - total_estimated_cost: float
    - breakdown_by_stage: Dict[str, Dict]
    - estimated_calls: int
    - estimated_tokens: Dict[str, int]
    """
    pricing = MODEL_PRICING.get(model, DEFAULT_PRICING)
    input_price, output_price = pricing
    
    total_input_tokens = 0
    total_output_tokens = 0
    total_calls = 0
    breakdown = {}
    
    # 1. Prioritization (if enabled)
    if prioritize and len(files) > prioritize_top:
        prioritization_input = PROMPT_OVERHEAD["prioritization"]
        # Add tokens for file list (approx 20 tokens per file path)
        prioritization_input += len(files) * 20
        
        prioritization_output = AVG_OUTPUT_TOKENS["prioritization"]
        
        total_input_tokens += prioritization_input
        total_output_tokens += prioritization_output
        total_calls += 1
        
        cost = (prioritization_input / 1_000_000) * input_price + (prioritization_output / 1_000_000) * output_price
        breakdown["prioritization"] = {
            "calls": 1,
            "input_tokens": prioritization_input,
            "output_tokens": prioritization_output,
            "total_tokens": prioritization_input + prioritization_output,
            "cost": cost
        }
        
        # Use prioritized files for analysis estimate
        analysis_files = files[:prioritize_top]
    else:
        analysis_files = files
    
    # 2. Analysis (per profile, per file)
    analysis_input_total = 0
    analysis_output_total = 0
    analysis_calls = 0
    
    for profile in profiles:
        profile_input = 0
        profile_output = 0
        profile_calls = 0
        
        for file_path in analysis_files:
            # Estimate tokens per file
            file_tokens = estimate_file_tokens(file_path)
            
            # Add prompt overhead per file
            per_file_input = PROMPT_OVERHEAD["analysis"] + file_tokens
            per_file_output = AVG_OUTPUT_TOKENS["analysis"]
            
            profile_input += per_file_input
            profile_output += per_file_output
            profile_calls += 1
        
        analysis_input_total += profile_input
        analysis_output_total += profile_output
        analysis_calls += profile_calls
        
        cost = (profile_input / 1_000_000) * input_price + (profile_output / 1_000_000) * output_price
        breakdown[f"analysis_{profile}"] = {
            "calls": profile_calls,
            "input_tokens": profile_input,
            "output_tokens": profile_output,
            "total_tokens": profile_input + profile_output,
            "cost": cost
        }
    
    total_input_tokens += analysis_input_total
    total_output_tokens += analysis_output_total
    total_calls += analysis_calls
    
    # Combine all analysis into one entry for summary
    analysis_cost = (analysis_input_total / 1_000_000) * input_price + (analysis_output_total / 1_000_000) * output_price
    breakdown["analysis"] = {
        "calls": analysis_calls,
        "input_tokens": analysis_input_total,
        "output_tokens": analysis_output_total,
        "total_tokens": analysis_input_total + analysis_output_total,
        "cost": analysis_cost,
        "files": len(analysis_files),
        "profiles": len(profiles)
    }
    
    # 3. Payload Generation (if enabled)
    if generate_payloads:
        # Estimate based on top_n findings
        payload_calls = top_n
        payload_input = PROMPT_OVERHEAD["payload_generation"] * payload_calls
        payload_output = AVG_OUTPUT_TOKENS["payload_generation"] * payload_calls
        
        total_input_tokens += payload_input
        total_output_tokens += payload_output
        total_calls += payload_calls
        
        cost = (payload_input / 1_000_000) * input_price + (payload_output / 1_000_000) * output_price
        breakdown["payload_generation"] = {
            "calls": payload_calls,
            "input_tokens": payload_input,
            "output_tokens": payload_output,
            "total_tokens": payload_input + payload_output,
            "cost": cost
        }
    
    # 4. Annotation (if enabled)
    if annotate_code:
        # Estimate based on top_n findings
        annotation_calls = top_n
        annotation_input = PROMPT_OVERHEAD["annotation"] * annotation_calls
        annotation_output = AVG_OUTPUT_TOKENS["annotation"] * annotation_calls
        
        total_input_tokens += annotation_input
        total_output_tokens += annotation_output
        total_calls += annotation_calls
        
        cost = (annotation_input / 1_000_000) * input_price + (annotation_output / 1_000_000) * output_price
        breakdown["annotation"] = {
            "calls": annotation_calls,
            "input_tokens": annotation_input,
            "output_tokens": annotation_output,
            "total_tokens": annotation_input + annotation_output,
            "cost": cost
        }
    
    # 5. Threat Modeling (if enabled)
    if threat_model:
        # Threat modeling analyzes all files together
        threat_input = PROMPT_OVERHEAD["threat_modeling"]
        # Add all file tokens
        for file_path in files:
            threat_input += estimate_file_tokens(file_path)
        
        threat_output = AVG_OUTPUT_TOKENS["threat_modeling"]
        
        total_input_tokens += threat_input
        total_output_tokens += threat_output
        total_calls += 1
        
        cost = (threat_input / 1_000_000) * input_price + (threat_output / 1_000_000) * output_price
        breakdown["threat_modeling"] = {
            "calls": 1,
            "input_tokens": threat_input,
            "output_tokens": threat_output,
            "total_tokens": threat_input + threat_output,
            "cost": cost
        }
    
    # Calculate total cost
    total_cost = (total_input_tokens / 1_000_000) * input_price + (total_output_tokens / 1_000_000) * output_price
    
    return {
        "total_estimated_cost": total_cost,
        "total_calls": total_calls,
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "total_tokens": total_input_tokens + total_output_tokens,
        "breakdown_by_stage": breakdown,
        "model": model,
        "model_pricing": {
            "input_per_1M": input_price,
            "output_per_1M": output_price
        }
    }


