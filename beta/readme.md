# Smart Code Analyzer

AI-powered code analysis tool using Claude 3.5 Haiku for security, performance, and architecture reviews.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set API key
export CLAUDE_API_KEY="your_key_here"

# Run analysis
python3 smart__.py /path/to/repo "find security vulnerabilities"
```

## Installation

```bash
pip install rich anthropic typing-inspection
export CLAUDE_API_KEY="your_api_key_here"
```

## Usage Examples

### Basic Security Scan
```bash
python3 smart__.py /path/to/repo "find all security vulnerabilities"
```

### CTF Mode (Exploitation-Focused)
```bash
python3 smart__.py /path/to/ctf-challenge \
  "find vulnerabilities and flags" \
  --ctf-mode \
  --top-n 10 \
  --generate-payloads
```

**CTF Mode**: Optimized for Capture The Flag challenges. Focuses on exploitable vulnerabilities, quick wins, and provides exploitation payloads with step-by-step guides.

### Security Analysis with Payloads
```bash
python3 smart__.py /path/to/app \
  "find injection vulnerabilities" \
  --generate-payloads \
  --top-n 5 \
  --annotate-code
```

### Resume Previous Review
```bash
# List reviews
python3 smart__.py . --list-reviews

# Resume last matching review
python3 smart__.py /path/to/repo "question" --resume-last

# Resume by ID
python3 smart__.py /path/to/repo --resume-review <review_id>
```

### Review State Management
```bash
# Start with state tracking
python3 smart__.py /path/to/repo "question" --enable-review-state

# Print past review
python3 smart__.py . --print-review <review_id> --verbose-review
```

### Cache Management
```bash
python3 smart__.py . --cache-info      # Show stats
python3 smart__.py . --cache-clear     # Clear cache
python3 smart__.py . --cache-prune 30  # Remove old entries
```

## Key Features

- **Multi-Stage Analysis**: Prioritization → Deep Dive → Synthesis
- **CTF Mode**: Exploitation-focused analysis with payloads and exploitation steps
- **Review State**: Resume interrupted reviews, track progress
- **API Caching**: Speed up repeated runs
- **Cost Tracking**: Monitor API usage and costs
- **Multiple Formats**: Console, HTML, Markdown, JSON output

## Common Options

| Option | Description |
|--------|-------------|
| `--ctf-mode` | Enable CTF mode (exploitation-focused) |
| `--generate-payloads` | Generate exploitation/test payloads |
| `--annotate-code` | Add code annotations with fixes |
| `--top-n N` | Limit payload/annotation generation to top N findings |
| `--enable-review-state` | Enable review state tracking |
| `--resume-last` | Auto-resume last matching review |
| `--include-yaml` | Include YAML files in analysis |
| `--verbose` / `-v` | Show detailed findings with code context |
| `--debug` | Show raw API responses |
| `--help-examples` | Show comprehensive usage examples |

## CTF Mode vs Regular Mode

**Regular Mode**: General security analysis focused on remediation
- Prioritizes files relevant to your question
- Provides remediation recommendations
- Generates Red/Blue team payloads for testing

**CTF Mode**: Exploitation-focused analysis for quick wins
- Prioritizes vulnerable entry points (login, upload, configs)
- Focuses on exploitable vulnerabilities
- Provides exploitation payloads with step-by-step guides
- Highlights flags, secrets, and hardcoded credentials
- Uses separate cache namespace (`ctf/`)

## How It Works

1. **Prioritization**: AI identifies most relevant files for your question
2. **Deep Dive**: Analyzes prioritized files for vulnerabilities/issues
3. **Synthesis**: Creates context-aware report (threat model, performance profile, etc.)
4. **Optional**: Generates payloads, annotations, or optimized code

## Review State & Caching

- **Review State**: Saves progress, allows resuming, generates context files
- **API Cache**: Stores API responses, speeds up repeated runs
- **Change Detection**: Automatically detects codebase changes
- **Checkpoints**: Saves progress at each stage

Cache location: `.scrynet_cache/`
- Reviews: `.scrynet_cache/reviews/`
- API Cache: `.scrynet_cache/api_cache/` (separate for `smart/` and `ctf/` modes)

## Help & Examples

```bash
# Standard help
python3 smart__.py -h

# Comprehensive examples
python3 smart__.py --help-examples
```

## Architecture

Modular design:
- `smart__.py` - Main orchestrator
- `models.py` - Data models
- `prompts.py` / `ctf_prompts.py` - Prompt templates
- `scrynet_context.py` - Context management (reviews, cache, costs)
- `output_manager.py` - Output formatting
- `common.py` - Shared utilities

## Cost Tracking

Shows API usage after each run:
```
API Calls: 15
Cache Hits: 8
Total Tokens: 57,680
Estimated Cost: $0.052
```

Cache hits don't count toward costs. Use `--no-cache` to force fresh API calls.

---

For detailed examples and workflows, run: `python3 smart__.py --help-examples`
