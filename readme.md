# 🔍 SCRYNET - Unified Security Scanner

> Do you hate reviews?  
> Do you love CTFs?  
> Do you hate java controllers?  
> Do you love having more time to not look at screens?  
> Do you miss the 90s?

---

**SCRYNET** is a comprehensive, multi-mode security scanning tool that combines fast static analysis with AI-powered contextual analysis. It supports multiple scanning modes optimized for different use cases, from quick CI/CD checks to deep security audits.

## ✨ What's New

- **🎯 AI Prioritization**: Automatically selects top N most relevant files (saves time & API costs)
- **💣 Payload Generation**: Creates Red/Blue team payloads for vulnerability verification
- **📝 Code Annotations**: Shows vulnerable code with inline fixes and recommendations
- **🌈 Rich UI**: Beautiful colors, spinners, and progress bars with real-time feedback
- **📄 Multiple Export Formats**: JSON, CSV, Markdown, and HTML reports
- **📍 Precise Location Tracking**: File paths and line numbers in all outputs
- **🔄 Unified CLI**: Single entry point (`scrynet.py`) for all modes

## 🚀 Features

### Core Capabilities

- **Multi-Language Support**: Go, JavaScript, Python, Java, PHP, HTML, YAML, Helm templates
- **Multiple Scanning Modes**: Static-only, AI-powered analysis, CTF-focused, and hybrid
- **OWASP Top 10 Coverage**: Comprehensive security rule sets
- **AI-Powered Analysis**: Claude AI integration for contextual vulnerability detection
- **🎯 Smart Prioritization**: AI selects most relevant files (saves time & cost)
- **💣 Payload Generation**: Red/Blue team payloads for verification
- **📝 Code Annotations**: Inline code fixes and recommendations
- **🌈 Rich UI**: Colors, spinners, progress bars, real-time feedback
- **Review State Management**: Resume interrupted reviews, track progress
- **API Caching**: Speed up repeated runs with intelligent caching
- **Cost Tracking**: Monitor API usage and costs
- **Multiple Output Formats**: Console, HTML, Markdown, JSON, CSV
- **📍 Precise Tracking**: File paths and line numbers in all outputs

## 🔧 Installation

### 1. Build the Go Scanner

```bash
git clone https://github.com/babywyrm/scrynet.git
cd gowasp

# Build the scanner binary
go build -o scanner scrynet.go
```

### 2. Set up Python Environment

```bash
# Install dependencies
pip install -r requirements.txt

# Set your API key (required for AI modes)
export CLAUDE_API_KEY="sk-ant-api03-..."
```

## 📖 Usage

SCRYNET provides a unified entry point with multiple scanning modes:

### Unified Entry Point

**`scrynet.py` is the main entry point for all SCRYNET operations.**

```bash
cd gowasp
python3 scrynet.py <mode> [options]
```

### Available Modes

#### 1. Static Mode (Fast, Free)

Fast static analysis using only the Go scanner - perfect for CI/CD:

```bash
python3 scrynet.py static /path/to/repo --severity HIGH --output json
```

**Features:**
- No API costs
- Very fast execution
- CI/CD friendly
- Custom rule sets

**Options:**
- `--rules`: Comma-separated rule files
- `--severity`: Minimum severity (CRITICAL, HIGH, MEDIUM, LOW)
- `--output`: Output format (text, json, markdown)
- `--verbose`: Show remediation advice
- `--git-diff`: Scan only changed files
- `--ignore`: Comma-separated glob patterns

#### 2. Analyze Mode (AI-Powered)

Comprehensive AI analysis with multi-stage pipeline:

```bash
python3 scrynet.py analyze /path/to/repo "find security vulnerabilities" \
  --generate-payloads \
  --top-n 10 \
  --enable-review-state
```

**Features:**
- Multi-stage analysis (Prioritization → Deep Dive → Synthesis)
- Review state management
- API caching
- Cost tracking
- Multiple output formats

