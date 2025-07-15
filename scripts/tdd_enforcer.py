#!/usr/bin/env python3
"""
TDD Enforcer - XP Methodology Compliance
Part of PM/XP Methodology Enforcer

This module enforces Test-Driven Development (TDD) practices by monitoring
red-green-refactor cycles, test coverage, and test-first development compliance.
"""

import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from pathlib import Path
import re
import ast


@dataclass
class TDDCycle:
    """Represents a single TDD red-green-refactor cycle."""
    cycle_id: str
    commit_hash: str
    test_file: str
    test_function: str
    phase: str  # 'red', 'green', 'refactor'
    timestamp: str
    duration_seconds: float
    coverage_change: float
    lines_changed: int
    complexity_change: float
    status: str  # 'completed', 'incomplete', 'failed'


@dataclass
class TDDMetrics:
    """Comprehensive TDD compliance metrics."""
    period_id: str
    start_date: str
    end_date: str
    total_cycles: int
    completed_cycles: int
    failed_cycles: int
    avg_cycle_duration: float
    test_coverage: float
    coverage_trend: str  # 'increasing', 'decreasing', 'stable'
    test_first_compliance: float  # percentage of code with tests first
    red_green_refactor_ratio: Tuple[float, float, float]
    quality_score: float  # 0-100 overall TDD quality
    violations: List[str]
    recommendations: List[str]


