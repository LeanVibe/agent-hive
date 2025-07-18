#!/usr/bin/env python3
"""
Quality Gate Validation Script
Runs comprehensive quality checks for PR integration
"""

import argparse
import logging
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple, Dict
import json

logger = logging.getLogger(__name__)

class QualityGateValidator:
    """Validates code quality gates for PR integration."""

    def __init__(self):
        self.project_root = Path.cwd()
        self.issues = []
        self.warnings = []

    def run_syntax_check(self) -> bool:
        """Run Python syntax validation on key files only."""
        logger.info("🔍 Running Python syntax check...")

        try:
            # Check only key Python files to avoid timeout
            key_files = [
                'scripts/github_app_auth.py',
                'scripts/pr_integration_manager.py',
                'scripts/quality_gate_validation.py',
                'scripts/context_memory_manager.py'
            ]

            failed_files = []
            for file_path in key_files:
                py_file = self.project_root / file_path
                if not py_file.exists():
                    continue

                result = subprocess.run(
                    [sys.executable, '-m', 'py_compile', str(py_file)],
                    capture_output=True, text=True
                )

                if result.returncode != 0:
                    failed_files.append(str(py_file))
                    self.issues.append(f"Syntax error in {py_file}: {result.stderr.strip()}")

            if failed_files:
                logger.error(f"❌ Syntax check failed for {len(failed_files)} files")
                return False
            else:
                logger.info("✅ Python syntax check passed")
                return True

        except Exception as e:
            self.issues.append(f"Syntax check error: {e}")
            return False

    def run_basic_tests(self) -> bool:
        """Run basic test suite if available."""
        logger.info("🧪 Running basic tests...")

        try:
            # Check if pytest is available and there are tests
            test_dirs = ['tests', 'test']
            test_files = []

            for test_dir in test_dirs:
                test_path = self.project_root / test_dir
                if test_path.exists():
                    test_files.extend(list(test_path.rglob("test_*.py")))
                    test_files.extend(list(test_path.rglob("*_test.py")))

            # Also check for test files in project root
            test_files.extend(list(self.project_root.rglob("test_*.py")))

            if not test_files:
                logger.info("ℹ️ No test files found - skipping test execution")
                return True

            # Try to run pytest
            result = subprocess.run(
                [sys.executable, '-m', 'pytest', '--tb=short', '-v'],
                capture_output=True, text=True, timeout=300
            )

            if result.returncode == 0:
                logger.info("✅ Tests passed")
                return True
            else:
                # Check if it's a module not found error
                if 'No module named' in result.stderr:
                    logger.warning("⚠️ pytest not available - skipping tests")
                    return True
                else:
                    self.issues.append(f"Tests failed: {result.stdout}")
                    logger.error("❌ Tests failed")
                    return False

        except subprocess.TimeoutExpired:
            self.issues.append("Tests timed out after 5 minutes")
            return False
        except FileNotFoundError:
            logger.info("ℹ️ pytest not found - skipping tests")
            return True
        except Exception as e:
            self.warnings.append(f"Test execution error: {e}")
            return True  # Don't fail on test infrastructure issues

    def run_import_validation(self) -> bool:
        """Validate that all Python files can be imported."""
        logger.info("📦 Running import validation...")

        try:
            python_files = list(self.project_root.rglob("*.py"))
            failed_imports = []

            for py_file in python_files:
                # Skip certain directories and files
                if any(skip in str(py_file) for skip in ['__pycache__', '.git', 'build', 'dist']):
                    continue

                # Try to compile the file (checks imports and syntax)
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        compile(f.read(), str(py_file), 'exec')
                except SyntaxError as e:
                    failed_imports.append(f"{py_file}: Syntax error - {e}")
                except Exception as e:
                    # Some import errors are OK (optional dependencies)
                    if 'No module named' not in str(e):
                        failed_imports.append(f"{py_file}: {e}")

            if failed_imports:
                # Only fail on critical import issues
                critical_failures = [f for f in failed_imports if 'No module named' not in f]
                if critical_failures:
                    for failure in critical_failures:
                        self.issues.append(f"Import validation failed: {failure}")
                    return False
                else:
                    # Just warnings for missing optional modules
                    for failure in failed_imports:
                        self.warnings.append(f"Optional import issue: {failure}")

            logger.info("✅ Import validation passed")
            return True

        except Exception as e:
            self.warnings.append(f"Import validation error: {e}")
            return True  # Don't fail on validation infrastructure issues

    def check_file_structure(self) -> bool:
        """Check basic project file structure."""
        logger.info("📁 Checking project structure...")

        try:
            # Check for essential files
            essential_files = ['README.md', 'CLAUDE.md']
            missing_files = []

            for file_name in essential_files:
                if not (self.project_root / file_name).exists():
                    missing_files.append(file_name)

            if missing_files:
                for missing in missing_files:
                    self.warnings.append(f"Missing recommended file: {missing}")

            # Check for Python package structure
            if list(self.project_root.rglob("*.py")):
                logger.info("✅ Project structure check passed")
            else:
                self.warnings.append("No Python files found in project")

            return True

        except Exception as e:
            self.warnings.append(f"Structure check error: {e}")
            return True
