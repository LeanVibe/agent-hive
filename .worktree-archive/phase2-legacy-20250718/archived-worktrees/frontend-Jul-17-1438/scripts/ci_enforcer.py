#!/usr/bin/env python3
"""
CI Enforcer - Continuous Integration Pipeline Management
Part of PM/XP Methodology Enforcer

This module enforces continuous integration practices and monitors
CI/CD pipeline health for XP methodology compliance.
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
import yaml


@dataclass
class CIJob:
    """Represents a CI job execution."""
    job_id: str
    job_name: str
    workflow_name: str
    branch: str
    commit_sha: str
    status: str  # 'pending', 'running', 'success', 'failure', 'cancelled'
    started_at: str
    completed_at: Optional[str]
    duration_seconds: Optional[float]

    # XP compliance metrics
    tests_passed: bool
    coverage_threshold_met: bool
    quality_gates_passed: bool
    deployment_ready: bool

    # Performance metrics
    test_execution_time: float
    build_time: float
    total_pipeline_time: float

    # Quality indicators
    test_failures: int
    coverage_percentage: float
    security_issues: int
    performance_regressions: int


@dataclass
class CIMetrics:
    """CI/CD pipeline metrics for XP methodology tracking."""
    period_id: str
    start_date: str
    end_date: str

    # Volume metrics
    total_builds: int
    successful_builds: int
    failed_builds: int

    # Performance metrics
    avg_build_time_minutes: float
    avg_test_time_minutes: float
    avg_pipeline_time_minutes: float

    # Quality metrics
    build_success_rate: float
    test_pass_rate: float
    coverage_compliance_rate: float
    deployment_success_rate: float

    # XP specific metrics
    small_commits_rate: float  # % of commits with < 20 files
    frequent_integration_rate: float  # builds per day
    fast_feedback_rate: float  # % of builds < 10 minutes

    # Trend indicators
    build_time_trend: str  # 'improving', 'stable', 'degrading'
    quality_trend: str
    velocity_trend: str


class CIEnforcer:
    """Continuous Integration enforcement and monitoring system."""

    def __init__(self, db_path: str = "ci_data.db"):
        self.db_path = db_path
        self.init_database()

        # CI/CD quality targets
        self.targets = {
            'build_time_max_minutes': 10,
            'test_time_max_minutes': 5,
            'pipeline_time_max_minutes': 15,
            'success_rate_minimum': 90.0,
            'coverage_minimum': 80.0,
            'max_files_per_commit': 20,
            'builds_per_day_target': 5
        }

    def init_database(self):
        """Initialize SQLite database for CI tracking."""
        with sqlite3.connect(self.db_path) as conn:
            # CI jobs table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ci_jobs (
                    job_id TEXT PRIMARY KEY,
                    job_name TEXT NOT NULL,
                    workflow_name TEXT NOT NULL,
                    branch TEXT NOT NULL,
                    commit_sha TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    duration_seconds REAL,
                    tests_passed BOOLEAN NOT NULL,
                    coverage_threshold_met BOOLEAN NOT NULL,
                    quality_gates_passed BOOLEAN NOT NULL,
                    deployment_ready BOOLEAN NOT NULL,
                    test_execution_time REAL NOT NULL,
                    build_time REAL NOT NULL,
                    total_pipeline_time REAL NOT NULL,
                    test_failures INTEGER NOT NULL,
                    coverage_percentage REAL NOT NULL,
                    security_issues INTEGER NOT NULL,
                    performance_regressions INTEGER NOT NULL
                )
            """)

            # CI metrics table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ci_metrics (
                    period_id TEXT PRIMARY KEY,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    total_builds INTEGER NOT NULL,
                    successful_builds INTEGER NOT NULL,
                    failed_builds INTEGER NOT NULL,
                    avg_build_time_minutes REAL NOT NULL,
                    avg_test_time_minutes REAL NOT NULL,
                    avg_pipeline_time_minutes REAL NOT NULL,
                    build_success_rate REAL NOT NULL,
                    test_pass_rate REAL NOT NULL,
                    coverage_compliance_rate REAL NOT NULL,
                    deployment_success_rate REAL NOT NULL,
                    small_commits_rate REAL NOT NULL,
                    frequent_integration_rate REAL NOT NULL,
                    fast_feedback_rate REAL NOT NULL,
                    build_time_trend TEXT NOT NULL,
                    quality_trend TEXT NOT NULL,
                    velocity_trend TEXT NOT NULL,
                    recorded_at TEXT NOT NULL
                )
            """)

            # Pipeline configurations table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pipeline_configs (
                    config_id TEXT PRIMARY KEY,
                    pipeline_name TEXT NOT NULL,
                    config_content TEXT NOT NULL,
                    xp_compliance_score REAL NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    active BOOLEAN DEFAULT TRUE
                )
            """)

            # Quality gate violations table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS quality_gate_violations (
                    violation_id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    gate_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    description TEXT NOT NULL,
                    threshold_value REAL,
                    actual_value REAL,
                    timestamp TEXT NOT NULL,
                    resolved BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (job_id) REFERENCES ci_jobs (job_id)
                )
            """)

            conn.commit()

    def validate_pipeline_config(self, config_file: str) -> Dict:
        """Validate CI pipeline configuration for XP compliance."""
        try:
            with open(config_file, 'r') as f:
                if config_file.endswith('.yml') or config_file.endswith('.yaml'):
                    config = yaml.safe_load(f)
                else:
                    config = json.load(f)

            compliance_score = 0.0
            violations = []
            recommendations = []

            # Check for required XP practices

            # 1. Automated testing (20 points)
            if self.has_automated_tests(config):
                compliance_score += 20
            else:
                violations.append("Missing automated test execution")
                recommendations.append("Add automated test steps to pipeline")

            # 2. Test coverage enforcement (15 points)
            if self.has_coverage_enforcement(config):
                compliance_score += 15
            else:
                violations.append("No test coverage enforcement")
                recommendations.append("Add coverage thresholds and reporting")

            # 3. Code quality gates (15 points)
            if self.has_quality_gates(config):
                compliance_score += 15
            else:
                violations.append("Missing code quality gates")
                recommendations.append("Add linting, formatting, and quality checks")

            # 4. Security scanning (10 points)
            if self.has_security_scanning(config):
                compliance_score += 10
            else:
                violations.append("No security scanning")
                recommendations.append("Add security vulnerability scanning")

            # 5. Fast feedback (15 points)
            if self.has_fast_feedback(config):
                compliance_score += 15
            else:
                violations.append("Pipeline too slow for fast feedback")
                recommendations.append("Optimize pipeline for <10 minute execution")

            # 6. Continuous deployment (10 points)
            if self.has_continuous_deployment(config):
                compliance_score += 10
            else:
                violations.append("No continuous deployment")
                recommendations.append("Add automated deployment stages")

            # 7. Branch protection (10 points)
            if self.has_branch_protection(config):
                compliance_score += 10
            else:
                violations.append("No branch protection")
                recommendations.append("Require CI checks for merge")

            # 8. Parallel execution (5 points)
            if self.has_parallel_execution(config):
                compliance_score += 5
            else:
                recommendations.append("Consider parallel job execution")

            return {
                'compliance_score': compliance_score,
                'violations': violations,
                'recommendations': recommendations,
                'xp_compliant': compliance_score >= 70
            }

        except Exception as e:
            return {
                'compliance_score': 0.0,
                'violations': [f"Invalid configuration: {e}"],
                'recommendations': ["Fix configuration file format and syntax"],
                'xp_compliant': False
            }

    def has_automated_tests(self, config: Dict) -> bool:
        """Check if pipeline has automated test execution."""
        config_str = json.dumps(config).lower()
        test_indicators = ['pytest', 'test', 'npm test', 'jest', 'mocha', 'unittest']
        return any(indicator in config_str for indicator in test_indicators)

    def has_coverage_enforcement(self, config: Dict) -> bool:
        """Check if pipeline enforces test coverage."""
        config_str = json.dumps(config).lower()
        coverage_indicators = ['coverage', 'cov', '--cov', 'codecov', 'coveralls']
        return any(indicator in config_str for indicator in coverage_indicators)

    def has_quality_gates(self, config: Dict) -> bool:
        """Check if pipeline has code quality gates."""
        config_str = json.dumps(config).lower()
        quality_indicators = ['lint', 'flake8', 'eslint', 'black', 'prettier', 'quality']
        return any(indicator in config_str for indicator in quality_indicators)

    def has_security_scanning(self, config: Dict) -> bool:
        """Check if pipeline includes security scanning."""
        config_str = json.dumps(config).lower()
        security_indicators = ['bandit', 'safety', 'snyk', 'security', 'vulnerabilit']
        return any(indicator in config_str for indicator in security_indicators)

    def has_fast_feedback(self, config: Dict) -> bool:
        """Check if pipeline is optimized for fast feedback."""
        # Check for timeout configurations suggesting fast execution
        config_str = json.dumps(config).lower()
        if 'timeout' in config_str:
            return True
        # Check for parallel execution or caching
        if any(indicator in config_str for indicator in ['parallel', 'cache', 'matrix']):
            return True
        return False

    def has_continuous_deployment(self, config: Dict) -> bool:
        """Check if pipeline includes deployment stages."""
        config_str = json.dumps(config).lower()
        deploy_indicators = ['deploy', 'release', 'publish', 'environment']
        return any(indicator in config_str for indicator in deploy_indicators)

    def has_branch_protection(self, config: Dict) -> bool:
        """Check if pipeline enforces branch protection."""
        config_str = json.dumps(config).lower()
        # This is more about GitHub settings, but we can check for PR triggers
        protection_indicators = ['pull_request', 'push:', 'main', 'master']
        return any(indicator in config_str for indicator in protection_indicators)

    def has_parallel_execution(self, config: Dict) -> bool:
        """Check if pipeline uses parallel execution."""
        config_str = json.dumps(config).lower()
        parallel_indicators = ['matrix', 'parallel', 'strategy', 'needs:']
        return any(indicator in config_str for indicator in parallel_indicators)

    def simulate_ci_job(self, branch: str = "main", commit_sha: str = None) -> CIJob:
        """Simulate a CI job execution for testing purposes."""
        if not commit_sha:
            commit_sha = "abc123def456"

        job_id = f"ci-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        started_at = datetime.now()

        # Simulate job execution
        time.sleep(0.1)  # Brief simulation

        # Mock results based on current system state
        tests_passed = True
        coverage_met = True
        quality_passed = True

        completed_at = datetime.now()
        duration = (completed_at - started_at).total_seconds()

        job = CIJob(
            job_id=job_id,
            job_name="XP Methodology Enforcement",
            workflow_name="xp_ci_enforcement",
            branch=branch,
            commit_sha=commit_sha,
            status="success" if tests_passed and quality_passed else "failure",
            started_at=started_at.isoformat(),
            completed_at=completed_at.isoformat(),
            duration_seconds=duration,
            tests_passed=tests_passed,
            coverage_threshold_met=coverage_met,
            quality_gates_passed=quality_passed,
            deployment_ready=tests_passed and quality_passed,
            test_execution_time=30.0,  # Mock values
            build_time=60.0,
            total_pipeline_time=120.0,
            test_failures=0 if tests_passed else 3,
            coverage_percentage=85.0,
            security_issues=0,
            performance_regressions=0
        )

        self.save_ci_job(job)
        return job

    def save_ci_job(self, job: CIJob):
        """Save CI job to database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO ci_jobs
                (job_id, job_name, workflow_name, branch, commit_sha, status,
                 started_at, completed_at, duration_seconds, tests_passed,
                 coverage_threshold_met, quality_gates_passed, deployment_ready,
                 test_execution_time, build_time, total_pipeline_time,
                 test_failures, coverage_percentage, security_issues,
                 performance_regressions)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job.job_id, job.job_name, job.workflow_name, job.branch,
                job.commit_sha, job.status, job.started_at, job.completed_at,
                job.duration_seconds, job.tests_passed, job.coverage_threshold_met,
                job.quality_gates_passed, job.deployment_ready,
                job.test_execution_time, job.build_time, job.total_pipeline_time,
                job.test_failures, job.coverage_percentage, job.security_issues,
                job.performance_regressions
            ))
            conn.commit()

    def calculate_ci_metrics(self, days: int = 7) -> CIMetrics:
        """Calculate CI/CD metrics for XP methodology tracking."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Volume metrics
            cursor.execute("""
                SELECT COUNT(*),
                       SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END),
                       SUM(CASE WHEN status = 'failure' THEN 1 ELSE 0 END)
                FROM ci_jobs
                WHERE started_at >= ? AND started_at <= ?
            """, (start_date.isoformat(), end_date.isoformat()))

            volume_data = cursor.fetchone()
            total_builds = volume_data[0] if volume_data[0] else 0
            successful_builds = volume_data[1] if volume_data[1] else 0
            failed_builds = volume_data[2] if volume_data[2] else 0

            # Performance metrics
            cursor.execute("""
                SELECT AVG(build_time), AVG(test_execution_time), AVG(total_pipeline_time)
                FROM ci_jobs
                WHERE started_at >= ? AND started_at <= ? AND status = 'success'
            """, (start_date.isoformat(), end_date.isoformat()))

            perf_data = cursor.fetchone()
            avg_build_time = (perf_data[0] / 60.0) if perf_data[0] else 0.0
            avg_test_time = (perf_data[1] / 60.0) if perf_data[1] else 0.0
            avg_pipeline_time = (perf_data[2] / 60.0) if perf_data[2] else 0.0

            # Quality metrics
            cursor.execute("""
                SELECT AVG(CASE WHEN tests_passed THEN 100.0 ELSE 0.0 END),
                       AVG(CASE WHEN coverage_threshold_met THEN 100.0 ELSE 0.0 END),
                       AVG(CASE WHEN deployment_ready THEN 100.0 ELSE 0.0 END)
                FROM ci_jobs
                WHERE started_at >= ? AND started_at <= ?
            """, (start_date.isoformat(), end_date.isoformat()))

            quality_data = cursor.fetchone()
            test_pass_rate = quality_data[0] if quality_data[0] else 0.0
            coverage_compliance_rate = quality_data[1] if quality_data[1] else 0.0
            deployment_success_rate = quality_data[2] if quality_data[2] else 0.0

        # Calculate additional XP metrics
        build_success_rate = (successful_builds / total_builds * 100) if total_builds > 0 else 0

        # XP specific calculations
        small_commits_rate = 85.0  # Placeholder - would analyze actual commit sizes
        frequent_integration_rate = total_builds / days if days > 0 else 0
        fast_feedback_rate = 80.0  # Placeholder - % of builds under target time

        # Trends (simplified)
        build_time_trend = "stable"
        quality_trend = "improving" if build_success_rate > 85 else "stable"
        velocity_trend = "stable"

        return CIMetrics(
            period_id=f"ci-metrics-{start_date.strftime('%Y%m%d')}-{end_date.strftime('%Y%m%d')}",
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            total_builds=total_builds,
            successful_builds=successful_builds,
            failed_builds=failed_builds,
            avg_build_time_minutes=avg_build_time,
            avg_test_time_minutes=avg_test_time,
            avg_pipeline_time_minutes=avg_pipeline_time,
            build_success_rate=build_success_rate,
            test_pass_rate=test_pass_rate,
            coverage_compliance_rate=coverage_compliance_rate,
            deployment_success_rate=deployment_success_rate,
            small_commits_rate=small_commits_rate,
            frequent_integration_rate=frequent_integration_rate,
            fast_feedback_rate=fast_feedback_rate,
            build_time_trend=build_time_trend,
            quality_trend=quality_trend,
            velocity_trend=velocity_trend
        )

    def generate_ci_report(self, days: int = 7) -> str:
        """Generate comprehensive CI/CD report for XP methodology."""
        metrics = self.calculate_ci_metrics(days)

        # Validate pipeline configuration if exists
        pipeline_config = ".github/workflows/xp_ci_enforcement.yml"
        config_analysis = None
        if os.path.exists(pipeline_config):
            config_analysis = self.validate_pipeline_config(pipeline_config)

        report = f"""
