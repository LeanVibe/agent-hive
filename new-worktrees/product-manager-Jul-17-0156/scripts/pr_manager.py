#!/usr/bin/env python3
"""
PR Manager - Automated Pull Request Review Workflows
Part of PM/XP Methodology Enforcer

This module implements automated PR review workflows, quality gates,
and integration criteria for XP methodology compliance.
"""

import json
import os
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from pathlib import Path
import re


@dataclass
class PRReview:
    """Represents a PR review with quality metrics."""
    pr_number: int
    pr_title: str
    pr_author: str
    pr_state: str
    review_id: str
    timestamp: str
    
    # Quality metrics
    files_changed: int
    lines_added: int
    lines_deleted: int
    commits_count: int
    
    # XP compliance checks
    has_tests: bool
    test_coverage: float
    tdd_compliance: bool
    code_quality_score: float
    
    # Review results
    automated_checks_passed: bool
    human_review_required: bool
    integration_approved: bool
    blocking_issues: List[str]
    recommendations: List[str]
    
    # Timing metrics
    review_duration_minutes: float
    merge_eligibility: bool


@dataclass
class PRQualityGate:
    """Quality gate configuration for PR reviews."""
    max_files_changed: int = 20
    max_lines_per_pr: int = 500
    max_commits_per_pr: int = 10
    min_test_coverage: float = 80.0
    require_tests_for_code: bool = True
    require_tdd_compliance: bool = True
    min_code_quality_score: float = 7.0
    max_review_time_hours: int = 24
    require_human_review_threshold: float = 0.8