class TDDEnforcer:
    """Advanced TDD enforcement and monitoring system."""
    
    def __init__(self, db_path: str = "tdd_data.db"):
        self.db_path = db_path
        self.init_database()
        self.coverage_threshold = 80.0  # Minimum coverage percentage
        self.test_patterns = [
            r'test_.*\.py$',
            r'.*_test\.py$',
            r'tests?/.*\.py$',
            r'.*_tests?\.py$'
        ]
    
    def init_database(self):
        """Initialize SQLite database for TDD tracking."""
        with sqlite3.connect(self.db_path) as conn:
            # TDD cycles table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tdd_cycles (
                    cycle_id TEXT PRIMARY KEY,
                    commit_hash TEXT NOT NULL,
                    test_file TEXT NOT NULL,
                    test_function TEXT NOT NULL,
                    phase TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    duration_seconds REAL NOT NULL,
                    coverage_change REAL NOT NULL,
                    lines_changed INTEGER NOT NULL,
                    complexity_change REAL NOT NULL,
                    status TEXT NOT NULL
                )
            """)
            
            # TDD metrics table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tdd_metrics (
                    period_id TEXT PRIMARY KEY,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    total_cycles INTEGER NOT NULL,
                    completed_cycles INTEGER NOT NULL,
                    failed_cycles INTEGER NOT NULL,
                    avg_cycle_duration REAL NOT NULL,
                    test_coverage REAL NOT NULL,
                    coverage_trend TEXT NOT NULL,
                    test_first_compliance REAL NOT NULL,
                    red_ratio REAL NOT NULL,
                    green_ratio REAL NOT NULL,
                    refactor_ratio REAL NOT NULL,
                    quality_score REAL NOT NULL,
                    recorded_at TEXT NOT NULL
                )
            """)
            
            # TDD violations table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tdd_violations (
                    violation_id TEXT PRIMARY KEY,
                    commit_hash TEXT NOT NULL,
                    violation_type TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    line_number INTEGER,
                    description TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    resolved BOOLEAN DEFAULT FALSE
                )
            """)
            
            # Coverage tracking table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS coverage_history (
                    record_id TEXT PRIMARY KEY,
                    commit_hash TEXT NOT NULL,
                    total_coverage REAL NOT NULL,
                    lines_covered INTEGER NOT NULL,
                    lines_total INTEGER NOT NULL,
                    branch_coverage REAL NOT NULL,
                    missing_files TEXT,
                    timestamp TEXT NOT NULL
                )
            """)
            
            conn.commit()
    
    def is_test_file(self, file_path: str) -> bool:
        """Check if a file is a test file based on naming patterns."""
        for pattern in self.test_patterns:
            if re.search(pattern, file_path):
                return True
        return False
    
    def extract_test_functions(self, file_path: str) -> List[str]:
        """Extract test function names from a test file."""
        test_functions = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse AST to find test functions
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                    test_functions.append(node.name)
        except Exception as e:
            print(f"Error extracting test functions from {file_path}: {e}")
        
        return test_functions
    
    def run_coverage_analysis(self) -> Dict[str, float]:
        """Run coverage analysis and return metrics."""
        try:
            # Run coverage
            result = subprocess.run([
                "python", "-m", "pytest", "--cov=.", "--cov-report=json",
                "--cov-report=term-missing", "-q"
            ], capture_output=True, text=True, cwd=".")
            
            # Parse coverage report
            coverage_file = "coverage.json"
            if os.path.exists(coverage_file):
                with open(coverage_file, 'r') as f:
                    coverage_data = json.loads(f.read())
                
                total_coverage = coverage_data.get('totals', {}).get('percent_covered', 0)
                lines_covered = coverage_data.get('totals', {}).get('covered_lines', 0)
                lines_total = coverage_data.get('totals', {}).get('num_statements', 0)
                
                return {
                    'total_coverage': total_coverage,
                    'lines_covered': lines_covered,
                    'lines_total': lines_total,
                    'branch_coverage': coverage_data.get('totals', {}).get('percent_covered_display', 0)
                }
        except Exception as e:
            print(f"Error running coverage analysis: {e}")
        
        return {
            'total_coverage': 0.0,
            'lines_covered': 0,
            'lines_total': 0,
            'branch_coverage': 0.0
        }
    
    def analyze_git_commits(self, since_date: str = None) -> List[Dict]:
        """Analyze git commits for TDD patterns."""
        try:
            # Get git log with file changes
            cmd = ["git", "log", "--name-status", "--pretty=format:%H|%s|%an|%ad", "--date=iso"]
            if since_date:
                cmd.extend(["--since", since_date])
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            commits = []
            current_commit = None
            
            for line in result.stdout.split('\n'):
                if '|' in line and not line.startswith(('A', 'M', 'D')):
                    # Commit header
                    parts = line.split('|')
                    if len(parts) >= 4:
                        current_commit = {
                            'hash': parts[0],
                            'message': parts[1],
                            'author': parts[2],
                            'date': parts[3],
                            'files': []
                        }
                        commits.append(current_commit)
                elif line.startswith(('A', 'M', 'D')) and current_commit:
                    # File change
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        change_type = parts[0]
                        file_path = parts[1]
                        current_commit['files'].append({
                            'type': change_type,
                            'path': file_path,
                            'is_test': self.is_test_file(file_path)
                        })
            
            return commits
        except subprocess.CalledProcessError as e:
            print(f"Error analyzing git commits: {e}")
            return []
    
    def detect_tdd_violations(self, commits: List[Dict]) -> List[Dict]:
        """Detect TDD violations in commit history."""
        violations = []
        
        for commit in commits:
            test_changes = [f for f in commit['files'] if f['is_test']]
            code_changes = [f for f in commit['files'] if not f['is_test'] and f['path'].endswith('.py')]
            
            # Violation 1: Code changes without corresponding test changes
            if code_changes and not test_changes:
                violations.append({
                    'type': 'missing_tests',
                    'commit': commit['hash'],
                    'description': f"Code changes in {len(code_changes)} files without test changes",
                    'severity': 'high',
                    'files': [f['path'] for f in code_changes]
                })
            
            # Violation 2: Large commits (anti-pattern for TDD)
            total_changes = len(commit['files'])
            if total_changes > 10:
                violations.append({
                    'type': 'large_commit',
                    'commit': commit['hash'],
                    'description': f"Large commit with {total_changes} file changes",
                    'severity': 'medium',
                    'files': [f['path'] for f in commit['files']]
                })
            
            # Violation 3: Test deletion without refactoring
            deleted_tests = [f for f in test_changes if f['type'] == 'D']
            if deleted_tests and not any(f['type'] == 'M' for f in test_changes):
                violations.append({
                    'type': 'test_deletion',
                    'commit': commit['hash'],
                    'description': f"Test files deleted without refactoring",
                    'severity': 'high',
                    'files': [f['path'] for f in deleted_tests]
                })
        
        return violations
    
    def calculate_tdd_metrics(self, period_days: int = 7) -> TDDMetrics:
        """Calculate comprehensive TDD metrics for a period."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=period_days)
        
        # Analyze commits in the period
        commits = self.analyze_git_commits(start_date.strftime('%Y-%m-%d'))
        
        # Detect violations
        violations = self.detect_tdd_violations(commits)
        
        # Calculate coverage
        coverage_data = self.run_coverage_analysis()
        
        # Analyze TDD cycles from database
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT phase, COUNT(*), AVG(duration_seconds)
                FROM tdd_cycles 
                WHERE timestamp >= ? AND timestamp <= ?
                GROUP BY phase
            """, (start_date.isoformat(), end_date.isoformat()))
            
            phase_data = cursor.fetchall()
            
            cursor.execute("""
                SELECT COUNT(*) as total, 
                       SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                       SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                       AVG(duration_seconds) as avg_duration
                FROM tdd_cycles 
                WHERE timestamp >= ? AND timestamp <= ?
            """, (start_date.isoformat(), end_date.isoformat()))
            
            cycle_stats = cursor.fetchone()
        
        # Calculate metrics
        total_cycles = cycle_stats[0] if cycle_stats[0] else 0
        completed_cycles = cycle_stats[1] if cycle_stats[1] else 0
        failed_cycles = cycle_stats[2] if cycle_stats[2] else 0
        avg_cycle_duration = cycle_stats[3] if cycle_stats[3] else 0.0
        
        # Calculate phase ratios
        phase_totals = {phase: count for phase, count, _ in phase_data}
        total_phases = sum(phase_totals.values())
        
        if total_phases > 0:
            red_ratio = phase_totals.get('red', 0) / total_phases
            green_ratio = phase_totals.get('green', 0) / total_phases
            refactor_ratio = phase_totals.get('refactor', 0) / total_phases
        else:
            red_ratio = green_ratio = refactor_ratio = 0.0
        
        # Calculate test-first compliance
        test_first_commits = 0
        for commit in commits:
            test_changes = [f for f in commit['files'] if f['is_test']]
            code_changes = [f for f in commit['files'] if not f['is_test'] and f['path'].endswith('.py')]
            
            if test_changes and code_changes:
                test_first_commits += 1
        
        test_first_compliance = (test_first_commits / len(commits)) * 100 if commits else 0
        
        # Calculate coverage trend
        coverage_trend = "stable"  # Simplified for now
        
        # Calculate quality score
        quality_score = self.calculate_quality_score(
            coverage_data['total_coverage'],
            test_first_compliance,
            len(violations),
            completed_cycles,
            failed_cycles
        )
        
        # Generate recommendations
        recommendations = self.generate_recommendations(
            coverage_data['total_coverage'],
            test_first_compliance,
            violations,
            red_ratio,
            green_ratio,
            refactor_ratio
        )
        
        return TDDMetrics(
            period_id=f"tdd-{start_date.strftime('%Y%m%d')}-{end_date.strftime('%Y%m%d')}",
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            total_cycles=total_cycles,
            completed_cycles=completed_cycles,
            failed_cycles=failed_cycles,
            avg_cycle_duration=avg_cycle_duration,
            test_coverage=coverage_data['total_coverage'],
            coverage_trend=coverage_trend,
            test_first_compliance=test_first_compliance,
            red_green_refactor_ratio=(red_ratio, green_ratio, refactor_ratio),
            quality_score=quality_score,
            violations=[v['description'] for v in violations],
            recommendations=recommendations
        )
    
    def calculate_quality_score(self, coverage: float, test_first: float, 
                               violation_count: int, completed: int, failed: int) -> float:
        """Calculate overall TDD quality score (0-100)."""
        # Coverage component (40% weight)
        coverage_score = min(coverage, 100) * 0.4
        
        # Test-first compliance (30% weight)
        test_first_score = min(test_first, 100) * 0.3
        
        # Violation penalty (20% weight)
        violation_penalty = max(0, 20 - violation_count * 2)
        
        # Success rate (10% weight)
        total_attempts = completed + failed
        success_rate = (completed / total_attempts) * 10 if total_attempts > 0 else 5
        
        return coverage_score + test_first_score + violation_penalty + success_rate
    
    def generate_recommendations(self, coverage: float, test_first: float,
                               violations: List[Dict], red_ratio: float,
                               green_ratio: float, refactor_ratio: float) -> List[str]:
        """Generate TDD improvement recommendations."""
        recommendations = []
        
        if coverage < self.coverage_threshold:
            recommendations.append(f"Increase test coverage from {coverage:.1f}% to {self.coverage_threshold}%")
        
        if test_first < 70:
            recommendations.append(f"Improve test-first compliance from {test_first:.1f}% to 70%+")
        
        if len(violations) > 5:
            recommendations.append(f"Address {len(violations)} TDD violations")
        
        # Check TDD cycle balance
        if red_ratio < 0.2:
            recommendations.append("Increase red phase focus - write failing tests first")
        
        if green_ratio < 0.3:
            recommendations.append("Improve green phase - focus on making tests pass")
        
        if refactor_ratio < 0.2:
            recommendations.append("Increase refactoring frequency - improve code quality")
        
        # General recommendations
        if not recommendations:
            recommendations.append("Continue current TDD practices - quality is good")
        
        return recommendations
    
    def save_tdd_metrics(self, metrics: TDDMetrics):
        """Save TDD metrics to database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO tdd_metrics
                (period_id, start_date, end_date, total_cycles, completed_cycles,
                 failed_cycles, avg_cycle_duration, test_coverage, coverage_trend,
                 test_first_compliance, red_ratio, green_ratio, refactor_ratio,
                 quality_score, recorded_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metrics.period_id, metrics.start_date, metrics.end_date,
                metrics.total_cycles, metrics.completed_cycles, metrics.failed_cycles,
                metrics.avg_cycle_duration, metrics.test_coverage, metrics.coverage_trend,
                metrics.test_first_compliance, metrics.red_green_refactor_ratio[0],
                metrics.red_green_refactor_ratio[1], metrics.red_green_refactor_ratio[2],
                metrics.quality_score, datetime.now().isoformat()
            ))
            conn.commit()
    
    def generate_tdd_report(self, period_days: int = 7) -> str:
        """Generate comprehensive TDD compliance report."""
        metrics = self.calculate_tdd_metrics(period_days)
        self.save_tdd_metrics(metrics)
        
        # Generate report
        report = f"""