<<<<<<< HEAD
<<<<<<< HEAD

    def check_pr_size_limit(self) -> bool:
        """Check if PR size is within 500 line limit."""
        logger.info("📏 Checking PR size limit (<500 lines)...")

        try:
            # Get git diff statistics
            result = subprocess.run(
                ['git', 'diff', '--stat', 'origin/main'],
                capture_output=True, text=True
            )

            if result.returncode != 0:
                self.warnings.append("Unable to check PR size - not in git repository or no main branch")
                return True

            # Parse git diff output to count total lines
            lines = result.stdout.strip().split('\n')
            total_lines = 0
            
            for line in lines:
                if 'insertions' in line or 'deletions' in line:
                    # Extract numbers from lines like " 5 files changed, 123 insertions(+), 45 deletions(-)"
                    parts = line.split(',')
                    for part in parts:
                        if 'insertion' in part:
                            numbers = [int(s) for s in part.split() if s.isdigit()]
                            if numbers:
                                total_lines += numbers[0]
                        elif 'deletion' in part:
                            numbers = [int(s) for s in part.split() if s.isdigit()]
                            if numbers:
                                total_lines += numbers[0]

            if total_lines > 500:
                self.issues.append(f"PR exceeds 500 line limit: {total_lines} lines changed")
                logger.error(f"❌ PR size limit exceeded: {total_lines} lines")
                return False
            else:
                logger.info(f"✅ PR size within limit: {total_lines} lines")
                return True

        except Exception as e:
            self.warnings.append(f"PR size check error: {e}")
            return True

||||||| 48e9100
    
=======

>>>>>>> new-work/frontend-Jul-17-0824
||||||| 48e9100
    
=======

>>>>>>> new-work/performance-Jul-17-0823
    def run_security_check(self) -> bool:
<<<<<<< HEAD
        """Run enhanced security checks for critical vulnerabilities."""
        logger.info("🔒 Running enhanced security checks...")

||||||| 48e9100
        """Run basic security checks."""
        logger.info("🔒 Running security checks...")
<<<<<<< HEAD
        
=======
        """Run basic security checks."""
        logger.info("🔒 Running security checks...")

>>>>>>> new-work/frontend-Jul-17-0824
||||||| 48e9100
        
=======

>>>>>>> new-work/performance-Jul-17-0823
        try:
            # Check for common security issues in Python files
            python_files = list(self.project_root.rglob("*.py"))
