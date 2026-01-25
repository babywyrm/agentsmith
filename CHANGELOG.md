# SCRYNET Changelog

All notable changes to this project will be documented in this file.

## [Unreleased] - 2026-01-24

### Added
- **Normalization Utilities** (`lib/common.py`)
  - `normalize_finding()` - Centralized finding normalization
  - `get_recommendation_text()` - Unified recommendation extraction
  - `get_line_number()` - Consistent line number handling
  - `handle_api_error()` - Smart API error handling with retry logic
  - `safe_file_read()` - Safe file operations with size checks
  - Custom exceptions: `APIError`, `FileAnalysisError`, `ScrynetError`

- **Test Suite Improvements**
  - 48 unit tests covering normalization and error handling
  - Integration tests for complete workflows
  - Test coverage: 89.6% (43/48 tests passing)

### Changed
- **Orchestrator Refactoring** (`orchestrator.py`)
  - Eliminated 13+ duplicated normalization patterns
  - All stages now use centralized utilities:
    - AI scanner findings processing
    - CSV/Markdown/HTML export
    - Payload generation stage
    - Code annotation stage
    - Deduplication key generation
  - Improved error handling with specific exception types
  - Better logging and error messages

### Fixed
- Inconsistent field handling (line vs line_number, fix vs recommendation)
- Generic exception handling replaced with specific error types
- File path normalization (Path objects converted to strings consistently)
- Severity capitalization standardized across all outputs

### Technical Debt Resolved
- Code duplication: 13+ patterns → 2 utility functions
- Maintainability: Single source of truth for field normalization
- Testability: All normalization logic now unit tested
- Error handling: Specific exceptions with proper context

---

## [Previous] - Historical

### Features
- Multi-mode security scanner (static, analyze, ctf, hybrid)
- AI-powered analysis with Claude integration
- Multiple AI profiles (owasp, ctf, code_review, etc.)
- AI prioritization to select most relevant files
- Payload generation for Red/Blue team testing
- Code annotation with inline fixes
- Intelligent deduplication of findings
- Cost tracking and estimation
- Review state management with caching
- Multiple export formats (JSON, CSV, Markdown, HTML)
- Rich console UI with progress bars
- Support for multiple languages (Go, Python, Java, JS, PHP, etc.)