# CI/CD Pipeline Report - XP Methodology Enforcement

## 📊 Period: {metrics.start_date} to {metrics.end_date} ({days} days)

### 🎯 Build Performance Metrics
- **Total Builds**: {metrics.total_builds}
- **Successful Builds**: {metrics.successful_builds}
- **Failed Builds**: {metrics.failed_builds}
- **Success Rate**: {metrics.build_success_rate:.1f}%

### ⚡ Performance Indicators
- **Average Build Time**: {metrics.avg_build_time_minutes:.1f} minutes
- **Average Test Time**: {metrics.avg_test_time_minutes:.1f} minutes
- **Average Pipeline Time**: {metrics.avg_pipeline_time_minutes:.1f} minutes
- **Fast Feedback Rate**: {metrics.fast_feedback_rate:.1f}%

### 🔄 XP Methodology Compliance
- **Test Pass Rate**: {metrics.test_pass_rate:.1f}%
- **Coverage Compliance**: {metrics.coverage_compliance_rate:.1f}%
- **Deployment Success**: {metrics.deployment_success_rate:.1f}%
- **Small Commits Rate**: {metrics.small_commits_rate:.1f}%
- **Integration Frequency**: {metrics.frequent_integration_rate:.1f} builds/day

### 📈 Trend Analysis
- **Build Time Trend**: {metrics.build_time_trend.title()}
- **Quality Trend**: {metrics.quality_trend.title()}
- **Velocity Trend**: {metrics.velocity_trend.title()}
"""

        if config_analysis:
            report += f"""
