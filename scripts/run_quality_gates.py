#!/usr/bin/env python3
"""
Quality Gates Runner

Runs strict quality gates for new worktrees to ensure high code quality
and adherence to development standards.
"""

import subprocess
import sys
import json
import os
from pathlib import Path
from typing import Dict, List, Any

class QualityGatesRunner:
    """Runs quality gates for new development work"""

    def __init__(self, worktree_path: str = "."):
        self.worktree_path = Path(worktree_path)
        self.quality_config = self._load_quality_config()

    def _load_quality_config(self) -> Dict[str, Any]:
        """Load quality gates configuration"""
        config_file = self.worktree_path / ".quality-gates.json"

        if not config_file.exists():
            # Default configuration for worktrees without config
            return {
                "quality_gates": {
                    "max_pr_size": 500,
                    "min_coverage": 85,
                    "required_tests": True,
                    "required_docs": True,
                    "required_security_review": True,
                    "max_complexity": 15
                }
            }

        try:
            with open(config_file, 'r') as f:
                loaded_data = json.load(f)
            return loaded_data if isinstance(loaded_data, dict) else {"quality_gates": {"max_pr_size": 500, "min_coverage": 85}}
        except (json.JSONDecodeError, IOError):
            print("⚠️ Invalid quality gates configuration, using defaults")
            return {"quality_gates": {"max_pr_size": 500, "min_coverage": 85}}

    def run_all_gates(self) -> Dict[str, Any]:
        """Run all quality gates"""
        results: Dict[str, Any] = {
            "success": True,
            "checks": {},
            "warnings": [],
            "errors": [],
            "summary": {}
        }

        print("🔍 Running Quality Gates...")
        print("=" * 50)

        # 1. Check PR size
        pr_size_result = self._check_pr_size()
        results["checks"]["pr_size"] = pr_size_result
        if not pr_size_result["passed"]:
            results["success"] = False
            results["errors"].extend(pr_size_result["errors"])

        # 2. Check code linting
        linting_result = self._check_linting()
        results["checks"]["linting"] = linting_result
        if not linting_result["passed"]:
            results["success"] = False
            results["errors"].extend(linting_result["errors"])

        # 3. Check tests
        test_result = self._check_tests()
        results["checks"]["tests"] = test_result
        if not test_result["passed"]:
            results["success"] = False
            results["errors"].extend(test_result["errors"])

        # 4. Check documentation
        docs_result = self._check_documentation()
        results["checks"]["documentation"] = docs_result
        if not docs_result["passed"]:
            results["success"] = False
            results["errors"].extend(docs_result["errors"])

        # 5. Check security
        security_result = self._check_security()
        results["checks"]["security"] = security_result
        if not security_result["passed"]:
            results["success"] = False
            results["errors"].extend(security_result["errors"])

        # 6. Check complexity
        complexity_result = self._check_complexity()
        results["checks"]["complexity"] = complexity_result
        if not complexity_result["passed"]:
            results["success"] = False
            results["errors"].extend(complexity_result["errors"])

        # Generate summary
        passed_checks = sum(1 for check in results["checks"].values() if check["passed"])
        total_checks = len(results["checks"])
        results["summary"] = {
            "passed_checks": passed_checks,
            "total_checks": total_checks,
            "success_rate": f"{(passed_checks/total_checks)*100:.1f}%"
        }

        return results

    def _check_pr_size(self) -> Dict[str, Any]:
        """Check PR size against limits"""
        try:
            result = subprocess.run([
                "git", "diff", "--stat", "main"
            ], cwd=self.worktree_path, capture_output=True, text=True)

            if result.returncode != 0:
                return {
                    "passed": False,
                    "errors": ["Could not check PR size - git command failed"],
                    "details": "Git diff command failed"
                }

            if not result.stdout.strip():
                return {
                    "passed": True,
                    "errors": [],
                    "details": "No changes detected"
                }

            lines = result.stdout.strip().split('\n')
            if lines:
                last_line = lines[-1]
                if "insertion" in last_line or "deletion" in last_line:
                    # Extract total changes
                    changes = 0
                    parts = last_line.split()
                    for i, part in enumerate(parts):
                        if part.isdigit():
                            changes += int(part)

                    max_size = self.quality_config["quality_gates"]["max_pr_size"]

                    if changes > max_size:
                        return {
                            "passed": False,
                            "errors": [f"PR size {changes} lines exceeds limit of {max_size} lines"],
                            "details": f"Current: {changes}, Limit: {max_size}"
                        }
                    else:
                        return {
                            "passed": True,
                            "errors": [],
                            "details": f"PR size: {changes}/{max_size} lines"
                        }

            return {
                "passed": True,
                "errors": [],
                "details": "No significant changes detected"
            }

        except Exception as e:
            return {
                "passed": False,
                "errors": [f"Error checking PR size: {e}"],
                "details": str(e)
            }

    def _check_linting(self) -> Dict[str, Any]:
        """Check code linting"""
        try:
            # Check if there are Python files to lint
            python_files = list(self.worktree_path.glob("**/*.py"))

            if not python_files:
                return {
                    "passed": True,
                    "errors": [],
                    "details": "No Python files to lint"
                }

            # Try to run flake8 or similar linter
            try:
                result = subprocess.run([
                    "python", "-m", "flake8", "--max-line-length=120", "."
                ], cwd=self.worktree_path, capture_output=True, text=True)

                if result.returncode == 0:
                    return {
                        "passed": True,
                        "errors": [],
                        "details": f"Linting passed for {len(python_files)} Python files"
                    }
                else:
                    return {
                        "passed": False,
                        "errors": [f"Linting failed: {result.stdout}"],
                        "details": result.stdout
                    }

            except FileNotFoundError:
                return {
                    "passed": False,
                    "errors": ["Linter not found - please install flake8"],
                    "details": "flake8 not available"
                }

        except Exception as e:
            return {
                "passed": False,
                "errors": [f"Error checking linting: {e}"],
                "details": str(e)
            }

    def _check_tests(self) -> Dict[str, Any]:
        """Check test coverage"""
        try:
            # Look for test files
            test_files = list(self.worktree_path.glob("**/test_*.py")) + \
                        list(self.worktree_path.glob("**/*_test.py")) + \
                        list(self.worktree_path.glob("**/tests/**/*.py"))

            if not test_files:
                return {
                    "passed": False,
                    "errors": ["No test files found"],
                    "details": "Required test files missing"
                }

            # Try to run pytest with coverage
            try:
                result = subprocess.run([
                    "python", "-m", "pytest", "--cov=.", "--cov-report=term-missing", "-v"
                ], cwd=self.worktree_path, capture_output=True, text=True)

                if result.returncode == 0:
                    # Try to extract coverage percentage
                    output_lines = result.stdout.split('\n')
                    for line in output_lines:
                        if "TOTAL" in line and "%" in line:
                            # Extract coverage percentage
                            parts = line.split()
                            for part in parts:
                                if part.endswith("%"):
                                    coverage = int(part[:-1])
                                    min_coverage = self.quality_config["quality_gates"]["min_coverage"]

                                    if coverage >= min_coverage:
                                        return {
                                            "passed": True,
                                            "errors": [],
                                            "details": f"Test coverage: {coverage}% (≥{min_coverage}%)"
                                        }
                                    else:
                                        return {
                                            "passed": False,
                                            "errors": [f"Test coverage {coverage}% below minimum {min_coverage}%"],
                                            "details": f"Coverage: {coverage}%, Required: {min_coverage}%"
                                        }

                    return {
                        "passed": True,
                        "errors": [],
                        "details": f"Tests passed for {len(test_files)} test files"
                    }
                else:
                    return {
                        "passed": False,
                        "errors": [f"Tests failed: {result.stdout}"],
                        "details": result.stdout
                    }

            except FileNotFoundError:
                return {
                    "passed": False,
                    "errors": ["pytest not found - please install pytest and pytest-cov"],
                    "details": "pytest not available"
                }

        except Exception as e:
            return {
                "passed": False,
                "errors": [f"Error checking tests: {e}"],
                "details": str(e)
            }

    def _check_documentation(self) -> Dict[str, Any]:
        """Check documentation requirements"""
        try:
            # Check for README files
            readme_files = list(self.worktree_path.glob("README*.md")) + \
                          list(self.worktree_path.glob("readme*.md"))

            # Check for docstrings in Python files
            python_files = list(self.worktree_path.glob("**/*.py"))
            documented_files = 0

            for py_file in python_files:
                if py_file.name.startswith("__"):
                    continue

                try:
                    with open(py_file, 'r') as f:
                        content = f.read()
                        if '"""' in content or "'''" in content:
                            documented_files += 1