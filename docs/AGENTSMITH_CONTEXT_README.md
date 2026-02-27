# Agent Smith Context Library

> **Location**: `lib/agentsmith_context.py`

Unified interface for review state, API caching, and cost tracking.

## Core Classes

| Class | Purpose |
|-------|---------|
| `ReviewContextManager` | Main entry point — creates/loads/resumes reviews, manages cache, tracks costs |
| `ReviewState` | A review session: ID, repo path, fingerprint, question, status, checkpoints, findings |
| `ReviewCheckpoint` | Saved stage progress (prioritization, deep_dive, synthesis) |
| `CachedResponse` | Cached API response with parsed result and token counts |
| `CostTracker` | Token usage and cost estimation |

## Quick Start

```python
from lib.agentsmith_context import ReviewContextManager

ctx = ReviewContextManager(
    cache_dir=".agentsmith_cache",
    use_cache=True,
    enable_cost_tracking=True
)

# Create or resume a review
review = ctx.create_review(repo_path=".", question="Find security vulnerabilities")

# Cache an API response
cached = ctx.get_cached_response("deep_dive", prompt, repo_path=".", model="claude-haiku-4-5-20251001")
if not cached:
    response = make_api_call(prompt)
    ctx.save_response("deep_dive", prompt, response, repo_path=".", model="claude-haiku-4-5-20251001",
                       input_tokens=1000, output_tokens=500)

# Track costs
ctx.track_cost(input_tokens=1000, output_tokens=500, cached=False)
summary = ctx.get_cost_summary("claude-haiku-4-5-20251001")
```

## Key Operations

### Reviews

```python
review = ctx.create_review(repo_path, question)
review = ctx.load_review(review_id)
review_id = ctx.find_matching_review(repo_path)       # Match by fingerprint
ctx.add_checkpoint(review_id, "deep_dive", data, files_analyzed=[...])
ctx.update_findings(review_id, findings_list)
ctx.mark_completed(review_id)
reviews = ctx.list_reviews(status="in_progress")       # Optional filter
```

### Caching

```python
cached = ctx.get_cached_response(stage, prompt, file=None, repo_path=None, model=None)
ctx.save_response(stage, prompt, raw_response, parsed=None, file=None, ...)
stats = ctx.cache_stats()                               # {"files": N, "bytes_mb": ...}
ctx.prune_cache(days=30)
ctx.clear_cache()
```

### Cost Tracking

```python
ctx.track_cost(input_tokens=1000, output_tokens=500, cached=False)
summary = ctx.get_cost_summary("claude-haiku-4-5-20251001")
# {"api_calls": 10, "cache_hits": 5, "total_tokens": 75000, "estimated_cost_usd": 0.12}
```

### Directory Fingerprinting

```python
fingerprint = ctx.compute_dir_fingerprint(repo_path)
changed, current_fp = ctx.detect_changes(repo_path, stored_fingerprint)
```

## Storage Layout

```
.agentsmith_cache/
├── reviews/
│   ├── <review_id>.json
│   └── _<review_id>_context.md
└── api_cache/
    └── <repo_fingerprint>/<model>/<hash>.json
```

Cache is namespaced by (repo_fingerprint, model). Keys are SHA256 of `stage|file|prompt`.

## CLI Access

```bash
python3 agentsmith.py analyze . --list-reviews
python3 agentsmith.py analyze . --cache-info
python3 agentsmith.py analyze . --cache-clear
```

See [REVIEW_STATE.md](REVIEW_STATE.md) for the user-facing guide.

## Example

See `tests/agentsmith_context_example.py` for a complete working example.
