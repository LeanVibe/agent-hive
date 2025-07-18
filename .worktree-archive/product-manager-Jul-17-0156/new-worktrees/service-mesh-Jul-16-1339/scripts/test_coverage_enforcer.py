#!/usr/bin/env python3
"""
Test Coverage Enforcer - XP Methodology Compliance
Part of PM/XP Methodology Enforcer

This module enforces test coverage requirements and tracks coverage trends
for XP methodology compliance and continuous quality improvement.
"""

import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime
from typing import Dict, List, Tuple
from dataclasses import dataclass
import xml.etree.ElementTree as ET


@dataclass
class CoverageReport:
    """Detailed coverage report for a specific run."""
    report_id: str
    timestamp: str
    total_coverage: float
    line_coverage: float
    branch_coverage: float
    function_coverage: float
    lines_covered: int
    lines_total: int
    branches_covered: int
    branches_total: int
    functions_covered: int
    functions_total: int
    files_analyzed: int
    missing_files: List[str]
    low_coverage_files: List[Dict[str, float]]
    coverage_trend: str
    quality_gate_passed: bool


@dataclass
class CoverageTarget:
    """Coverage targets and thresholds."""
    minimum_total: float = 80.0
    minimum_line: float = 80.0
    minimum_branch: float = 70.0
    minimum_function: float = 85.0
    warning_threshold: float = 85.0
    excellent_threshold: float = 95.0
    file_minimum: float = 70.0
    new_code_minimum: float = 90.0