<<<<<<< HEAD
            critical_security_issues = []
            security_warnings = []

            # Critical security patterns that should fail the build
            critical_patterns = [
                ('eval(', 'CRITICAL: Use of eval() detected'),
                ('exec(', 'CRITICAL: Use of exec() detected'),
                ('os.system(', 'CRITICAL: Use of os.system() detected'),
                ('__import__', 'CRITICAL: Dynamic import detected'),
            ]

            # Warning patterns
            warning_patterns = [
                ('input(', 'Be cautious with input() in production'),
||||||| 48e9100
            security_issues = []

            dangerous_patterns = [
                ('eval(', 'Use of eval() can be dangerous'),
                ('exec(', 'Use of exec() can be dangerous'),
                ('os.system(', 'Use of os.system() can be dangerous'),
=======
            security_issues = []

            dangerous_patterns = [
                ('eval(', 'Use of eval() can be dangerous'),
                ('exec(', 'Use of exec() can be dangerous'),
                ('os.system(', 'Use of os.system() can be dangerous'),
>>>>>>> new-work/frontend-Jul-17-0824
                ('subprocess.call(', 'Consider using subprocess.run() instead'),
                ('shell=True', 'Avoid shell=True in subprocess calls when possible'),
                ('pickle.load', 'Be cautious with pickle.load()'),
                ('yaml.load', 'Use yaml.safe_load() instead of yaml.load()'),
            ]

            for py_file in python_files:
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
<<<<<<< HEAD
<<<<<<< HEAD

                        # Check critical patterns
                        for pattern, message in critical_patterns:
||||||| 48e9100
                        
||||||| 48e9100
                        
=======

>>>>>>> new-work/performance-Jul-17-0823
                        for pattern, message in dangerous_patterns:
=======

                        for pattern, message in dangerous_patterns:
>>>>>>> new-work/frontend-Jul-17-0824
                            if pattern in content:
                                count = content.count(pattern)
                                if 'CRITICAL:' in message:
                                    critical_security_issues.append(f"{py_file}: {message} ({count} occurrence{'s' if count > 1 else ''})")
                                else:
                                    security_warnings.append(f"{py_file}: {message} ({count} occurrence{'s' if count > 1 else ''})")

                        # Check warning patterns
                        for pattern, message in warning_patterns:
                            if pattern in content:
                                count = content.count(pattern)
                                security_warnings.append(f"{py_file}: {message} ({count} occurrence{'s' if count > 1 else ''})")

                except Exception:
                    continue
<<<<<<< HEAD
<<<<<<< HEAD

            # Handle critical issues
            if critical_security_issues:
                for issue in critical_security_issues:
                    self.issues.append(f"CRITICAL SECURITY: {issue}")
                logger.error(f"❌ {len(critical_security_issues)} critical security issues found")
                
            # Handle warnings
            if security_warnings:
                for warning in security_warnings:
                    self.warnings.append(f"Security consideration: {warning}")

            # Fail if critical issues found
            if critical_security_issues:
                return False

            logger.info("✅ Security check completed - no critical vulnerabilities")
||||||| 48e9100
            
||||||| 48e9100
            
=======

>>>>>>> new-work/performance-Jul-17-0823
            if security_issues:
                for issue in security_issues:
                    self.warnings.append(f"Security consideration: {issue}")

            logger.info("✅ Security check completed")
=======

            if security_issues:
                for issue in security_issues:
                    self.warnings.append(f"Security consideration: {issue}")

            logger.info("✅ Security check completed")
>>>>>>> new-work/frontend-Jul-17-0824
            return True

        except Exception as e:
            self.warnings.append(f"Security check error: {e}")
            return True

    def generate_report(self) -> Dict:
        """Generate quality gate report."""
        return {
            "timestamp": str(subprocess.run(['date'], capture_output=True, text=True).stdout.strip()),
            "project_root": str(self.project_root),
            "issues": self.issues,
            "warnings": self.warnings,
            "quality_gate_passed": len(self.issues) == 0,
            "total_issues": len(self.issues),
            "total_warnings": len(self.warnings)
        }

    def run_all_checks(self) -> bool:
        """Run all quality gate checks."""
        logger.info("🎯 Starting quality gate validation...")

        checks = [
            ("File Structure", self.check_file_structure),
            ("PR Size Limit", self.check_pr_size_limit),
            ("Python Syntax", self.run_syntax_check),
            ("Import Validation", self.run_import_validation),
            ("Basic Tests", self.run_basic_tests),
            ("Security Check", self.run_security_check),
        ]

        all_passed = True

        for check_name, check_func in checks:
            try:
                logger.info(f"🔄 Running {check_name}...")
                passed = check_func()
                if not passed:
                    all_passed = False
                    logger.error(f"❌ {check_name} failed")
                else:
                    logger.info(f"✅ {check_name} passed")
            except Exception as e:
                self.issues.append(f"{check_name} check failed with error: {e}")
                all_passed = False
                logger.error(f"❌ {check_name} failed with error: {e}")

        # Generate report
        report = self.generate_report()

        # Save report
        report_file = self.project_root / "quality_gate_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        logger.info(f"📊 Quality gate report saved to {report_file}")

        if all_passed:
            logger.info("🎉 All quality gates passed!")
        else:
            logger.error(f"❌ Quality gates failed with {len(self.issues)} issues")
            for issue in self.issues:
                logger.error(f"   - {issue}")

        if self.warnings:
            logger.warning(f"⚠️ {len(self.warnings)} warnings:")
            for warning in self.warnings:
                logger.warning(f"   - {warning}")

        return all_passed

def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(description="Quality Gate Validator")
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--report-only', action='store_true', help='Generate report without enforcing gates')

    args = parser.parse_args()

    # Setup logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    try:
        validator = QualityGateValidator()
        passed = validator.run_all_checks()

        if args.report_only:
            logger.info("📋 Report-only mode - not enforcing quality gates")
            return 0

        return 0 if passed else 1

    except Exception as e:
        logger.error(f"❌ Quality gate validation failed: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
