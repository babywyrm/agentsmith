#!/usr/bin/env python3
"""Quick test to verify all imports work."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from lib.common import (
        normalize_finding,
        get_recommendation_text,
        get_line_number,
        handle_api_error,
        safe_file_read,
        APIError,
        FileAnalysisError,
    )
    print("✅ All imports successful!")
    
    # Quick smoke test
    finding = {'severity': 'high', 'fix': 'Test fix'}
    normalized = normalize_finding(finding)
    print(f"✅ Normalization works: {normalized['severity']} -> {normalized['recommendation']}")
    
    rec = get_recommendation_text({'recommendation': 'Test'})
    print(f"✅ Recommendation extraction works: {rec}")
    
    line = get_line_number({'line': 42})
    print(f"✅ Line number extraction works: {line}")
    
    print("\n🎉 All basic functionality verified!")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