class TestCoverageEnforcer:
    """Advanced test coverage enforcement and monitoring system."""

    def __init__(self, db_path: str = "coverage_data.db"):
        self.db_path = db_path
        self.targets = CoverageTarget()
        self.init_database()

    def init_database(self):
        """Initialize SQLite database for coverage tracking."""
        with sqlite3.connect(self.db_path) as conn:
            # Coverage reports table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS coverage_reports (
                    report_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    total_coverage REAL NOT NULL,
                    line_coverage REAL NOT NULL,
                    branch_coverage REAL NOT NULL,
                    function_coverage REAL NOT NULL,
                    lines_covered INTEGER NOT NULL,
                    lines_total INTEGER NOT NULL,
                    branches_covered INTEGER NOT NULL,
                    branches_total INTEGER NOT NULL,
                    functions_covered INTEGER NOT NULL,
                    functions_total INTEGER NOT NULL,
                    files_analyzed INTEGER NOT NULL,
                    coverage_trend TEXT NOT NULL,
                    quality_gate_passed BOOLEAN NOT NULL
                )
            """)

            # File coverage table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS file_coverage (
                    record_id TEXT PRIMARY KEY,
                    report_id TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    line_coverage REAL NOT NULL,
                    branch_coverage REAL NOT NULL,
                    function_coverage REAL NOT NULL,
                    lines_covered INTEGER NOT NULL,
                    lines_total INTEGER NOT NULL,
                    missing_lines TEXT,
                    complexity_score REAL,
                    FOREIGN KEY (report_id) REFERENCES coverage_reports (report_id)
                )
            """)

            # Coverage trends table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS coverage_trends (
                    trend_id TEXT PRIMARY KEY,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    coverage_change REAL NOT NULL,
                    trend_direction TEXT NOT NULL,
                    trend_strength REAL NOT NULL,
                    files_improved INTEGER NOT NULL,
                    files_degraded INTEGER NOT NULL,
                    recorded_at TEXT NOT NULL
                )
            """)

            # Coverage violations table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS coverage_violations (
                    violation_id TEXT PRIMARY KEY,
                    report_id TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    violation_type TEXT NOT NULL,
                    current_coverage REAL NOT NULL,
                    required_coverage REAL NOT NULL,
                    severity TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    resolved BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (report_id) REFERENCES coverage_reports (report_id)
                )
            """)

            conn.commit()

    def run_coverage_analysis(self, test_path: str = "tests/",
                             source_path: str = ".",
                             output_formats: List[str] = None) -> Dict:
        """Run comprehensive coverage analysis."""
        if output_formats is None:
            output_formats = ["json", "xml", "html", "term"]

        try:
            # Build coverage command
            cmd = ["python", "-m", "pytest", f"--cov={source_path}", "--cov-branch"]

            # Add output formats
            for fmt in output_formats:
                if fmt == "json":
                    cmd.append("--cov-report=json")
                elif fmt == "xml":
                    cmd.append("--cov-report=xml")
                elif fmt == "html":
                    cmd.append("--cov-report=html")
                elif fmt == "term":
                    cmd.append("--cov-report=term-missing")

            # Add test path
            cmd.append(test_path)

            # Run coverage
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=".")

            # Parse coverage results
            coverage_data = self.parse_coverage_results(output_formats)

            return {
                'success': result.returncode == 0,
                'output': result.stdout,
                'error': result.stderr,
                'coverage_data': coverage_data,
                'return_code': result.returncode
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'coverage_data': None,
                'return_code': -1
            }

    def parse_coverage_results(self, formats: List[str]) -> Dict:
        """Parse coverage results from different output formats."""
        coverage_data = {
            'total_coverage': 0.0,
            'line_coverage': 0.0,
            'branch_coverage': 0.0,
            'function_coverage': 0.0,
            'lines_covered': 0,
            'lines_total': 0,
            'branches_covered': 0,
            'branches_total': 0,
            'functions_covered': 0,
            'functions_total': 0,
            'files': {},
            'missing_files': []
        }

        # Parse JSON report
        if "json" in formats and os.path.exists("coverage.json"):
            coverage_data.update(self.parse_json_coverage("coverage.json"))

        # Parse XML report
        if "xml" in formats and os.path.exists("coverage.xml"):
            xml_data = self.parse_xml_coverage("coverage.xml")
            coverage_data.update(xml_data)

        return coverage_data

    def parse_json_coverage(self, json_file: str) -> Dict:
        """Parse JSON coverage report."""
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)

            totals = data.get('totals', {})
            files = data.get('files', {})

            # Parse file-level coverage
            file_coverage = {}
            for file_path, file_data in files.items():
                summary = file_data.get('summary', {})
                file_coverage[file_path] = {
                    'line_coverage': summary.get('percent_covered', 0),
                    'lines_covered': summary.get('covered_lines', 0),
                    'lines_total': summary.get('num_statements', 0),
                    'missing_lines': file_data.get('missing_lines', []),
                    'excluded_lines': file_data.get('excluded_lines', [])
                }

            return {
                'total_coverage': totals.get('percent_covered', 0),
                'line_coverage': totals.get('percent_covered', 0),
                'lines_covered': totals.get('covered_lines', 0),
                'lines_total': totals.get('num_statements', 0),
                'files': file_coverage
            }

        except Exception as e:
            print(f"Error parsing JSON coverage: {e}")
            return {}

    def parse_xml_coverage(self, xml_file: str) -> Dict:
        """Parse XML coverage report."""
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()

            # Parse overall coverage
            coverage_attrs = root.attrib
            line_rate = float(coverage_attrs.get('line-rate', 0)) * 100
            branch_rate = float(coverage_attrs.get('branch-rate', 0)) * 100

            # Count totals
            lines_covered = int(coverage_attrs.get('lines-covered', 0))
            lines_valid = int(coverage_attrs.get('lines-valid', 0))
            branches_covered = int(coverage_attrs.get('branches-covered', 0))
            branches_valid = int(coverage_attrs.get('branches-valid', 0))

            return {
                'line_coverage': line_rate,
                'branch_coverage': branch_rate,
                'lines_covered': lines_covered,
                'lines_total': lines_valid,
                'branches_covered': branches_covered,
                'branches_total': branches_valid
            }

        except Exception as e:
            print(f"Error parsing XML coverage: {e}")
            return {}

    def analyze_coverage_trends(self, days: int = 30) -> Dict:
        """Analyze coverage trends over time."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Get coverage history
            cursor.execute("""
                SELECT timestamp, total_coverage, line_coverage, branch_coverage
                FROM coverage_reports
                WHERE timestamp >= datetime('now', '-{} days')
                ORDER BY timestamp
            """.format(days))

            history = cursor.fetchall()

        if len(history) < 2:
            return {
                'trend': 'insufficient_data',
                'change': 0.0,
                'direction': 'stable',
                'strength': 0.0,
                'data_points': len(history)
            }

        # Calculate trend
        coverages = [row[1] for row in history]

        # Simple linear trend
        n = len(coverages)
        x_mean = (n - 1) / 2
        y_mean = sum(coverages) / n

        numerator = sum((i - x_mean) * (coverages[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            slope = 0
        else:
            slope = numerator / denominator

        # Determine trend direction and strength
        if slope > 0.1:
            direction = 'increasing'
        elif slope < -0.1:
            direction = 'decreasing'
        else:
            direction = 'stable'

        strength = abs(slope) / 10.0  # Normalize to 0-1 range
        change = coverages[-1] - coverages[0]

        return {
            'trend': direction,
            'change': change,
            'direction': direction,
            'strength': min(strength, 1.0),
            'data_points': len(history),
            'current_coverage': coverages[-1],
            'starting_coverage': coverages[0]
        }

    def check_coverage_quality_gates(self, coverage_data: Dict) -> Tuple[bool, List[str]]:
        """Check if coverage meets quality gate requirements."""
        violations = []

        # Check total coverage
        if coverage_data['total_coverage'] < self.targets.minimum_total:
            violations.append(f"Total coverage {coverage_data['total_coverage']:.1f}% < {self.targets.minimum_total}%")

        # Check line coverage
        if coverage_data['line_coverage'] < self.targets.minimum_line:
            violations.append(f"Line coverage {coverage_data['line_coverage']:.1f}% < {self.targets.minimum_line}%")

        # Check branch coverage
        if coverage_data['branch_coverage'] < self.targets.minimum_branch:
            violations.append(f"Branch coverage {coverage_data['branch_coverage']:.1f}% < {self.targets.minimum_branch}%")

        # Check file-level coverage
        low_coverage_files = []
        for file_path, file_data in coverage_data.get('files', {}).items():
            if file_data['line_coverage'] < self.targets.file_minimum:
                low_coverage_files.append(f"{file_path}: {file_data['line_coverage']:.1f}%")

        if low_coverage_files:
            violations.append(f"Low coverage files: {', '.join(low_coverage_files[:5])}")

        return len(violations) == 0, violations

    def generate_coverage_report(self, detailed: bool = True) -> str:
        """Generate comprehensive coverage report."""
        # Run coverage analysis
        analysis_result = self.run_coverage_analysis()

        if not analysis_result['success']:
            return f"Coverage analysis failed: {analysis_result['error']}"

        coverage_data = analysis_result['coverage_data']

        # Check quality gates
        gates_passed, violations = self.check_coverage_quality_gates(coverage_data)

        # Analyze trends
        trends = self.analyze_coverage_trends()

        # Generate report
        report = f"""
