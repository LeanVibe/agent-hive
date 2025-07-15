#!/usr/bin/env python3
"""
TDD Enforcement Micro-Component - XP Methodology Enforcement
Part of PM/XP Methodology Enforcer (Micro-Component #4)

This micro-component handles ONLY Test-Driven Development (TDD) enforcement.
Follows XP Small Releases principle: ≤400 lines, single responsibility.
"""

import json
import sqlite3
import subprocess
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TDDViolation:
    """TDD violation record for micro-component."""
    violation_id: str
    file_path: str
    violation_type: str  # 'no_test', 'test_after_code', 'insufficient_coverage'
    severity: str  # 'critical', 'warning', 'info'
    line_count: int
    test_coverage: float
    timestamp: str


@dataclass
class TDDMetric:
    """TDD compliance metric for micro-component."""
    metric_id: str
    total_files: int
    files_with_tests: int
    coverage_percentage: float
    tdd_compliance_score: float
    violations_count: int
    timestamp: str


class TDDEnforcementMicro:
    """Micro-component for TDD enforcement functionality only."""
    
    def __init__(self, db_path: str = "tdd_enforcement_micro.db", 
                 project_root: str = "."):
        self.db_path = db_path
        self.project_root = Path(project_root)
        self.init_database()
    
    def init_database(self):
        """Initialize minimal database for TDD enforcement."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tdd_violations (
                    violation_id TEXT PRIMARY KEY,
                    file_path TEXT NOT NULL,
                    violation_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    line_count INTEGER NOT NULL,
                    test_coverage REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    resolved BOOLEAN DEFAULT FALSE
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tdd_metrics (
                    metric_id TEXT PRIMARY KEY,
                    total_files INTEGER NOT NULL,
                    files_with_tests INTEGER NOT NULL,
                    coverage_percentage REAL NOT NULL,
                    tdd_compliance_score REAL NOT NULL,
                    violations_count INTEGER NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)
            conn.commit()
    
    def scan_tdd_compliance(self, include_patterns: List[str] = None) -> TDDMetric:
        """Scan project for TDD compliance - core functionality."""
        if include_patterns is None:
            include_patterns = ["*.py", "*.js", "*.ts", "*.java", "*.rb", "*.go"]
        
        source_files = self._find_source_files(include_patterns)
        test_files = self._find_test_files()
        
        total_files = len(source_files)
        files_with_tests = 0
        total_violations = 0
        
        # Analyze each source file for TDD compliance
        for source_file in source_files:
            if self._has_corresponding_test(source_file, test_files):
                files_with_tests += 1
            else:
                violation = self._create_no_test_violation(source_file)
                self.save_violation(violation)
                total_violations += 1
        
        # Calculate metrics
        coverage_percentage = (files_with_tests / total_files * 100) if total_files > 0 else 0
        tdd_compliance_score = self._calculate_tdd_score(files_with_tests, total_files, total_violations)
        
        metric = TDDMetric(
            metric_id=f"tdd-scan-{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            total_files=total_files,
            files_with_tests=files_with_tests,
            coverage_percentage=coverage_percentage,
            tdd_compliance_score=tdd_compliance_score,
            violations_count=total_violations,
            timestamp=datetime.now().isoformat()
        )
        
        self.save_metric(metric)
        return metric
    
    def check_file_tdd_compliance(self, file_path: str) -> Dict:
        """Check TDD compliance for single file - core functionality."""
        file_path_obj = Path(file_path)
        
        if not file_path_obj.exists():
            return {"error": "File not found", "compliant": False}
        
        # Check if test file exists
        test_files = self._find_test_files()
        has_test = self._has_corresponding_test(file_path, test_files)
        
        # Get basic file info
        line_count = self._count_lines(file_path)
        
        compliance_data = {
            "file_path": str(file_path),
            "has_test": has_test,
            "line_count": line_count,
            "compliant": has_test,
            "violations": []
        }
        
        if not has_test:
            violation = self._create_no_test_violation(file_path)
            self.save_violation(violation)
            compliance_data["violations"].append({
                "type": violation.violation_type,
                "severity": violation.severity,
                "message": f"No test file found for {file_path}"
            })
        
        return compliance_data
    
    def get_tdd_violations(self, severity: str = None, limit: int = 50) -> List[TDDViolation]:
        """Get TDD violations - core functionality."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if severity:
                cursor.execute("""
                    SELECT violation_id, file_path, violation_type, severity,
                           line_count, test_coverage, timestamp
                    FROM tdd_violations
                    WHERE resolved = FALSE AND severity = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (severity, limit))
            else:
                cursor.execute("""
                    SELECT violation_id, file_path, violation_type, severity,
                           line_count, test_coverage, timestamp
                    FROM tdd_violations
                    WHERE resolved = FALSE
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (limit,))
            
            return [TDDViolation(*row) for row in cursor.fetchall()]
    
    def get_latest_tdd_metric(self) -> Optional[TDDMetric]:
        """Get latest TDD compliance metric."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT metric_id, total_files, files_with_tests, coverage_percentage,
                       tdd_compliance_score, violations_count, timestamp
                FROM tdd_metrics
                ORDER BY timestamp DESC
                LIMIT 1
            """)
            
            result = cursor.fetchone()
            return TDDMetric(*result) if result else None
    
    def save_violation(self, violation: TDDViolation):
        """Save TDD violation to database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO tdd_violations
                (violation_id, file_path, violation_type, severity,
                 line_count, test_coverage, timestamp, resolved)
                VALUES (?, ?, ?, ?, ?, ?, ?, FALSE)
            """, (
                violation.violation_id, violation.file_path, violation.violation_type,
                violation.severity, violation.line_count, violation.test_coverage,
                violation.timestamp
            ))
            conn.commit()
    
    def save_metric(self, metric: TDDMetric):
        """Save TDD metric to database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO tdd_metrics
                (metric_id, total_files, files_with_tests, coverage_percentage,
                 tdd_compliance_score, violations_count, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                metric.metric_id, metric.total_files, metric.files_with_tests,
                metric.coverage_percentage, metric.tdd_compliance_score,
                metric.violations_count, metric.timestamp
            ))
            conn.commit()
    
    def _find_source_files(self, patterns: List[str]) -> List[str]:
        """Find source files matching patterns."""
        source_files = []
        for pattern in patterns:
            source_files.extend(self.project_root.glob(f"**/{pattern}"))
        
        # Filter out test files and common non-source directories
        filtered_files = []
        for file_path in source_files:
            path_str = str(file_path)
            if not any(exclude in path_str.lower() for exclude in 
                      ['test', 'spec', '__pycache__', '.git', 'node_modules']):
                filtered_files.append(path_str)
        
        return filtered_files
    
    def _find_test_files(self) -> List[str]:
        """Find test files in project."""
        test_patterns = ["**/test_*.py", "**/tests/**/*.py", "**/*_test.py", 
                        "**/*_spec.py", "**/spec/**/*.py"]
        test_files = []
        
        for pattern in test_patterns:
            test_files.extend(self.project_root.glob(pattern))
        
        return [str(f) for f in test_files]
    
    def _has_corresponding_test(self, source_file: str, test_files: List[str]) -> bool:
        """Check if source file has corresponding test."""
        source_name = Path(source_file).stem
        source_dir = Path(source_file).parent.name
        
        for test_file in test_files:
            test_name = Path(test_file).stem
            test_dir = Path(test_file).parent.name
            
            # Various test naming conventions
            if (f"test_{source_name}" in test_name or
                f"{source_name}_test" in test_name or
                f"{source_name}_spec" in test_name or
                (source_name in test_name and source_dir in test_file)):
                return True
        
        return False
    
    def _create_no_test_violation(self, file_path: str) -> TDDViolation:
        """Create violation for missing test file."""
        line_count = self._count_lines(file_path)
        
        return TDDViolation(
            violation_id=f"no-test-{Path(file_path).stem}-{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            file_path=file_path,
            violation_type="no_test",
            severity="critical" if line_count > 100 else "warning",
            line_count=line_count,
            test_coverage=0.0,
            timestamp=datetime.now().isoformat()
        )
    
    def _count_lines(self, file_path: str) -> int:
        """Count lines in file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return sum(1 for _ in f)
        except Exception:
            return 0
    
    def _calculate_tdd_score(self, files_with_tests: int, total_files: int, violations: int) -> float:
        """Calculate TDD compliance score (0-100)."""
        if total_files == 0:
            return 100.0
        
        base_score = (files_with_tests / total_files) * 100
        violation_penalty = min(violations * 2, 20)  # Max 20 point penalty
        
        return max(0.0, base_score - violation_penalty)


