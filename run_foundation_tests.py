#!/usr/bin/env python3
"""
Foundation Epic Phase 1 test runner.
Ensures all critical tests pass for Foundation Epic completion.
"""

import subprocess
import sys
from pathlib import Path


def run_tests():
    """Run Foundation Epic Phase 1 critical tests."""
    print("🚀 Foundation Epic Phase 1 - Critical Test Suite")
    print("=" * 50)
    
    # Critical test files for Foundation Epic
    test_files = [
        "tests/test_emergency_cli.py",
        "tests/test_automated_accountability.py"
    ]
    
    all_passed = True
    
    for test_file in test_files:
        test_path = Path(test_file)
        if not test_path.exists():
            print(f"❌ Test file not found: {test_file}")
            all_passed = False
            continue
            
        print(f"\n🧪 Running {test_file}...")
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", test_file, "-v"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                print(f"✅ {test_file} - All tests passed")
                # Count passed tests
                lines = result.stdout.split('\n')
                for line in lines:
                    if " passed" in line and "failed" not in line:
                        print(f"   📊 {line.strip()}")
                        break
            else:
                print(f"❌ {test_file} - Tests failed")
                print(f"   Error: {result.stderr}")
                all_passed = False
                
        except subprocess.TimeoutExpired:
            print(f"⏰ {test_file} - Tests timed out")
            all_passed = False
        except Exception as e:
            print(f"💥 {test_file} - Error running tests: {e}")
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 Foundation Epic Phase 1 - ALL TESTS PASSED")
        print("✅ Ready for Foundation Epic completion")
        return 0
    else:
        print("❌ Foundation Epic Phase 1 - TESTS FAILED")
        print("🚨 Foundation Epic completion blocked")
        return 1


if __name__ == "__main__":
    sys.exit(run_tests())