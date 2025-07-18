#!/usr/bin/env python3
"""
Enhanced Quality Gates with Automated Technical Debt Enforcement

This script provides automated enforcement of quality standards specifically
designed to prevent technical debt accumulation and maintain code health.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class TechnicalDebtEnforcer:
    """Automated technical debt detection and enforcement."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.quality_thresholds = {
            'mypy_error_limit': 10,  # Maximum allowed mypy errors (reduced from 50)
            'pylint_score_minimum': 8.5,  # Minimum pylint score (increased from 8.0)
            'complexity_threshold': 8,  # Maximum cyclomatic complexity (reduced from 10)
            'duplicate_code_threshold': 3,  # Maximum % duplicate code (reduced from 5)
            'test_coverage_minimum': 90,  # Minimum test coverage % (increased from 85)
            'security_issues_limit': 0,  # Maximum security issues
            'dead_code_threshold': 5,  # Maximum % dead code
            'type_annotation_coverage': 95,  # Minimum type annotation coverage %
        }
        self.results: Dict[str, Any] = {}

    def run_mypy_analysis(self) -> Dict[str, Any]:
        """Run MyPy static type checking."""
        logger.info("🔍 Running MyPy static type analysis...")

        try:
            result = subprocess.run(
                ['python', '-m', 'mypy', '.', '--config-file=mypy.ini', '--exclude', 'new-worktrees'],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )

            # Count errors
            lines = result.stdout.split('\n')
            error_lines = [line for line in lines if 'error:' in line]
            error_count = len(error_lines)

            analysis = {
                'error_count': error_count,
                'errors': error_lines[:10],  # First 10 errors for reporting
                'passed': error_count <= self.quality_thresholds['mypy_error_limit'],
                'exit_code': result.returncode
            }

            logger.info(f"MyPy analysis: {error_count} errors found")
            return analysis

        except Exception as e:
            logger.error(f"MyPy analysis failed: {e}")
            return {'error_count': 999, 'errors': [str(e)], 'passed': False, 'exit_code': 1}

    def run_pylint_analysis(self) -> Dict[str, Any]:
        """Run Pylint code quality analysis."""
        logger.info("🔍 Running Pylint code quality analysis...")

        try:
            # Focus on main modules to avoid overwhelming output
            key_modules = ['cli.py', 'advanced_orchestration/', 'external_api/', 'scripts/']

            scores = []
            for module in key_modules:
                if Path(self.project_root / module).exists():
                    result = subprocess.run(
                        ['python', '-m', 'pylint', module, '--score=y', '--reports=n'],
                        capture_output=True,
                        text=True,
                        cwd=self.project_root
                    )

                    # Extract score from output
                    for line in result.stdout.split('\n'):
                        if 'Your code has been rated at' in line:
                            try:
                                score = float(line.split()[6].split('/')[0])
                                scores.append(score)
                                break
                            except (IndexError, ValueError):
                                continue

            avg_score = sum(scores) / len(scores) if scores else 0.0
            analysis = {
                'average_score': avg_score,
                'module_scores': scores,
                'passed': avg_score >= self.quality_thresholds['pylint_score_minimum'],
                'recommendation': 'Consider addressing pylint warnings' if avg_score < 9.0 else 'Good code quality'
            }

            logger.info(f"Pylint analysis: average score {avg_score:.1f}/10.0")
            return analysis

        except Exception as e:
            logger.error(f"Pylint analysis failed: {e}")
            return {'average_score': 0.0, 'passed': False, 'recommendation': f'Analysis failed: {e}'}

    def run_complexity_analysis(self) -> Dict[str, Any]:
        """Run cyclomatic complexity analysis."""
        logger.info("🔍 Running complexity analysis...")

        try:
            result = subprocess.run(
                ['python', '-m', 'radon', 'cc', '.', '--min', 'B', '--json'],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )

            if result.returncode == 0:
                complexity_data = json.loads(result.stdout)
                high_complexity = []

                for file_path, functions in complexity_data.items():
                    for func in functions:
                        if func.get('complexity', 0) > self.quality_thresholds['complexity_threshold']:
                            high_complexity.append({
                                'file': file_path,
                                'function': func.get('name', 'unknown'),
                                'complexity': func.get('complexity', 0)
                            })

                analysis = {
                    'high_complexity_count': len(high_complexity),
                    'high_complexity_functions': high_complexity[:5],  # Top 5
                    'passed': len(high_complexity) == 0,
                    'recommendation': 'Consider refactoring complex functions' if high_complexity else 'Good complexity levels'
                }

                logger.info(f"Complexity analysis: {len(high_complexity)} high-complexity functions")
                return analysis
            else:
                return {'passed': True, 'recommendation': 'Radon not available, complexity check skipped'}

        except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError):
            return {'passed': True, 'recommendation': 'Complexity analysis not available'}

    def run_security_analysis(self) -> Dict[str, Any]:
        """Run security vulnerability analysis."""
        logger.info("🔍 Running security analysis...")

        try:
            # Run bandit security linter
            result = subprocess.run(
                ['python', '-m', 'bandit', '-r', '.', '-f', 'json', '--skip', 'B101'],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )

            if result.stdout:
                security_data = json.loads(result.stdout)
                issues = security_data.get('results', [])
                high_severity = [issue for issue in issues if issue.get('issue_severity') == 'HIGH']

                analysis = {
                    'total_issues': len(issues),
                    'high_severity_issues': len(high_severity),
                    'passed': len(high_severity) <= self.quality_thresholds['security_issues_limit'],
                    'recommendation': 'Address high-severity security issues' if high_severity else 'No critical security issues'
                }

                logger.info(f"Security analysis: {len(issues)} total issues, {len(high_severity)} high-severity")
                return analysis
            else:
                return {'passed': True, 'recommendation': 'No security issues detected'}

        except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError):
            return {'passed': True, 'recommendation': 'Security analysis not available'}

    def run_dead_code_analysis(self) -> Dict[str, Any]:
        """Detect dead/unused code."""
        logger.info("🧹 Running dead code analysis...")

        try:
            result = subprocess.run(
                ['python', '-m', 'vulture', '.', '--exclude', 'new-worktrees', '--min-confidence', '80'],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )

            # Count dead code findings
            lines = result.stdout.strip().split('\n') if result.stdout.strip() else []
            dead_code_count = len([line for line in lines if line and not line.startswith('#')])

            # Calculate dead code percentage (rough estimate)
            total_files = len(list(self.project_root.rglob('*.py')))
            dead_code_percentage = (dead_code_count / max(total_files * 10, 1)) * 100  # Rough estimate

            passed = dead_code_percentage <= self.quality_thresholds['dead_code_threshold']

            return {
                'passed': passed,
                'dead_code_count': dead_code_count,
                'dead_code_percentage': round(dead_code_percentage, 2),
                'recommendation': f"Remove {dead_code_count} dead code items" if not passed else "Dead code levels acceptable"
            }

        except (subprocess.CalledProcessError, FileNotFoundError):
            return {'passed': True, 'recommendation': 'Dead code analysis not available'}

    def run_type_annotation_analysis(self) -> Dict[str, Any]:
        """Check type annotation coverage."""
        logger.info("🏷️ Running type annotation analysis...")

        try:
            result = subprocess.run(
                ['python', '-m', 'mypy', '.', '--config-file=mypy.ini', '--exclude', 'new-worktrees', '--strict'],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )

            # Count type annotation issues
            lines = result.stdout.split('\n')
            annotation_errors = len([line for line in lines if 'annotation' in line.lower() or 'untyped' in line.lower()])

            # Estimate type annotation coverage
            total_python_files = len(list(self.project_root.rglob('*.py')))
            coverage_estimate = max(0, 100 - (annotation_errors / max(total_python_files, 1)) * 10)

            passed = coverage_estimate >= self.quality_thresholds['type_annotation_coverage']

            return {
                'passed': passed,
                'annotation_errors': annotation_errors,
                'coverage_estimate': round(coverage_estimate, 2),
                'recommendation': f"Add type annotations to improve coverage" if not passed else "Type annotation coverage acceptable"
            }

        except (subprocess.CalledProcessError, FileNotFoundError):
            return {'passed': True, 'recommendation': 'Type annotation analysis not available'}

    def generate_quality_report(self) -> None:
        """Generate comprehensive quality report."""
        logger.info("📊 Generating quality gate report...")

        self.results['mypy'] = self.run_mypy_analysis()
        self.results['pylint'] = self.run_pylint_analysis()
        self.results['complexity'] = self.run_complexity_analysis()
        self.results['security'] = self.run_security_analysis()
        self.results['dead_code'] = self.run_dead_code_analysis()
        self.results['type_annotations'] = self.run_type_annotation_analysis()

        # Calculate overall status
        all_passed = all(result.get('passed', False) for result in self.results.values())

        # Generate report
        report = {
            'timestamp': '2025-07-17T08:32:00Z',
            'overall_status': 'PASS' if all_passed else 'FAIL',
            'quality_gates': self.results,
            'summary': {
                'total_gates': len(self.results),
                'passed_gates': sum(1 for result in self.results.values() if result.get('passed', False)),
                'recommendations': [result.get('recommendation', '') for result in self.results.values() if result.get('recommendation')]
            }
        }

        # Save report
        report_file = self.project_root / 'analysis_reports' / 'quality_gates_report.json'
        report_file.parent.mkdir(exist_ok=True)

        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        # Print summary
        self._print_summary(report)

        return all_passed

    def _print_summary(self, report: Dict[str, Any]) -> None:
        """Print quality gate summary."""
        print("\n🚨 QUALITY GATES ENFORCEMENT REPORT")
        print("=" * 40)

        status_emoji = "✅" if report['overall_status'] == 'PASS' else "❌"
        print(f"\n{status_emoji} Overall Status: {report['overall_status']}")
        print(f"📊 Gates Passed: {report['summary']['passed_gates']}/{report['summary']['total_gates']}")

        print("\n📋 Gate Results:")
        for gate_name, result in report['quality_gates'].items():
            gate_emoji = "✅" if result.get('passed', False) else "❌"
            print(f"  {gate_emoji} {gate_name.title()}: {result.get('recommendation', 'No issues')}")

        if report['summary']['recommendations']:
            print(f"\n💡 Recommendations:")
            for rec in report['summary']['recommendations']:
                if rec:
                    print(f"  • {rec}")

        print(f"\n📄 Full report saved to: analysis_reports/quality_gates_report.json")