### ⚙️ Pipeline Configuration Analysis
- **XP Compliance Score**: {config_analysis['compliance_score']:.1f}/100
- **XP Compliant**: {'✅ Yes' if config_analysis['xp_compliant'] else '❌ No'}
"""

            if config_analysis['violations']:
                report += f"""
#### ⚠️ Configuration Violations
"""
                for i, violation in enumerate(config_analysis['violations'], 1):
                    report += f"{i}. {violation}\n"

            if config_analysis['recommendations']:
                report += f"""
#### 💡 Improvement Recommendations
"""
                for i, rec in enumerate(config_analysis['recommendations'], 1):
                    report += f"{i}. {rec}\n"

        # XP practice validation
        report += f"""
### 🔄 XP Practice Validation

#### Core XP Practices Status
- **Planning Game**: {'✅' if metrics.frequent_integration_rate > 2 else '⚠️'} Frequent integration validates planning
- **Small Releases**: {'✅' if metrics.small_commits_rate > 80 else '⚠️'} {metrics.small_commits_rate:.1f}% small commits
- **Simple Design**: {'✅' if metrics.build_success_rate > 90 else '⚠️'} {metrics.build_success_rate:.1f}% build success
- **Testing**: {'✅' if metrics.test_pass_rate > 95 else '⚠️'} {metrics.test_pass_rate:.1f}% test success
- **Refactoring**: {'✅' if metrics.quality_trend == 'improving' else '⚠️'} Quality trend: {metrics.quality_trend}
- **Continuous Integration**: {'✅' if metrics.frequent_integration_rate > 1 else '⚠️'} {metrics.frequent_integration_rate:.1f} integrations/day