# Test Coverage Report

## 📊 Coverage Overview
- **Total Coverage**: {coverage_data['total_coverage']:.1f}%
- **Line Coverage**: {coverage_data['line_coverage']:.1f}%
- **Branch Coverage**: {coverage_data['branch_coverage']:.1f}%
- **Lines Covered**: {coverage_data['lines_covered']:,} / {coverage_data['lines_total']:,}
- **Branches Covered**: {coverage_data['branches_covered']:,} / {coverage_data['branches_total']:,}

## 🎯 Quality Gates
- **Status**: {'✅ PASSED' if gates_passed else '❌ FAILED'}
- **Target Coverage**: {self.targets.minimum_total}%
- **Current vs Target**: {coverage_data['total_coverage'] - self.targets.minimum_total:+.1f}%

## 📈 Coverage Trends ({trends['data_points']} data points)
- **Trend Direction**: {trends['direction'].title()}
- **Coverage Change**: {trends['change']:+.1f}%
- **Trend Strength**: {trends['strength']:.2f}
"""

        if trends['data_points'] >= 2:
            report += f"- **Starting Coverage**: {trends['starting_coverage']:.1f}%\n"
            report += f"- **Current Coverage**: {trends['current_coverage']:.1f}%\n"

        # Add violations if any
        if violations:
            report += """
## ⚠️ Quality Gate Violations
"""
            for i, violation in enumerate(violations, 1):
                report += f"{i}. {violation}\n"

        # Add file-level details if requested
        if detailed and coverage_data.get('files'):
            report += """
