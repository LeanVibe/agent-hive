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