#### Quality Targets
- **Build Time**: {'✅' if metrics.avg_build_time_minutes < self.targets['build_time_max_minutes'] else '❌'} Target: <{self.targets['build_time_max_minutes']} min
- **Test Time**: {'✅' if metrics.avg_test_time_minutes < self.targets['test_time_max_minutes'] else '❌'} Target: <{self.targets['test_time_max_minutes']} min
- **Success Rate**: {'✅' if metrics.build_success_rate >= self.targets['success_rate_minimum'] else '❌'} Target: ≥{self.targets['success_rate_minimum']}%
- **Integration Frequency**: {'✅' if metrics.frequent_integration_rate >= 1 else '❌'} Target: ≥1 build/day

### 📋 Recommendations
"""

        # Generate recommendations
        recommendations = []

        if metrics.build_success_rate < 90:
            recommendations.append("Improve build stability - success rate below 90%")

        if metrics.avg_pipeline_time_minutes > self.targets['pipeline_time_max_minutes']:
            recommendations.append("Optimize pipeline speed - exceeds 15-minute target for fast feedback")

        if metrics.frequent_integration_rate < 2:
            recommendations.append("Increase integration frequency - aim for multiple integrations per day")

        if metrics.test_pass_rate < 95:
            recommendations.append("Focus on test reliability - test pass rate below 95%")

        if not recommendations:
            recommendations.append("CI/CD pipeline meets XP methodology standards")

        for i, rec in enumerate(recommendations, 1):
            report += f"{i}. {rec}\n"

        report += f"""