**Key Options:**
- `--ctf-mode`: Enable CTF-focused analysis (see CTF Mode below)
- `--generate-payloads`: Generate exploitation/test payloads
- `--annotate-code`: Add code annotations with fixes
- `--top-n N`: Limit to top N findings
- `--enable-review-state`: Enable review state tracking
- `--resume-last`: Auto-resume last matching review
- `--include-yaml`: Include YAML files
- `--include-helm`: Include Helm templates
- `--format`: Output formats (console, html, markdown, json)

#### 3. CTF Mode (Exploitation-Focused)

Optimized for Capture The Flag challenges:

```bash
python3 scrynet.py ctf /path/to/ctf "find all vulnerabilities" \
  --generate-payloads \
  --top-n 10
```

**Features:**
- Prioritizes entry points (login, upload, APIs)
- Focuses on exploitable vulnerabilities
- Generates CTF-ready exploitation payloads
- Highlights potential flags and secrets
- Separate cache namespace

#### 4. Hybrid Mode (Static + AI) ⚡ **RECOMMENDED**

Combines fast static scanning with AI analysis - best of both worlds:

```bash
python3 scrynet.py hybrid /path/to/repo ./scanner \
  --profile owasp \
  --prioritize \
  --prioritize-top 20 \
  --question "find SQL injection vulnerabilities" \
  --generate-payloads \
  --annotate-code \
  --top-n 10 \
  --export-format json html markdown \
  --output-dir ./reports \
  --verbose
```

**Features:**
- Runs Go scanner + AI analysis
- **AI Prioritization**: Selects top N most relevant files (saves time & cost)
- **Payload Generation**: Creates Red/Blue team payloads for verification
- **Code Annotations**: Shows vulnerable code with inline fixes
- Merges and deduplicates findings
- Multiple AI profiles
- Threat modeling support
- **Rich UI**: Colors, spinners, progress bars, real-time feedback
- **Multiple Export Formats**: JSON, CSV, Markdown, HTML

**Key Options:**
- `--profile`: AI analysis profiles (comma-separated, default: owasp)
- `--prioritize`: Enable AI prioritization (HIGHLY RECOMMENDED for 50+ files)
- `--prioritize-top N`: Number of files to prioritize (default: 15)
- `--question "..."`: Guides prioritization (be specific!)
- `--generate-payloads`: Generate Red/Blue team payloads
- `--annotate-code`: Generate annotated code snippets
- `--top-n N`: Number of findings for payloads/annotations (default: 5)
- `--export-format`: Report formats (json, csv, markdown, html)
- `--output-dir`: Custom output directory (default: ./output)
- `--static-rules`: Static rule files
- `--severity`: Minimum severity filter
- `--threat-model`: Perform threat modeling
- `--parallel`: Run AI analysis in parallel
- `--verbose`: Show colors, spinners, and detailed progress

## 🎯 Examples

### Quick Security Scan

```bash
# Fast static scan
python3 scrynet.py static . --severity HIGH

# Comprehensive AI analysis
python3 scrynet.py analyze . "find security vulnerabilities" \
  --top-n 5 \
  --generate-payloads
```

### CTF Challenge Analysis

```bash
python3 scrynet.py ctf ./ctf-challenge \
  "find all exploitable vulnerabilities" \
  --ctf-mode \
  --generate-payloads \
  --top-n 15 \
  --max-files 20
```

### Resume Previous Review

```bash
# List available reviews
python3 scrynet.py analyze . --list-reviews

# Resume last matching review
python3 scrynet.py analyze /path/to/repo "question" --resume-last

# Resume by ID
python3 scrynet.py analyze /path/to/repo --resume-review abc123def456
```

### Hybrid Analysis (Recommended)