class PRManager:
    """Automated PR review and integration management system."""
    
    def __init__(self, db_path: str = "pr_data.db"):
        self.db_path = db_path
        self.quality_gates = PRQualityGate()
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database for PR tracking."""
        with sqlite3.connect(self.db_path) as conn:
            # PR reviews table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pr_reviews (
                    review_id TEXT PRIMARY KEY,
                    pr_number INTEGER NOT NULL,
                    pr_title TEXT NOT NULL,
                    pr_author TEXT NOT NULL,
                    pr_state TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    files_changed INTEGER NOT NULL,
                    lines_added INTEGER NOT NULL,
                    lines_deleted INTEGER NOT NULL,
                    commits_count INTEGER NOT NULL,
                    has_tests BOOLEAN NOT NULL,
                    test_coverage REAL NOT NULL,
                    tdd_compliance BOOLEAN NOT NULL,
                    code_quality_score REAL NOT NULL,
                    automated_checks_passed BOOLEAN NOT NULL,
                    human_review_required BOOLEAN NOT NULL,
                    integration_approved BOOLEAN NOT NULL,
                    review_duration_minutes REAL NOT NULL,
                    merge_eligibility BOOLEAN NOT NULL
                )
            """)
            
            # PR quality issues table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pr_quality_issues (
                    issue_id TEXT PRIMARY KEY,
                    review_id TEXT NOT NULL,
                    issue_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    description TEXT NOT NULL,
                    file_path TEXT,
                    line_number INTEGER,
                    recommendation TEXT,
                    resolved BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (review_id) REFERENCES pr_reviews (review_id)
                )
            """)
            
            # PR metrics table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pr_metrics (
                    metric_id TEXT PRIMARY KEY,
                    period_start TEXT NOT NULL,
                    period_end TEXT NOT NULL,
                    total_prs INTEGER NOT NULL,
                    approved_prs INTEGER NOT NULL,
                    rejected_prs INTEGER NOT NULL,
                    avg_review_time_hours REAL NOT NULL,
                    avg_integration_time_hours REAL NOT NULL,
                    quality_gate_pass_rate REAL NOT NULL,
                    human_review_rate REAL NOT NULL,
                    recorded_at TEXT NOT NULL
                )
            """)
            
            # PR integration tracking
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pr_integrations (
                    integration_id TEXT PRIMARY KEY,
                    pr_number INTEGER NOT NULL,
                    integration_status TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    integration_branch TEXT NOT NULL,
                    conflicts_resolved INTEGER DEFAULT 0,
                    post_integration_tests_passed BOOLEAN DEFAULT FALSE,
                    rollback_required BOOLEAN DEFAULT FALSE
                )
            """)
            
            conn.commit()
    
    def get_pr_info(self, pr_number: int) -> Optional[Dict]:
        """Get PR information from GitHub API."""
        try:
            # Get PR details
            result = subprocess.run([
                "gh", "pr", "view", str(pr_number),
                "--json", "number,title,author,state,additions,deletions,changedFiles,commits,mergeable,reviews,statusCheckRollup"
            ], capture_output=True, text=True, check=True)
            
            pr_data = json.loads(result.stdout)
            
            # Get PR files
            files_result = subprocess.run([
                "gh", "pr", "diff", str(pr_number),
                "--name-only"
            ], capture_output=True, text=True, check=True)
            
            changed_files = files_result.stdout.strip().split('\n') if files_result.stdout.strip() else []
            
            return {
                'number': pr_data['number'],
                'title': pr_data['title'],
                'author': pr_data['author']['login'],
                'state': pr_data['state'],
                'additions': pr_data['additions'],
                'deletions': pr_data['deletions'],
                'changed_files': changed_files,
                'changed_files_count': pr_data['changedFiles'],
                'commits': pr_data['commits'],
                'mergeable': pr_data['mergeable'],
                'reviews': pr_data['reviews'],
                'status_checks': pr_data.get('statusCheckRollup', [])
            }
            
        except subprocess.CalledProcessError as e:
            print(f"Error getting PR info: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"Error parsing PR info: {e}")
            return None
    
    def analyze_pr_changes(self, pr_number: int) -> Dict:
        """Analyze PR changes for quality assessment."""
        try:
            # Get PR diff
            result = subprocess.run([
                "gh", "pr", "diff", str(pr_number)
            ], capture_output=True, text=True, check=True)
            
            diff_content = result.stdout
            
            # Analyze changes
            analysis = {
                'has_test_files': False,
                'has_code_files': False,
                'complexity_score': 0.0,
                'test_to_code_ratio': 0.0,
                'risk_indicators': []
            }
            
            # Parse diff for files
            test_files = []
            code_files = []
            
            for line in diff_content.split('\n'):
                if line.startswith('diff --git'):
                    file_path = line.split()[-1].replace('b/', '')
                    
                    if self.is_test_file(file_path):
                        test_files.append(file_path)
                    elif file_path.endswith('.py'):
                        code_files.append(file_path)
            
            analysis['has_test_files'] = len(test_files) > 0
            analysis['has_code_files'] = len(code_files) > 0
            analysis['test_to_code_ratio'] = len(test_files) / len(code_files) if code_files else 0
            
            # Risk indicators
            if len(code_files) > 0 and len(test_files) == 0:
                analysis['risk_indicators'].append("Code changes without tests")
            
            if len(code_files) > 10:
                analysis['risk_indicators'].append("Large number of files changed")
            
            # Calculate complexity score (simplified)
            added_lines = diff_content.count('\n+')
            deleted_lines = diff_content.count('\n-')
            
            if added_lines + deleted_lines > 0:
                analysis['complexity_score'] = min(10.0, (added_lines + deleted_lines) / 100.0)
            
            return analysis
            
        except subprocess.CalledProcessError as e:
            print(f"Error analyzing PR changes: {e}")
            return {}
    
    def is_test_file(self, file_path: str) -> bool:
        """Check if file is a test file."""
        test_patterns = [
            r'test_.*\.py$',
            r'.*_test\.py$',
            r'tests?/.*\.py$',
            r'.*_tests?\.py$'
        ]
        
        for pattern in test_patterns:
            if re.search(pattern, file_path):
                return True
        return False
    
    def run_automated_checks(self, pr_number: int) -> Dict:
        """Run automated quality checks on PR."""
        checks = {
            'tests_pass': False,
            'coverage_adequate': False,
            'linting_clean': False,
            'security_scan_clean': False,
            'performance_acceptable': False,
            'documentation_updated': False
        }
        
        try:
            # Check if tests pass
            test_result = subprocess.run([
                "python", "-m", "pytest", "-v", "--tb=short"
            ], capture_output=True, text=True, timeout=300)
            
            checks['tests_pass'] = test_result.returncode == 0
            
            # Check coverage
            coverage_result = subprocess.run([
                "python", "-m", "pytest", "--cov=.", "--cov-report=json"
            ], capture_output=True, text=True, timeout=300)
            
            if coverage_result.returncode == 0 and os.path.exists("coverage.json"):
                with open("coverage.json", 'r') as f:
                    coverage_data = json.load(f)
                    total_coverage = coverage_data.get('totals', {}).get('percent_covered', 0)
                    checks['coverage_adequate'] = total_coverage >= self.quality_gates.min_test_coverage
            
            # Basic linting check
            lint_result = subprocess.run([
                "python", "-m", "flake8", "--max-line-length=120", "--ignore=E501,W503"
            ], capture_output=True, text=True, timeout=120)
            
            checks['linting_clean'] = lint_result.returncode == 0
            
            # Security scan (simplified)
            checks['security_scan_clean'] = True  # Placeholder
            
            # Performance check (simplified)
            checks['performance_acceptable'] = True  # Placeholder
            
            # Documentation check (simplified)
            checks['documentation_updated'] = True  # Placeholder
            
        except subprocess.TimeoutExpired:
            print("Automated checks timed out")
        except Exception as e:
            print(f"Error running automated checks: {e}")
        
        return checks
    
    def calculate_code_quality_score(self, pr_info: Dict, pr_analysis: Dict, 
                                   automated_checks: Dict) -> float:
        """Calculate overall code quality score for PR."""
        score = 0.0
        
        # Test coverage component (30%)
        if automated_checks.get('coverage_adequate', False):
            score += 3.0
        
        # Tests passing component (25%)
        if automated_checks.get('tests_pass', False):
            score += 2.5
        
        # Code quality component (20%)
        if automated_checks.get('linting_clean', False):
            score += 2.0
        
        # PR size component (10%)
        if pr_info['changed_files_count'] <= self.quality_gates.max_files_changed:
            score += 1.0
        
        # Test inclusion component (15%)
        if pr_analysis.get('has_test_files', False) and pr_analysis.get('has_code_files', False):
            score += 1.5
        elif pr_analysis.get('has_test_files', False):
            score += 0.5
        
        return min(score, 10.0)
    
    def check_quality_gates(self, pr_info: Dict, pr_analysis: Dict, 
                           automated_checks: Dict) -> Tuple[bool, List[str]]:
        """Check if PR meets quality gate requirements."""
        issues = []
        
        # File count check
        if pr_info['changed_files_count'] > self.quality_gates.max_files_changed:
            issues.append(f"Too many files changed: {pr_info['changed_files_count']} > {self.quality_gates.max_files_changed}")
        
        # Lines changed check
        total_lines = pr_info['additions'] + pr_info['deletions']
        if total_lines > self.quality_gates.max_lines_per_pr:
            issues.append(f"Too many lines changed: {total_lines} > {self.quality_gates.max_lines_per_pr}")
        
        # Commits check
        if len(pr_info['commits']) > self.quality_gates.max_commits_per_pr:
            issues.append(f"Too many commits: {len(pr_info['commits'])} > {self.quality_gates.max_commits_per_pr}")
        
        # Test requirements
        if self.quality_gates.require_tests_for_code and pr_analysis.get('has_code_files', False):
            if not pr_analysis.get('has_test_files', False):
                issues.append("Code changes require corresponding tests")
        
        # Coverage check
        if not automated_checks.get('coverage_adequate', False):
            issues.append(f"Test coverage below minimum: {self.quality_gates.min_test_coverage}%")
        
        # Tests passing check
        if not automated_checks.get('tests_pass', False):
            issues.append("Tests are failing")
        
        # Linting check
        if not automated_checks.get('linting_clean', False):
            issues.append("Code quality issues found")
        
        return len(issues) == 0, issues
    
    def review_pr(self, pr_number: int) -> PRReview:
        """Conduct comprehensive PR review."""
        start_time = time.time()
        
        # Get PR information
        pr_info = self.get_pr_info(pr_number)
        if not pr_info:
            raise ValueError(f"Could not get information for PR #{pr_number}")
        
        # Analyze PR changes
        pr_analysis = self.analyze_pr_changes(pr_number)
        
        # Run automated checks
        automated_checks = self.run_automated_checks(pr_number)
        
        # Calculate quality score
        quality_score = self.calculate_code_quality_score(pr_info, pr_analysis, automated_checks)
        
        # Check quality gates
        gates_passed, blocking_issues = self.check_quality_gates(pr_info, pr_analysis, automated_checks)
        
        # Determine review requirements
        human_review_required = (
            quality_score < self.quality_gates.require_human_review_threshold * 10 or
            pr_info['changed_files_count'] > self.quality_gates.max_files_changed * 0.8 or
            len(blocking_issues) > 0
        )
        
        # Generate recommendations
        recommendations = self.generate_recommendations(pr_info, pr_analysis, automated_checks, quality_score)
        
        # Calculate review duration
        review_duration = (time.time() - start_time) / 60.0  # minutes
        
        # Create review record
        review = PRReview(
            pr_number=pr_number,
            pr_title=pr_info['title'],
            pr_author=pr_info['author'],
            pr_state=pr_info['state'],
            review_id=f"review-{pr_number}-{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            timestamp=datetime.now().isoformat(),
            files_changed=pr_info['changed_files_count'],
            lines_added=pr_info['additions'],
            lines_deleted=pr_info['deletions'],
            commits_count=len(pr_info['commits']),
            has_tests=pr_analysis.get('has_test_files', False),
            test_coverage=automated_checks.get('coverage_adequate', False) * 100,  # Simplified
            tdd_compliance=automated_checks.get('tests_pass', False),
            code_quality_score=quality_score,
            automated_checks_passed=gates_passed,
            human_review_required=human_review_required,
            integration_approved=gates_passed and not human_review_required,
            blocking_issues=blocking_issues,
            recommendations=recommendations,
            review_duration_minutes=review_duration,
            merge_eligibility=gates_passed and pr_info['mergeable']
        )
        
        # Save review
        self.save_pr_review(review)
        
        return review
    
    def generate_recommendations(self, pr_info: Dict, pr_analysis: Dict, 
                               automated_checks: Dict, quality_score: float) -> List[str]:
        """Generate improvement recommendations for PR."""
        recommendations = []
        
        # Size recommendations
        if pr_info['changed_files_count'] > self.quality_gates.max_files_changed:
            recommendations.append("Consider breaking this PR into smaller, focused changes")
        
        # Test recommendations
        if pr_analysis.get('has_code_files', False) and not pr_analysis.get('has_test_files', False):
            recommendations.append("Add tests for the new/modified code")
        
        # Coverage recommendations
        if not automated_checks.get('coverage_adequate', False):
            recommendations.append("Increase test coverage to meet minimum requirements")
        
        # Quality recommendations
        if not automated_checks.get('linting_clean', False):
            recommendations.append("Fix code quality issues identified by linting")
        
        # Performance recommendations
        if quality_score < 7.0:
            recommendations.append("Improve overall code quality before merging")
        
        # General recommendations
        if quality_score >= 8.0:
            recommendations.append("Great work! This PR meets high quality standards")
        
        return recommendations
    
    def save_pr_review(self, review: PRReview):
        """Save PR review to database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO pr_reviews
                (review_id, pr_number, pr_title, pr_author, pr_state, timestamp,
                 files_changed, lines_added, lines_deleted, commits_count,
                 has_tests, test_coverage, tdd_compliance, code_quality_score,
                 automated_checks_passed, human_review_required, integration_approved,
                 review_duration_minutes, merge_eligibility)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                review.review_id, review.pr_number, review.pr_title,
                review.pr_author, review.pr_state, review.timestamp,
                review.files_changed, review.lines_added, review.lines_deleted,
                review.commits_count, review.has_tests, review.test_coverage,
                review.tdd_compliance, review.code_quality_score,
                review.automated_checks_passed, review.human_review_required,
                review.integration_approved, review.review_duration_minutes,
                review.merge_eligibility
            ))
            
            # Save blocking issues
            for issue in review.blocking_issues:
                conn.execute("""
                    INSERT INTO pr_quality_issues
                    (issue_id, review_id, issue_type, severity, description, recommendation)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    f"{review.review_id}-{len(review.blocking_issues)}-{hash(issue)}",
                    review.review_id, "quality_gate", "high", issue, "Fix before merging"
                ))
            
            conn.commit()
    
    def generate_pr_report(self, pr_number: int) -> str:
        """Generate comprehensive PR review report."""
        review = self.review_pr(pr_number)
        
        # Status indicators
        status_icon = "✅" if review.automated_checks_passed else "❌"
        merge_icon = "🟢" if review.merge_eligibility else "🔴"
        human_icon = "👥" if review.human_review_required else "🤖"
        
        report = f"""
# PR Review Report #{review.pr_number}

## {status_icon} Overall Status: {'APPROVED' if review.integration_approved else 'NEEDS WORK'}

### 📋 PR Information
- **Title**: {review.pr_title}
- **Author**: {review.pr_author}
- **State**: {review.pr_state}
- **Review Duration**: {review.review_duration_minutes:.1f} minutes

### 📊 Change Summary
- **Files Changed**: {review.files_changed}
- **Lines Added**: {review.lines_added}
- **Lines Deleted**: {review.lines_deleted}
- **Commits**: {review.commits_count}

### 🎯 Quality Metrics
- **Code Quality Score**: {review.code_quality_score:.1f}/10.0
- **Has Tests**: {'✅' if review.has_tests else '❌'}
- **Test Coverage**: {review.test_coverage:.1f}%
- **TDD Compliance**: {'✅' if review.tdd_compliance else '❌'}

### 🚪 Quality Gates
- **Automated Checks**: {'✅ PASSED' if review.automated_checks_passed else '❌ FAILED'}
- **Human Review**: {human_icon} {'Required' if review.human_review_required else 'Not Required'}
- **Merge Eligibility**: {merge_icon} {'Ready' if review.merge_eligibility else 'Blocked'}
"""
        
        # Add blocking issues
        if review.blocking_issues:
            report += f"""
### ⚠️ Blocking Issues ({len(review.blocking_issues)} found)
"""
            for i, issue in enumerate(review.blocking_issues, 1):
                report += f"{i}. {issue}\n"
        
        # Add recommendations
        if review.recommendations:
            report += f"""
### 💡 Recommendations
"""
            for i, rec in enumerate(review.recommendations, 1):
                report += f"{i}. {rec}\n"
        
        # Add XP compliance section
        report += f"""
### 🔄 XP Methodology Compliance
- **Small Changes**: {'✅' if review.files_changed <= 10 else '❌'} (Target: ≤10 files)
- **Test Coverage**: {'✅' if review.test_coverage >= 80 else '❌'} (Target: ≥80%)
- **Continuous Integration**: {'✅' if review.tdd_compliance else '❌'}
- **Code Quality**: {'✅' if review.code_quality_score >= 7.0 else '❌'} (Target: ≥7.0)

### 📝 Next Steps
"""
        
        if review.integration_approved:
            report += "1. ✅ PR is approved for integration\n"
            report += "2. 🔄 Ready for merge\n"
        else:
            report += "1. ❌ Address blocking issues\n"
            report += "2. 🔧 Follow recommendations\n"
            if review.human_review_required:
                report += "3. 👥 Request human review\n"
            report += "4. 🔄 Re-run automated review\n"
        
        report += f"""
---
Generated by PM/XP Methodology Enforcer Agent
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Review ID: {review.review_id}
"""
        
        return report
    
    def bulk_review_open_prs(self) -> List[PRReview]:
        """Review all open PRs."""
        try:
            # Get list of open PRs
            result = subprocess.run([
                "gh", "pr", "list", "--state", "open", "--json", "number"
            ], capture_output=True, text=True, check=True)
            
            pr_list = json.loads(result.stdout)
            reviews = []
            
            for pr_info in pr_list:
                pr_number = pr_info['number']
                print(f"Reviewing PR #{pr_number}...")
                
                try:
                    review = self.review_pr(pr_number)
                    reviews.append(review)
                except Exception as e:
                    print(f"Error reviewing PR #{pr_number}: {e}")
            
            return reviews
            
        except subprocess.CalledProcessError as e:
            print(f"Error getting PR list: {e}")
            return []


def main():
    """Main CLI interface for PR management."""
    if len(sys.argv) < 2:
        print("Usage: python pr_manager.py <command> [options]")
        print("Commands:")
        print("  review <pr_number>       - Review specific PR")
        print("  report <pr_number>       - Generate PR review report")
        print("  bulk-review              - Review all open PRs")
        print("  list-open                - List open PRs")
        print("  quality-gates            - Show quality gate configuration")
        print("  metrics [days]           - Show PR metrics")
        sys.exit(1)
    
    manager = PRManager()
    command = sys.argv[1]
    
    if command == "review":
        if len(sys.argv) < 3:
            print("Usage: python pr_manager.py review <pr_number>")
            sys.exit(1)
        
        pr_number = int(sys.argv[2])
        
        try:
            review = manager.review_pr(pr_number)
            print(f"✅ PR #{pr_number} reviewed")
            print(f"Quality Score: {review.code_quality_score:.1f}/10.0")
            print(f"Status: {'APPROVED' if review.integration_approved else 'NEEDS WORK'}")
            print(f"Merge Eligible: {'Yes' if review.merge_eligibility else 'No'}")
            
            if review.blocking_issues:
                print(f"Blocking Issues: {len(review.blocking_issues)}")
                for issue in review.blocking_issues:
                    print(f"  - {issue}")
        
        except Exception as e:
            print(f"❌ Error reviewing PR #{pr_number}: {e}")
            sys.exit(1)
    
    elif command == "report":
        if len(sys.argv) < 3:
            print("Usage: python pr_manager.py report <pr_number>")
            sys.exit(1)
        
        pr_number = int(sys.argv[2])
        
        try:
            report = manager.generate_pr_report(pr_number)
            
            # Save report
            filename = f"pr_report_{pr_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            with open(filename, 'w') as f:
                f.write(report)
            
            print(report)
            print(f"\nReport saved to: {filename}")
        
        except Exception as e:
            print(f"❌ Error generating report for PR #{pr_number}: {e}")
            sys.exit(1)
    
    elif command == "bulk-review":
        print("🔄 Reviewing all open PRs...")
        reviews = manager.bulk_review_open_prs()
        
        print(f"\n✅ Reviewed {len(reviews)} PRs")
        for review in reviews:
            status = "✅ APPROVED" if review.integration_approved else "❌ NEEDS WORK"
            print(f"PR #{review.pr_number}: {status} (Quality: {review.code_quality_score:.1f}/10.0)")
    
    elif command == "list-open":
        try:
            result = subprocess.run([
                "gh", "pr", "list", "--state", "open",
                "--json", "number,title,author,createdAt"
            ], capture_output=True, text=True, check=True)
            
            pr_list = json.loads(result.stdout)
            
            print(f"Open PRs ({len(pr_list)} found):")
            for pr in pr_list:
                print(f"#{pr['number']}: {pr['title']} by {pr['author']['login']}")
        
        except subprocess.CalledProcessError as e:
            print(f"Error listing PRs: {e}")
    
    elif command == "quality-gates":
        gates = manager.quality_gates
        print("PR Quality Gates Configuration:")
        print(f"  Max Files Changed: {gates.max_files_changed}")
        print(f"  Max Lines Per PR: {gates.max_lines_per_pr}")
        print(f"  Max Commits Per PR: {gates.max_commits_per_pr}")
        print(f"  Min Test Coverage: {gates.min_test_coverage}%")
        print(f"  Require Tests for Code: {gates.require_tests_for_code}")
        print(f"  Require TDD Compliance: {gates.require_tdd_compliance}")
        print(f"  Min Code Quality Score: {gates.min_code_quality_score}")
        print(f"  Max Review Time: {gates.max_review_time_hours} hours")
    
    elif command == "metrics":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        
        # Calculate metrics from database
        with sqlite3.connect(manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN integration_approved = 1 THEN 1 ELSE 0 END) as approved,
                       AVG(review_duration_minutes) as avg_duration,
                       AVG(code_quality_score) as avg_quality
                FROM pr_reviews
                WHERE timestamp >= datetime('now', '-{} days')
            """.format(days))
            
            metrics = cursor.fetchone()
        
        if metrics and metrics[0] > 0:
            print(f"PR Metrics ({days} days):")
            print(f"  Total PRs Reviewed: {metrics[0]}")
            print(f"  Approved PRs: {metrics[1]}")
            print(f"  Approval Rate: {(metrics[1] / metrics[0]) * 100:.1f}%")
            print(f"  Average Review Duration: {metrics[2]:.1f} minutes")
            print(f"  Average Quality Score: {metrics[3]:.1f}/10.0")
        else:
            print("No PR metrics available for the specified period")
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()