# TDD Compliance Report

## Period: {metrics.start_date} to {metrics.end_date}

## 📊 Overall TDD Quality Score: {metrics.quality_score:.1f}/100

### 🔴🟢🔵 TDD Cycle Analysis
- **Total Cycles**: {metrics.total_cycles}
- **Completed**: {metrics.completed_cycles}
- **Failed**: {metrics.failed_cycles}
- **Average Duration**: {metrics.avg_cycle_duration:.1f} seconds

### 📈 Phase Distribution
- **Red Phase**: {metrics.red_green_refactor_ratio[0]:.1%} (Write failing tests)
- **Green Phase**: {metrics.red_green_refactor_ratio[1]:.1%} (Make tests pass)
- **Refactor Phase**: {metrics.red_green_refactor_ratio[2]:.1%} (Improve code quality)

### 🧪 Test Coverage Metrics
- **Current Coverage**: {metrics.test_coverage:.1f}%
- **Coverage Trend**: {metrics.coverage_trend.title()}
- **Test-First Compliance**: {metrics.test_first_compliance:.1f}%
- **Target Coverage**: {self.coverage_threshold}%

### ⚠️ TDD Violations ({len(metrics.violations)} found)
"""
        
        for i, violation in enumerate(metrics.violations, 1):
            report += f"{i}. {violation}\n"
        
        if not metrics.violations:
            report += "✅ No TDD violations detected\n"
        
        report += f"""