```bash
# Focused SQL Injection Hunt with Prioritization
python3 scrynet.py hybrid /path/to/repo ./scanner \
  --profile owasp \
  --prioritize \
  --prioritize-top 20 \
  --question "find SQL injection vulnerabilities in database queries" \
  --generate-payloads \
  --annotate-code \
  --top-n 10 \
  --export-format json html markdown \
  --verbose

# Comprehensive Security Audit
python3 scrynet.py hybrid /path/to/repo ./scanner \
  --profile owasp \
  --prioritize \
  --prioritize-top 25 \
  --question "find authentication bypass and broken access control" \
  --generate-payloads \
  --annotate-code \
  --top-n 15 \
  --export-format json html \
  --output-dir ./security-reports \
  --verbose

# Fast Parallel Analysis (Large Repos)
python3 scrynet.py hybrid /path/to/repo ./scanner \
  --profile owasp \
  --prioritize \
  --prioritize-top 15 \
  --parallel \
  --verbose
```

## 📁 Project Structure

```
gowasp/
├── scrynet.py              # ⭐ MAIN ENTRY POINT - Use this!
├── smart_analyzer.py       # AI-powered analyzer
├── ctf_analyzer.py         # CTF-focused analyzer
├── orchestrator.py          # Hybrid static + AI orchestrator
├── scanner                 # Go scanner binary
├── scrynet.go              # Go scanner source
├── rules/                  # Security rule sets
│   ├── rules_core.json
│   ├── rules_secrets.json
│   └── ...
├── lib/                    # Shared Python library
│   ├── common.py           # Utilities
│   ├── models.py           # Data models
│   ├── output_manager.py   # Output formatting
│   ├── scrynet_context.py # Caching & review state
│   ├── prompts.py          # Prompt factories
│   └── ctf_prompts.py      # CTF prompts
├── prompts/                # Text-based prompt templates
│   ├── owasp_profile.txt
│   ├── attacker_profile.txt
│   └── performance_profile.txt
├── test_targets/           # Test applications
│   ├── DVWA/
│   └── WebGoat/
├── tests/                  # Test suite
├── output/                 # Analysis results (gitignored)
├── test-reports/           # Test report outputs (gitignored)
└── security-reports/       # Custom report outputs (gitignored)
```

## 🔍 Review State & Caching

### Review State Management

SCRYNET can save and resume analysis sessions:

```bash
# Start with state tracking
python3 scrynet.py analyze /path/to/repo "question" --enable-review-state

# Resume last review
python3 scrynet.py analyze /path/to/repo "question" --resume-last

# List all reviews
python3 scrynet.py analyze . --list-reviews
```

**Features:**
- Automatic checkpointing at each stage
- Change detection (warns if codebase changed)
- Context file generation for Cursor/Claude
- Progress tracking

### API Caching

Caching speeds up repeated runs:

```bash
# View cache stats
python3 scrynet.py analyze . --cache-info

# Clear cache
python3 scrynet.py analyze . --cache-clear

# Prune old entries
python3 scrynet.py analyze . --cache-prune 30
```

Cache location: `.scrynet_cache/`
- Reviews: `.scrynet_cache/reviews/`
- API Cache: `.scrynet_cache/api_cache/` (namespaced by mode)

## 💰 Cost Tracking

After each AI-powered run, you'll see a cost summary:

```
API Usage Summary
┌──────────────┬─────────┐
│ Metric       │ Value   │
├──────────────┼─────────┤
│ API Calls    │ 15      │
│ Cache Hits   │ 8       │
│ Total Tokens │ 57,680  │
│ Estimated Cost │ $0.052│
└──────────────┴─────────┘
```

**Tips:**
- Cache hits don't count toward token usage
- Resume reviews to maximize cache hits
- Use `--no-cache` to force fresh API calls

## 🎉 Tips for Effective Scanning

