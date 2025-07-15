#!/usr/bin/env python3
"""
PR Coverage Enforcement Micro-Component - XP Methodology Enforcement
Part of PM/XP Methodology Enforcer (Micro-Component #5)

This micro-component handles ONLY PR coverage enforcement for XP compliance.
Follows XP Small Releases principle: ≤350 lines, single responsibility.
"""

import json
import sqlite3
import subprocess
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PRCoverageViolation:
    """PR coverage violation record for micro-component."""
    violation_id: str
    pr_number: int
    pr_title: str
    line_count: int
    file_count: int
    violation_type: str  # 'size_violation', 'no_tests', 'insufficient_coverage'
    severity: str  # 'critical', 'warning', 'info'
    branch_name: str
    timestamp: str


@dataclass
class PRCoverageMetric:
    """PR coverage compliance metric for micro-component."""
    metric_id: str
    pr_number: int
    pr_title: str
    line_count: int
    file_count: int
    test_coverage: float
    xp_compliance_score: float
    violations_count: int
    timestamp: str


class PRCoverageEnforcementMicro:
    """Micro-component for PR coverage enforcement functionality only."""
    
    def __init__(self, db_path: str = "pr_coverage_micro.db"):
        self.db_path = db_path
        self.xp_size_limit = 1000  # XP Small Releases limit
        self.init_database()
    
    def init_database(self):
        """Initialize minimal database for PR coverage enforcement."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pr_coverage_violations (
                    violation_id TEXT PRIMARY KEY,
                    pr_number INTEGER NOT NULL,
                    pr_title TEXT NOT NULL,
                    line_count INTEGER NOT NULL,
                    file_count INTEGER NOT NULL,
                    violation_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    branch_name TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    resolved BOOLEAN DEFAULT FALSE
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pr_coverage_metrics (
                    metric_id TEXT PRIMARY KEY,
                    pr_number INTEGER NOT NULL,
                    pr_title TEXT NOT NULL,
                    line_count INTEGER NOT NULL,
                    file_count INTEGER NOT NULL,
                    test_coverage REAL NOT NULL,
                    xp_compliance_score REAL NOT NULL,
                    violations_count INTEGER NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)
            conn.commit()
    
    def analyze_pr_coverage(self, pr_number: int) -> PRCoverageMetric:
        """Analyze PR coverage compliance - core functionality."""
        pr_info = self._get_pr_info(pr_number)
        if not pr_info:
            raise ValueError(f"PR #{pr_number} not found")
        
        # Get PR statistics
        line_count = self._count_pr_lines(pr_info["branch"])
        file_count = self._count_pr_files(pr_info["branch"])
        test_coverage = self._calculate_pr_test_coverage(pr_info["branch"])
        
        # Check for violations
        violations = self._check_pr_violations(pr_number, pr_info, line_count, file_count)
        
        # Calculate XP compliance score
        xp_score = self._calculate_xp_compliance_score(line_count, file_count, test_coverage, len(violations))
        
        metric = PRCoverageMetric(
            metric_id=f"pr-coverage-{pr_number}-{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            pr_number=pr_number,
            pr_title=pr_info["title"],
            line_count=line_count,
            file_count=file_count,
            test_coverage=test_coverage,
            xp_compliance_score=xp_score,
            violations_count=len(violations),
            timestamp=datetime.now().isoformat()
        )
        
        # Save violations and metric
        for violation in violations:
            self.save_violation(violation)
        self.save_metric(metric)
        
        return metric
    
    def check_pr_xp_compliance(self, pr_number: int) -> Dict:
        """Check PR XP compliance - core functionality."""
        try:
            metric = self.analyze_pr_coverage(pr_number)
            violations = self.get_pr_violations(pr_number)
            
            return {
                "pr_number": pr_number,
                "compliant": metric.xp_compliance_score >= 80,
                "score": metric.xp_compliance_score,
                "line_count": metric.line_count,
                "file_count": metric.file_count,
                "test_coverage": metric.test_coverage,
                "violations": len(violations),
                "size_compliant": metric.line_count <= self.xp_size_limit,
                "recommendations": self._generate_recommendations(metric, violations)
            }
        except Exception as e:
            return {"error": str(e), "compliant": False}
    
    def get_pr_violations(self, pr_number: int = None, severity: str = None) -> List[PRCoverageViolation]:
        """Get PR violations - core functionality."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT violation_id, pr_number, pr_title, line_count, file_count,
                       violation_type, severity, branch_name, timestamp
                FROM pr_coverage_violations
                WHERE resolved = FALSE
            """
            params = []
            
            if pr_number:
                query += " AND pr_number = ?"
                params.append(pr_number)
            
            if severity:
                query += " AND severity = ?"
                params.append(severity)
            
            query += " ORDER BY timestamp DESC LIMIT 50"
            
            cursor.execute(query, params)
            return [PRCoverageViolation(*row) for row in cursor.fetchall()]
    
    def get_pr_metrics(self, limit: int = 10) -> List[PRCoverageMetric]:
        """Get recent PR metrics - core functionality."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT metric_id, pr_number, pr_title, line_count, file_count,
                       test_coverage, xp_compliance_score, violations_count, timestamp
                FROM pr_coverage_metrics
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            
            return [PRCoverageMetric(*row) for row in cursor.fetchall()]
    
    def save_violation(self, violation: PRCoverageViolation):
        """Save PR coverage violation to database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO pr_coverage_violations
                (violation_id, pr_number, pr_title, line_count, file_count,
                 violation_type, severity, branch_name, timestamp, resolved)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, FALSE)
            """, (
                violation.violation_id, violation.pr_number, violation.pr_title,
                violation.line_count, violation.file_count, violation.violation_type,
                violation.severity, violation.branch_name, violation.timestamp
            ))
            conn.commit()
    
    def save_metric(self, metric: PRCoverageMetric):
        """Save PR coverage metric to database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO pr_coverage_metrics
                (metric_id, pr_number, pr_title, line_count, file_count,
                 test_coverage, xp_compliance_score, violations_count, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metric.metric_id, metric.pr_number, metric.pr_title,
                metric.line_count, metric.file_count, metric.test_coverage,
                metric.xp_compliance_score, metric.violations_count, metric.timestamp
            ))
            conn.commit()
    
    def _get_pr_info(self, pr_number: int) -> Optional[Dict]:
        """Get PR information from GitHub CLI."""
        try:
            result = subprocess.run(
                ["gh", "pr", "view", str(pr_number), "--json", "title,headRefName"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                return json.loads(result.stdout)
        except Exception:
            pass
        return None
    
    def _count_pr_lines(self, branch: str) -> int:
        """Count lines in PR branch."""
        try:
            result = subprocess.run(
                ["git", "diff", "--stat", f"main...{branch}"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                # Parse git diff --stat output for line count
                lines = result.stdout.strip().split('\n')
                if lines:
                    last_line = lines[-1]
                    # Extract insertions and deletions
                    match = re.search(r'(\d+) insertion[s]?.*?(\d+) deletion[s]?', last_line)
                    if match:
                        return int(match.group(1)) + int(match.group(2))
        except Exception:
            pass
        return 0
    
    def _count_pr_files(self, branch: str) -> int:
        """Count files changed in PR branch."""
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", f"main...{branch}"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                return len([f for f in result.stdout.strip().split('\n') if f])
        except Exception:
            pass
        return 0
    
    def _calculate_pr_test_coverage(self, branch: str) -> float:
        """Calculate test coverage for PR branch."""
        try:
            # Simple heuristic: count test files vs source files
            result = subprocess.run(
                ["git", "diff", "--name-only", f"main...{branch}"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                files = result.stdout.strip().split('\n')
                test_files = [f for f in files if 'test' in f.lower() or 'spec' in f.lower()]
                source_files = [f for f in files if f.endswith(('.py', '.js', '.ts', '.java', '.rb', '.go'))]
                
                if source_files:
                    return (len(test_files) / len(source_files)) * 100
        except Exception:
            pass
        return 0.0
    
    def _check_pr_violations(self, pr_number: int, pr_info: Dict, line_count: int, file_count: int) -> List[PRCoverageViolation]:
        """Check PR for XP violations."""
        violations = []
        
        # Size violation check
        if line_count > self.xp_size_limit:
            violations.append(PRCoverageViolation(
                violation_id=f"size-{pr_number}-{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                pr_number=pr_number,
                pr_title=pr_info["title"],
                line_count=line_count,
                file_count=file_count,
                violation_type="size_violation",
                severity="critical" if line_count > 5000 else "warning",
                branch_name=pr_info["headRefName"],
                timestamp=datetime.now().isoformat()
            ))
        
        return violations
    
    def _calculate_xp_compliance_score(self, line_count: int, file_count: int, test_coverage: float, violations: int) -> float:
        """Calculate XP compliance score (0-100)."""
        score = 100.0
        
        # Size penalty
        if line_count > self.xp_size_limit:
            penalty = min((line_count - self.xp_size_limit) / 100, 30)
            score -= penalty
        
        # Test coverage bonus/penalty
        if test_coverage >= 50:
            score += min(test_coverage / 10, 10)
        else:
            score -= (50 - test_coverage) / 5
        
        # Violation penalty
        score -= violations * 5
        
        return max(0.0, min(100.0, score))
    
    def _generate_recommendations(self, metric: PRCoverageMetric, violations: List[PRCoverageViolation]) -> List[str]:
        """Generate improvement recommendations."""
        recommendations = []
        
        if metric.line_count > self.xp_size_limit:
            recommendations.append(f"Break PR into smaller components (current: {metric.line_count} lines, limit: {self.xp_size_limit})")
        
        if metric.test_coverage < 50:
            recommendations.append(f"Add more test coverage (current: {metric.test_coverage:.1f}%, target: 50%+)")
        
        if metric.file_count > 10:
            recommendations.append(f"Consider reducing scope (current: {metric.file_count} files)")
        
        return recommendations


def main():
    """CLI interface for PR coverage enforcement micro-component."""
    import sys
    
    if len(sys.argv) < 2:
        print("PR Coverage Enforcement Micro-Component")
        print("Commands:")
        print("  analyze <pr_number>                  - Analyze PR coverage compliance")
        print("  check <pr_number>                    - Check PR XP compliance")
        print("  violations [pr_number] [severity]    - List PR violations")
        print("  metrics [limit]                      - Show recent PR metrics")
        return
    
    enforcer = PRCoverageEnforcementMicro()
    command = sys.argv[1]
    
    if command == "analyze":
        if len(sys.argv) < 3:
            print("Usage: analyze <pr_number>")
            return
        
        pr_number = int(sys.argv[2])
        try:
            metric = enforcer.analyze_pr_coverage(pr_number)
            print(f"PR #{pr_number} Coverage Analysis:")
            print(f"  Title: {metric.pr_title}")
            print(f"  Lines: {metric.line_count}")
            print(f"  Files: {metric.file_count}")
            print(f"  Test Coverage: {metric.test_coverage:.1f}%")
            print(f"  XP Score: {metric.xp_compliance_score:.1f}/100")
            print(f"  Violations: {metric.violations_count}")
        except Exception as e:
            print(f"❌ Error analyzing PR #{pr_number}: {e}")
    
    elif command == "check":
        if len(sys.argv) < 3:
            print("Usage: check <pr_number>")
            return
        
        pr_number = int(sys.argv[2])
        result = enforcer.check_pr_xp_compliance(pr_number)
        
        if "error" in result:
            print(f"❌ {result['error']}")
            return
        
        print(f"PR #{pr_number} XP Compliance Check:")
        print(f"  Compliant: {'✅' if result['compliant'] else '❌'}")
        print(f"  Score: {result['score']:.1f}/100")
        print(f"  Size: {result['line_count']} lines ({'✅' if result['size_compliant'] else '❌'})")
        print(f"  Test Coverage: {result['test_coverage']:.1f}%")
        print(f"  Violations: {result['violations']}")
        
        if result['recommendations']:
            print("  Recommendations:")
            for rec in result['recommendations']:
                print(f"    - {rec}")
    
    elif command == "violations":
        pr_number = int(sys.argv[2]) if len(sys.argv) > 2 else None
        severity = sys.argv[3] if len(sys.argv) > 3 else None
        violations = enforcer.get_pr_violations(pr_number, severity)
        
        print(f"PR Coverage Violations:")
        for violation in violations:
            print(f"  PR #{violation.pr_number}: {violation.violation_type} [{violation.severity}]")
            print(f"    {violation.line_count} lines - {violation.pr_title}")
    
    elif command == "metrics":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        metrics = enforcer.get_pr_metrics(limit)
        
        print(f"Recent PR Metrics (last {limit}):")
        for metric in metrics:
            print(f"  PR #{metric.pr_number}: {metric.xp_compliance_score:.1f}/100")
            print(f"    {metric.line_count} lines, {metric.test_coverage:.1f}% coverage")
    
    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()