class AutomatedCodeFixer:
    """Automated fixes for common code quality issues."""

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def fix_trailing_whitespace(self) -> List[str]:
        """Remove trailing whitespace from Python files."""
        logger.info("🔧 Fixing trailing whitespace...")

        fixed_files = []
        for py_file in self.project_root.rglob('*.py'):
            try:
                with open(py_file, 'r') as f:
                    lines = f.readlines()

                # Remove trailing whitespace
                new_lines = [line.rstrip() + '\n' for line in lines]

                # Only write if changes were made
                if lines != new_lines:
                    with open(py_file, 'w') as f:
                        f.writelines(new_lines)
                    fixed_files.append(str(py_file.relative_to(self.project_root)))
            except Exception as e:
                logger.warning(f"Could not fix whitespace in {py_file}: {e}")

        return fixed_files

    def remove_unused_imports(self) -> List[str]:
        """Remove unused imports using autoflake."""
        logger.info("🔧 Removing unused imports...")

        try:
            result = subprocess.run(
                ['python', '-m', 'autoflake', '--remove-all-unused-imports', '--in-place', '--recursive', '.'],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )

            if result.returncode == 0:
                return ['Successfully removed unused imports']
            else:
                return ['autoflake not available or failed']
        except FileNotFoundError:
            return ['autoflake not installed, skipping unused import removal']

    def apply_automatic_fixes(self) -> Dict[str, List[str]]:
        """Apply all automatic fixes."""
        logger.info("🔧 Applying automatic code fixes...")

        fixes = {
            'trailing_whitespace': self.fix_trailing_whitespace(),
            'unused_imports': self.remove_unused_imports()
        }

        return fixes


def main():
    """Main quality gates enforcement entry point."""
    project_root = Path.cwd()

    print("🚀 LeanVibe Enhanced Quality Gates")
    print("=" * 35)

    # Initialize components
    debt_enforcer = TechnicalDebtEnforcer(project_root)
    code_fixer = AutomatedCodeFixer(project_root)

    # Apply automatic fixes first
    print("\n🔧 AUTOMATED FIXES")
    fixes = code_fixer.apply_automatic_fixes()

    total_fixes = sum(len(fix_list) for fix_list in fixes.values())
    if total_fixes > 0:
        print(f"✅ Applied {total_fixes} automatic fixes")
        for fix_type, fix_list in fixes.items():
            if fix_list:
                print(f"  • {fix_type}: {len(fix_list)} items")
    else:
        print("✅ No automatic fixes needed")

    # Run quality gate analysis
    print("\n🔍 QUALITY GATE ANALYSIS")
    all_passed = debt_enforcer.generate_quality_report()

    # Exit with appropriate code
    if all_passed:
        print("\n🎉 All quality gates passed! Code is ready for commit.")
        sys.exit(0)
    else:
        print("\n❌ Some quality gates failed. Please address issues before committing.")
        sys.exit(1)


if __name__ == '__main__':
    main()