### 💡 Recommendations
"""
        
        for i, rec in enumerate(metrics.recommendations, 1):
            report += f"{i}. {rec}\n"
        
        # Add compliance status
        compliance_status = "✅ COMPLIANT" if metrics.quality_score >= 80 else "⚠️ NEEDS IMPROVEMENT"
        if metrics.quality_score < 60:
            compliance_status = "❌ NON-COMPLIANT"
        
        report += f"""
## 🎯 XP Methodology Compliance

### TDD Practice Assessment
- **Overall Status**: {compliance_status}
- **Red-Green-Refactor**: {'✅ Balanced' if all(r > 0.15 for r in metrics.red_green_refactor_ratio) else '❌ Imbalanced'}
- **Test Coverage**: {'✅ Adequate' if metrics.test_coverage >= self.coverage_threshold else '❌ Insufficient'}
- **Test-First Development**: {'✅ Good' if metrics.test_first_compliance >= 70 else '❌ Poor'}

### Quality Gates
- **Minimum Coverage**: {self.coverage_threshold}% (Current: {metrics.test_coverage:.1f}%)
- **Test-First Compliance**: 70% (Current: {metrics.test_first_compliance:.1f}%)
- **Quality Score**: 80+ (Current: {metrics.quality_score:.1f})
- **Violation Limit**: 5 (Current: {len(metrics.violations)})