## 📁 File-Level Coverage
"""

            # Sort files by coverage (lowest first)
            sorted_files = sorted(
                coverage_data['files'].items(),
                key=lambda x: x[1]['line_coverage']
            )

            for file_path, file_data in sorted_files[:10]:  # Top 10 lowest coverage
                status = "❌" if file_data['line_coverage'] < self.targets.file_minimum else "✅"
                report += f"{status} **{file_path}**: {file_data['line_coverage']:.1f}% ({file_data['lines_covered']}/{file_data['lines_total']} lines)\n"

        # Add recommendations
        report += self.generate_coverage_recommendations(coverage_data, violations, trends)

        # Save report
        report_record = CoverageReport(
            report_id=f"coverage-{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            timestamp=datetime.now().isoformat(),
            total_coverage=coverage_data['total_coverage'],
            line_coverage=coverage_data['line_coverage'],
            branch_coverage=coverage_data['branch_coverage'],
            function_coverage=coverage_data.get('function_coverage', 0),
            lines_covered=coverage_data['lines_covered'],
            lines_total=coverage_data['lines_total'],
            branches_covered=coverage_data['branches_covered'],
            branches_total=coverage_data['branches_total'],
            functions_covered=coverage_data.get('functions_covered', 0),
            functions_total=coverage_data.get('functions_total', 0),
            files_analyzed=len(coverage_data.get('files', {})),
            missing_files=coverage_data.get('missing_files', []),
            low_coverage_files=[],
            coverage_trend=trends['direction'],
            quality_gate_passed=gates_passed
        )

        self.save_coverage_report(report_record)

        return report

    def generate_coverage_recommendations(self, coverage_data: Dict,
                                        violations: List[str],
                                        trends: Dict) -> str:
        """Generate coverage improvement recommendations."""
        recommendations = []

        # Coverage-based recommendations
        if coverage_data['total_coverage'] < self.targets.minimum_total:
            gap = self.targets.minimum_total - coverage_data['total_coverage']
            recommendations.append(f"Increase total coverage by {gap:.1f}% to meet minimum requirements")

        if coverage_data['branch_coverage'] < self.targets.minimum_branch:
            recommendations.append("Add tests for conditional branches and edge cases")

        # Trend-based recommendations
        if trends['direction'] == 'decreasing':
            recommendations.append("Coverage is declining - prioritize adding tests for new code")

        if trends['direction'] == 'stable' and coverage_data['total_coverage'] < self.targets.warning_threshold:
            recommendations.append("Coverage is stable but below warning threshold - plan improvement")

        # File-based recommendations
        low_coverage_files = []
        for file_path, file_data in coverage_data.get('files', {}).items():
            if file_data['line_coverage'] < self.targets.file_minimum:
                low_coverage_files.append(file_path)

        if low_coverage_files:
            recommendations.append(f"Focus on {len(low_coverage_files)} files with low coverage")

        # General recommendations
        if not recommendations:
            recommendations.append("Coverage is meeting targets - continue current testing practices")

        report_section = """
## 💡 Recommendations
"""

        for i, rec in enumerate(recommendations, 1):
            report_section += f"{i}. {rec}\n"

        report_section += f"""
## 🔧 Coverage Improvement Actions
1. **Immediate**: Fix quality gate violations
2. **Short-term**: Add tests for uncovered lines and branches
3. **Medium-term**: Achieve {self.targets.warning_threshold}% coverage
4. **Long-term**: Maintain {self.targets.excellent_threshold}% coverage

## 📋 Quality Standards
- **Minimum Coverage**: {self.targets.minimum_total}%
- **Warning Threshold**: {self.targets.warning_threshold}%
- **Excellent Coverage**: {self.targets.excellent_threshold}%
- **File Minimum**: {self.targets.file_minimum}%
- **New Code Minimum**: {self.targets.new_code_minimum}%