1. **For CI/CD**: Use `static` mode with `--severity HIGH` for fast, free checks
2. **For Deep Reviews**: Use `analyze` mode with `--enable-review-state`
3. **For CTF Challenges**: Use `ctf` mode for quick vulnerability discovery
4. **For Comprehensive Analysis**: Use `hybrid` mode with `--prioritize` (RECOMMENDED)
5. **Save Time & Cost**: Always use `--prioritize` for repos with 50+ files
6. **Be Specific**: Use detailed `--question` for better prioritization results
7. **Get Actionable Results**: Combine `--generate-payloads` + `--annotate-code` for full context
8. **Start Focused**: Begin with `--severity HIGH` to tackle critical issues first
9. **Reduce Noise**: Use `--ignore` or `.scannerignore` to exclude test files
10. **Resume Reviews**: Use `--resume-last` to continue where you left off

### Understanding Prioritization

- `--prioritize-top N`: AI selects top N files to analyze (saves time/cost)
  - Example: `--prioritize-top 20` analyzes 20 most relevant files
- `--top-n N`: Generate payloads/annotations for top N findings
  - Example: `--top-n 10` creates payloads for 10 most critical issues
- `--question "..."`: Guides AI prioritization (be specific!)
  - Good: `"find SQL injection in user input handling"`
  - Bad: `"find bugs"`

## 📚 Additional Resources

### Help & Examples

```bash
# Standard help
python3 scrynet.py <mode> --help

# Comprehensive examples (analyze mode)
python3 scrynet.py analyze --help-examples
```

### Direct Script Access

You can also run scripts directly (advanced usage):

```bash
# AI analyzer (called by scrynet.py analyze)
python3 smart_analyzer.py /path/to/repo "question"

# CTF analyzer (called by scrynet.py ctf)
python3 ctf_analyzer.py /path/to/ctf "question"

# Hybrid orchestrator (called by scrynet.py hybrid)
python3 orchestrator.py /path/to/repo ./scanner --profile owasp
```

**Note:** For most users, `scrynet.py` is the recommended entry point.

## 🏗️ Architecture

SCRYNET uses a modular architecture:

- **Entry Point**: `scrynet.py` - Unified CLI dispatcher
- **Analyzers**: `smart_analyzer.py`, `ctf_analyzer.py` - AI-powered analysis
- **Orchestrator**: `orchestrator.py` - Hybrid static + AI
- **Library**: `lib/` - Shared modules (common, models, output, context, prompts)
- **Scanner**: `scanner` - Fast Go-based static analyzer

## 🔒 Security & Privacy

### Never Commit These Files

SCRYNET outputs may contain sensitive information. The following are automatically gitignored:

- `output/` - All analysis results
- `test-reports/`, `security-reports/`, `*-reports/` - Custom report directories
- `**/payloads/`, `**/annotations/` - Generated payloads and annotations
- `**/*_findings.*` - All finding reports (JSON, CSV, MD, HTML)
- `.scrynet_cache/` - API cache and review state
- `.env`, `*.key`, `*secret*` - Configuration and secrets

### API Key Security

- **Never commit** your `CLAUDE_API_KEY` to the repository
- Use environment variables: `export CLAUDE_API_KEY="sk-ant-api03-..."`
- The `.gitignore` file protects against accidental commits
- All outputs are gitignored by default

### Verifying Before Commit

```bash
# Check what would be committed
git status

# Verify no secrets in staged files
git diff --cached | grep -i "api.*key\|secret\|password" || echo "✓ No secrets found"

# Check for large output files
git status --porcelain | grep -E "(output|report|findings)" || echo "✓ No output files staged"
```

## 📝 License

[Add your license information here]

---

## 🚀 Quick Start

**Fast static scan (no API key needed):**
```bash
python3 scrynet.py static . --severity HIGH
```

**Comprehensive AI analysis (requires API key):**
```bash
export CLAUDE_API_KEY="your_key_here"
python3 scrynet.py hybrid . ./scanner \
  --profile owasp \
  --prioritize \
  --prioritize-top 20 \
  --question "find security vulnerabilities" \
  --generate-payloads \
  --annotate-code \
  --top-n 10 \
  --verbose
```

**Get help:**
```bash
python3 scrynet.py --help
python3 scrynet.py hybrid --help
```