### Next Steps
1. **Immediate**: Address high-severity violations
2. **Short-term**: Improve test coverage to {self.coverage_threshold}%
3. **Long-term**: Achieve balanced TDD cycles
4. **Continuous**: Monitor and maintain quality score 80+

---
Generated by PM/XP Methodology Enforcer Agent
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        return report
    
    def check_pre_commit_tdd(self) -> bool:
        """Check TDD compliance before commit."""
        try:
            # Run tests
            test_result = subprocess.run(["python", "-m", "pytest", "-v"], 
                                       capture_output=True, text=True)
            
            # Check coverage
            coverage_data = self.run_coverage_analysis()
            
            # Check for test files in staged changes
            staged_result = subprocess.run(["git", "diff", "--cached", "--name-only"], 
                                         capture_output=True, text=True)
            
            staged_files = staged_result.stdout.strip().split('\n')
            test_files = [f for f in staged_files if self.is_test_file(f)]
            code_files = [f for f in staged_files if f.endswith('.py') and not self.is_test_file(f)]
            
            # TDD compliance checks
            issues = []
            
            if test_result.returncode != 0:
                issues.append("❌ Tests are failing")
            
            if coverage_data['total_coverage'] < self.coverage_threshold:
                issues.append(f"❌ Coverage {coverage_data['total_coverage']:.1f}% < {self.coverage_threshold}%")
            
            if code_files and not test_files:
                issues.append("❌ Code changes without corresponding test changes")
            
            if issues:
                print("TDD Compliance Issues:")
                for issue in issues:
                    print(f"  {issue}")
                return False
            
            print("✅ TDD compliance checks passed")
            return True
            
        except Exception as e:
            print(f"Error checking TDD compliance: {e}")
            return False


def main():
    """Main CLI interface for TDD enforcement."""
    if len(sys.argv) < 2:
        print("Usage: python tdd_enforcer.py <command> [options]")
        print("Commands:")
        print("  check                    - Check current TDD compliance")
        print("  report [days]            - Generate TDD compliance report")
        print("  pre-commit               - Pre-commit TDD validation")
        print("  coverage                 - Run coverage analysis")
        print("  violations [days]        - Show TDD violations")
        print("  metrics [days]           - Show TDD metrics")
        sys.exit(1)
    
    enforcer = TDDEnforcer()
    command = sys.argv[1]
    
    if command == "check":
        if enforcer.check_pre_commit_tdd():
            print("✅ TDD compliance: PASSED")
        else:
            print("❌ TDD compliance: FAILED")
            sys.exit(1)
    
    elif command == "report":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
        report = enforcer.generate_tdd_report(days)
        
        # Save report
        filename = f"tdd_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(filename, 'w') as f:
            f.write(report)
        
        print(report)
        print(f"\nReport saved to: {filename}")
    
    elif command == "pre-commit":
        if enforcer.check_pre_commit_tdd():
            sys.exit(0)
        else:
            sys.exit(1)
    
    elif command == "coverage":
        coverage_data = enforcer.run_coverage_analysis()
        print(f"Coverage: {coverage_data['total_coverage']:.1f}%")
        print(f"Lines: {coverage_data['lines_covered']}/{coverage_data['lines_total']}")
        print(f"Branch Coverage: {coverage_data['branch_coverage']:.1f}%")
    
    elif command == "violations":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
        metrics = enforcer.calculate_tdd_metrics(days)
        
        print(f"TDD Violations ({len(metrics.violations)} found):")
        for i, violation in enumerate(metrics.violations, 1):
            print(f"{i}. {violation}")
        
        if not metrics.violations:
            print("✅ No TDD violations found")
    
    elif command == "metrics":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
        metrics = enforcer.calculate_tdd_metrics(days)
        
        print(f"TDD Metrics ({days} days):")
        print(f"Quality Score: {metrics.quality_score:.1f}/100")
        print(f"Test Coverage: {metrics.test_coverage:.1f}%")
        print(f"Test-First Compliance: {metrics.test_first_compliance:.1f}%")
        print(f"Cycles: {metrics.completed_cycles}/{metrics.total_cycles}")
        print(f"Phase Ratios: R{metrics.red_green_refactor_ratio[0]:.1%} G{metrics.red_green_refactor_ratio[1]:.1%} F{metrics.red_green_refactor_ratio[2]:.1%}")
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()