# SCRYNET Test Suite

Python test suite for SCRYNET core functionality.

## Running Tests

### Quick Test
```bash
cd gowasp
source .venv/bin/activate
python3 tests/test_imports.py
```

### All Tests
```bash
python3 -m unittest discover tests -v
```

### Specific Test Files
```bash
python3 -m unittest tests.test_common -v
python3 -m unittest tests.test_orchestrator -v
python3 -m unittest tests.test_profiles -v
python3 -m unittest tests.test_integration -v
```

### Specific Test Classes
```bash
python3 -m unittest tests.test_common.TestNormalizeFinding -v
python3 -m unittest tests.test_integration.TestNormalizationIntegration -v
```

## Test Files

- `test_common.py` - Tests for `lib/common.py` utilities
- `test_orchestrator.py` - Tests for orchestrator functionality
- `test_profiles.py` - Tests for profile loading
- `test_integration.py` - Integration and workflow tests
- `test_imports.py` - Quick import verification
- `test_context_lib.py` - Context/caching tests

## Test Coverage

Current coverage: **43/48 tests passing (89.6%)**

### Covered
✅ Finding normalization (8 tests)
✅ Recommendation extraction (1 test)
✅ Line number extraction (5 tests)
✅ Safe file reading (3 tests)
✅ Error classes (2 tests)
✅ JSON parsing (5 tests)
✅ Integration workflows (5 tests)
✅ Orchestrator functionality (5 tests)
✅ Profile loading (9 tests)

### Test Targets

Real vulnerability test applications in `test_targets/`:
- DVWA - Damn Vulnerable Web Application
- juice-shop - OWASP Juice Shop
- WebGoat - OWASP WebGoat

## Shell Scripts

Located in `scripts/`:
- `test_dvwa.sh` - Test DVWA scan
- `test_juice_shop.sh` - Test juice-shop scan
- `test_advanced.sh` - Advanced feature tests
- `test_complex.sh` - Complex multi-profile tests
- `test_all_profiles.sh` - Test all profiles

Run with:
```bash
cd gowasp/tests/scripts
./test_dvwa.sh
```

## Notes

- Tests use virtual environment (`.venv`)
- Some tests require `CLAUDE_API_KEY` for API integration tests
- Static tests work without API key