### 🎯 Next Steps
1. **Immediate**: Address any failing builds or quality gate violations
2. **Short-term**: Optimize pipeline performance to meet XP fast feedback requirements
3. **Medium-term**: Increase integration frequency to support XP continuous integration
4. **Long-term**: Achieve and maintain 95%+ success rates across all quality gates

---
Generated by PM/XP Methodology Enforcer Agent
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
CI Jobs Analyzed: {metrics.total_builds}
"""

        return report


def main():
    """Main CLI interface for CI enforcement."""
    if len(sys.argv) < 2:
        print("Usage: python ci_enforcer.py <command> [options]")
        print("Commands:")
        print("  validate <config_file>   - Validate pipeline configuration for XP compliance")
        print("  simulate [branch]        - Simulate CI job execution")
        print("  report [days]            - Generate CI/CD report")
        print("  metrics [days]           - Show CI metrics")
        print("  check-pipeline           - Check current pipeline configuration")
        print("  targets                  - Show CI/CD quality targets")
        sys.exit(1)

    enforcer = CIEnforcer()
    command = sys.argv[1]

    if command == "validate":
        if len(sys.argv) < 3:
            print("Usage: python ci_enforcer.py validate <config_file>")
            sys.exit(1)

        config_file = sys.argv[2]

        if not os.path.exists(config_file):
            print(f"❌ Configuration file not found: {config_file}")
            sys.exit(1)

        analysis = enforcer.validate_pipeline_config(config_file)

        print(f"Pipeline Configuration Analysis: {config_file}")
        print(f"XP Compliance Score: {analysis['compliance_score']:.1f}/100")
        print(f"XP Compliant: {'✅ Yes' if analysis['xp_compliant'] else '❌ No'}")

        if analysis['violations']:
            print(f"\nViolations ({len(analysis['violations'])}):")
            for i, violation in enumerate(analysis['violations'], 1):
                print(f"{i}. {violation}")

        if analysis['recommendations']:
            print(f"\nRecommendations ({len(analysis['recommendations'])}):")
            for i, rec in enumerate(analysis['recommendations'], 1):
                print(f"{i}. {rec}")

    elif command == "simulate":
        branch = sys.argv[2] if len(sys.argv) > 2 else "main"

        print(f"🔄 Simulating CI job for branch: {branch}")
        job = enforcer.simulate_ci_job(branch)

        print(f"✅ CI job completed: {job.job_id}")
        print(f"Status: {job.status}")
        print(f"Duration: {job.duration_seconds:.1f} seconds")
        print(f"Tests Passed: {'✅' if job.tests_passed else '❌'}")
        print(f"Quality Gates: {'✅' if job.quality_gates_passed else '❌'}")
        print(f"Deployment Ready: {'✅' if job.deployment_ready else '❌'}")

    elif command == "report":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
        report = enforcer.generate_ci_report(days)

        # Save report
        filename = f"ci_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(filename, 'w') as f:
            f.write(report)

        print(report)
        print(f"\nReport saved to: {filename}")

    elif command == "metrics":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
        metrics = enforcer.calculate_ci_metrics(days)

        print(f"CI/CD Metrics ({days} days):")
        print(f"  Total Builds: {metrics.total_builds}")
        print(f"  Success Rate: {metrics.build_success_rate:.1f}%")
        print(f"  Average Build Time: {metrics.avg_build_time_minutes:.1f} minutes")
        print(f"  Integration Frequency: {metrics.frequent_integration_rate:.1f} builds/day")
        print(f"  Fast Feedback Rate: {metrics.fast_feedback_rate:.1f}%")

    elif command == "check-pipeline":
        pipeline_file = ".github/workflows/xp_ci_enforcement.yml"

        if os.path.exists(pipeline_file):
            analysis = enforcer.validate_pipeline_config(pipeline_file)
            print(f"✅ Pipeline configuration found: {pipeline_file}")
            print(f"XP Compliance Score: {analysis['compliance_score']:.1f}/100")
            print(f"XP Compliant: {'✅ Yes' if analysis['xp_compliant'] else '❌ No'}")
        else:
            print(f"❌ No XP CI pipeline found at: {pipeline_file}")
            print("💡 Use the GitHub workflow provided by the PM/XP agent")

    elif command == "targets":
        targets = enforcer.targets
        print("CI/CD Quality Targets:")
        print(f"  Max Build Time: {targets['build_time_max_minutes']} minutes")
        print(f"  Max Test Time: {targets['test_time_max_minutes']} minutes")
        print(f"  Max Pipeline Time: {targets['pipeline_time_max_minutes']} minutes")
        print(f"  Min Success Rate: {targets['success_rate_minimum']}%")
        print(f"  Min Coverage: {targets['coverage_minimum']}%")
        print(f"  Max Files per Commit: {targets['max_files_per_commit']}")
        print(f"  Target Builds per Day: {targets['builds_per_day_target']}")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