---
Generated by PM/XP Methodology Enforcer Agent
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        return report_section

    def save_coverage_report(self, report: CoverageReport):
        """Save coverage report to database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO coverage_reports
                (report_id, timestamp, total_coverage, line_coverage, branch_coverage,
                 function_coverage, lines_covered, lines_total, branches_covered,
                 branches_total, functions_covered, functions_total, files_analyzed,
                 coverage_trend, quality_gate_passed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                report.report_id, report.timestamp, report.total_coverage,
                report.line_coverage, report.branch_coverage, report.function_coverage,
                report.lines_covered, report.lines_total, report.branches_covered,
                report.branches_total, report.functions_covered, report.functions_total,
                report.files_analyzed, report.coverage_trend, report.quality_gate_passed
            ))
            conn.commit()

    def check_pre_commit_coverage(self) -> bool:
        """Check coverage before commit."""
        analysis_result = self.run_coverage_analysis()

        if not analysis_result['success']:
            print(f"❌ Coverage analysis failed: {analysis_result['error']}")
            return False

        coverage_data = analysis_result['coverage_data']
        gates_passed, violations = self.check_coverage_quality_gates(coverage_data)

        if gates_passed:
            print(f"✅ Coverage quality gates passed: {coverage_data['total_coverage']:.1f}%")
            return True
        else:
            print("❌ Coverage quality gates failed:")
            for violation in violations:
                print(f"  - {violation}")
            return False


def main():
    """Main CLI interface for coverage enforcement."""
    if len(sys.argv) < 2:
        print("Usage: python test_coverage_enforcer.py <command> [options]")
        print("Commands:")
        print("  check                    - Check current coverage")
        print("  report [detailed]        - Generate coverage report")
        print("  run [source] [tests]     - Run coverage analysis")
        print("  trends [days]            - Show coverage trends")
        print("  gates                    - Check quality gates")
        print("  pre-commit               - Pre-commit coverage check")
        print("  targets                  - Show coverage targets")
        sys.exit(1)

    enforcer = TestCoverageEnforcer()
    command = sys.argv[1]

    if command == "check":
        if enforcer.check_pre_commit_coverage():
            print("✅ Coverage check: PASSED")
        else:
            print("❌ Coverage check: FAILED")
            sys.exit(1)

    elif command == "report":
        detailed = len(sys.argv) > 2 and sys.argv[2] == "detailed"
        report = enforcer.generate_coverage_report(detailed)

        # Save report
        filename = f"coverage_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(filename, 'w') as f:
            f.write(report)

        print(report)
        print(f"\nReport saved to: {filename}")

    elif command == "run":
        source = sys.argv[2] if len(sys.argv) > 2 else "."
        tests = sys.argv[3] if len(sys.argv) > 3 else "tests/"

        result = enforcer.run_coverage_analysis(tests, source)

        if result['success']:
            data = result['coverage_data']
            print("✅ Coverage analysis completed")
            print(f"Total Coverage: {data['total_coverage']:.1f}%")
            print(f"Line Coverage: {data['line_coverage']:.1f}%")
            print(f"Branch Coverage: {data['branch_coverage']:.1f}%")
        else:
            print(f"❌ Coverage analysis failed: {result['error']}")
            sys.exit(1)

    elif command == "trends":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        trends = enforcer.analyze_coverage_trends(days)

        print(f"Coverage Trends ({days} days):")
        print(f"Direction: {trends['direction']}")
        print(f"Change: {trends['change']:+.1f}%")
        print(f"Strength: {trends['strength']:.2f}")
        print(f"Data Points: {trends['data_points']}")

    elif command == "gates":
        result = enforcer.run_coverage_analysis()
        if result['success']:
            gates_passed, violations = enforcer.check_coverage_quality_gates(result['coverage_data'])

            if gates_passed:
                print("✅ All quality gates passed")
            else:
                print("❌ Quality gates failed:")
                for violation in violations:
                    print(f"  - {violation}")
        else:
            print(f"❌ Cannot check gates: {result['error']}")

    elif command == "pre-commit":
        if enforcer.check_pre_commit_coverage():
            sys.exit(0)
        else:
            sys.exit(1)

    elif command == "targets":
        targets = enforcer.targets
        print("Coverage Targets:")
        print(f"  Minimum Total: {targets.minimum_total}%")
        print(f"  Minimum Line: {targets.minimum_line}%")
        print(f"  Minimum Branch: {targets.minimum_branch}%")
        print(f"  Minimum Function: {targets.minimum_function}%")
        print(f"  Warning Threshold: {targets.warning_threshold}%")
        print(f"  Excellent Threshold: {targets.excellent_threshold}%")
        print(f"  File Minimum: {targets.file_minimum}%")
        print(f"  New Code Minimum: {targets.new_code_minimum}%")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
