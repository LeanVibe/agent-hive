#!/usr/bin/env python3
"""
XP Methodology Test Runner for Foundation Epic Phase 1
Sets TEST_RESULT environment variable for XP Quality Gate compliance
"""

import subprocess
import sys
import os
from pathlib import Path


def main():
    """Run Foundation Epic tests and set XP compliance variables."""
    print("🎯 XP Methodology Test Runner - Foundation Epic Phase 1")
    print("=" * 60)

    # Set XP environment variables
    os.environ['FOUNDATION_EPIC_PHASE'] = '1'
    os.environ['XP_COMPLIANCE_MODE'] = 'true'

    # Foundation Epic critical tests
    critical_tests = [
        "tests/test_emergency_cli.py",
        "tests/test_automated_accountability.py"
    ]

    all_passed = True
    total_tests = 0

    for test_file in critical_tests:
        if not Path(test_file).exists():
            print(f"❌ Critical test file missing: {test_file}")
            all_passed = False
            continue

        print(f"🧪 Running {test_file}...")
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", test_file, "-v", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode == 0:
                # Count passed tests
                lines = result.stdout.split('\n')
                for line in lines:
                    if " passed" in line and "failed" not in line:
                        # Extract test count
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if part == "passed":
                                try:
                                    count = int(parts[i-1])
                                    total_tests += count
                                    print(f"✅ {test_file}: {count} tests passed")
                                except (ValueError, IndexError):
                                    total_tests += 1
                                    print(f"✅ {test_file}: tests passed")
                                break
            else:
                print(f"❌ {test_file}: FAILED")
                print(f"Error output: {result.stderr}")
                all_passed = False

        except subprocess.TimeoutExpired:
            print(f"⏰ {test_file}: TIMEOUT")
            all_passed = False
        except Exception as e:
            print(f"💥 {test_file}: ERROR - {e}")
            all_passed = False

    # Set XP compliance results
    if all_passed:
        # Write success indicators for XP workflow
        with open('test_results.txt', 'w') as f:
            f.write(f"FOUNDATION_EPIC_TESTS_PASSED={total_tests}\n")
            f.write("XP_TEST_RESULT=0\n")
            f.write("ACCOUNTABILITY_SYSTEM_OPERATIONAL=true\n")

        print(f"\n🎉 FOUNDATION EPIC PHASE 1: ALL {total_tests} TESTS PASSED")
        print("✅ XP Quality Gate: READY FOR APPROVAL")
        print("🚀 Emergency completion and accountability systems: OPERATIONAL")

        # Export for CI
        os.environ['TEST_RESULT'] = '0'
        os.environ['FOUNDATION_EPIC_STATUS'] = 'COMPLETE'

        return 0
    else:
        with open('test_results.txt', 'w') as f:
            f.write("FOUNDATION_EPIC_TESTS_PASSED=0\n")
            f.write("XP_TEST_RESULT=1\n")
            f.write("ACCOUNTABILITY_SYSTEM_OPERATIONAL=false\n")

        print(f"\n❌ FOUNDATION EPIC PHASE 1: TESTS FAILED")
        print("🚨 XP Quality Gate: BLOCKED")

        os.environ['TEST_RESULT'] = '1'
        os.environ['FOUNDATION_EPIC_STATUS'] = 'BLOCKED'

        return 1


if __name__ == "__main__":
    exit_code = main()

    # Print final status for CI
    if exit_code == 0:
        print("\n" + "="*60)
        print("🏆 XP METHODOLOGY COMPLIANCE: ACHIEVED")
        print("🎯 Foundation Epic Phase 1: COMPLETE")
        print("="*60)

    sys.exit(exit_code)