def main():
    """CLI interface for TDD enforcement micro-component."""
    import sys
    
    if len(sys.argv) < 2:
        print("TDD Enforcement Micro-Component")
        print("Commands:")
        print("  scan [patterns]                      - Scan project for TDD compliance")
        print("  check <file_path>                    - Check single file TDD compliance")
        print("  violations [severity] [limit]        - List TDD violations")
        print("  metric                               - Show latest TDD compliance metric")
        return
    
    tdd_enforcer = TDDEnforcementMicro()
    command = sys.argv[1]
    
    if command == "scan":
        patterns = sys.argv[2:] if len(sys.argv) > 2 else None
        metric = tdd_enforcer.scan_tdd_compliance(patterns)
        
        print(f"TDD Compliance Scan Results:")
        print(f"  Total Files: {metric.total_files}")
        print(f"  Files with Tests: {metric.files_with_tests}")
        print(f"  Coverage: {metric.coverage_percentage:.1f}%")
        print(f"  TDD Score: {metric.tdd_compliance_score:.1f}/100")
        print(f"  Violations: {metric.violations_count}")
    
    elif command == "check":
        if len(sys.argv) < 3:
            print("Usage: check <file_path>")
            return
        
        file_path = sys.argv[2]
        result = tdd_enforcer.check_file_tdd_compliance(file_path)
        
        if "error" in result:
            print(f"❌ {result['error']}")
            return
        
        print(f"TDD Compliance Check: {file_path}")
        print(f"  Has Test: {'✅' if result['has_test'] else '❌'}")
        print(f"  Line Count: {result['line_count']}")
        print(f"  Compliant: {'✅' if result['compliant'] else '❌'}")
        
        if result['violations']:
            print("  Violations:")
            for violation in result['violations']:
                print(f"    - {violation['type']}: {violation['message']}")
    
    elif command == "violations":
        severity = sys.argv[2] if len(sys.argv) > 2 else None
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 50
        violations = tdd_enforcer.get_tdd_violations(severity, limit)
        
        print(f"TDD Violations (last {limit}):")
        for violation in violations:
            print(f"  {violation.file_path}: {violation.violation_type} [{violation.severity}]")
    
    elif command == "metric":
        metric = tdd_enforcer.get_latest_tdd_metric()
        
        if metric:
            print(f"Latest TDD Compliance Metric:")
            print(f"  Score: {metric.tdd_compliance_score:.1f}/100")
            print(f"  Coverage: {metric.coverage_percentage:.1f}%")
            print(f"  Files: {metric.files_with_tests}/{metric.total_files}")
            print(f"  Violations: {metric.violations_count}")
            print(f"  Timestamp: {metric.timestamp}")
        else:
            print("No TDD metrics found. Run 'scan' first.")
    
    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()