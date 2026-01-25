# SCRYNET Documentation

Additional documentation for SCRYNET features.

## 📚 Documentation Files

### Essential Guides

- **[PROFILES.md](PROFILES.md)** - Complete profile reference
  - All available AI profiles (owasp, ctf, code_review, etc.)
  - Use cases and examples
  - How to combine profiles

- **[ADVANCED_EXAMPLES.md](ADVANCED_EXAMPLES.md)** - Advanced usage examples
  - Multi-profile scans
  - Deduplication strategies
  - Complex workflows

### Feature Documentation

- **[REVIEW_STATE.md](REVIEW_STATE.md)** - Review state management
  - How to save and resume scans
  - Change detection
  - Progress tracking

- **[SCRYNET_CONTEXT_README.md](SCRYNET_CONTEXT_README.md)** - Context & caching system
  - API response caching
  - Context file generation
  - Cache management

- **[DEDUPLICATION_FLOW.md](DEDUPLICATION_FLOW.md)** - Deduplication system
  - How deduplication works
  - Similarity detection
  - Merge strategies

## 🚀 Quick Links

- **Main README**: [../README.md](../README.md)
- **Changelog**: [../CHANGELOG.md](../CHANGELOG.md)
- **Test Suite**: [../tests/README.md](../tests/README.md)

## 💡 Getting Started

For most users, the main README has everything you need:
```bash
cd gowasp
python3 scrynet.py --help
```

For advanced features, see the guides listed above.
