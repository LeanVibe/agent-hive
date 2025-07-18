#!/usr/bin/env python3
"""
Advanced Quality Metrics Monitoring and Alerting System
LeanVibe Quality Agent - Real-time Quality Assurance

This script provides comprehensive quality monitoring with:
- Real-time test execution monitoring
- Quality metrics tracking and analysis
- Performance regression detection
- Automated alerting and reporting
- Quality trend analysis and predictions
"""

import json
import logging
import sqlite3
import statistics
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('quality_monitoring.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class QualityMetricsMonitor:
    """Advanced quality metrics monitoring and alerting system."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize the quality metrics monitor."""
        self.config = self._load_config(config_path)
        self.db_path = Path("quality_metrics.db")
        self.reports_dir = Path("quality_reports")
        self.reports_dir.mkdir(exist_ok=True)

        # Initialize database
        self._init_database()

        # Quality thresholds
        self.coverage_threshold = self.config.get("coverage_threshold", 85.0)
        self.performance_threshold = self.config.get(
            "performance_threshold_ms", 2000)
        self.regression_threshold = self.config.get(
            "regression_threshold_percent", 20)

        # Monitoring configuration
        self.monitoring_interval = self.config.get(
            "monitoring_interval_minutes", 30)
        self.trend_analysis_days = self.config.get("trend_analysis_days", 7)

        logger.info(
            "Quality Metrics Monitor initialized with advanced analytics")

    def _load_config(self, config_path: Optional[str]) -> Dict:
        """Load configuration from file or use defaults."""
        default_config = {
            "coverage_threshold": 85.0,
            "performance_threshold_ms": 2000,
            "regression_threshold_percent": 20,
            "monitoring_interval_minutes": 30,
            "trend_analysis_days": 7,
            "enable_alerts": True,
            "enable_performance_monitoring": True,
            "enable_coverage_monitoring": True,
            "enable_quality_gates": True
        }

        if config_path and Path(config_path).exists():
            try:
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                default_config.update(user_config)
            except Exception as e:
                logger.warning(
                    f"Failed to load config from {config_path}: {e}")

        return default_config

    def _init_database(self):
        """Initialize SQLite database for quality metrics."""
        conn = sqlite3.connect(str(self.db_path))

        # Test execution metrics table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS test_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                total_tests INTEGER,
                passed_tests INTEGER,
                failed_tests INTEGER,
                skipped_tests INTEGER,
                execution_time_ms INTEGER,
                coverage_percentage REAL,
                branch TEXT,
                commit_hash TEXT
            )
        """)

        # Performance metrics table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                test_suite TEXT,
                avg_execution_time_ms REAL,
                max_execution_time_ms REAL,
                min_execution_time_ms REAL,
                memory_usage_mb REAL,
                cpu_usage_percent REAL
            )
        """)

        # Quality alerts table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS quality_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                alert_type TEXT,
                severity TEXT,
                message TEXT,
                metrics JSON,
                resolved BOOLEAN DEFAULT FALSE
            )
        """)

        # Quality trends table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS quality_trends (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE,
                avg_coverage REAL,
                avg_execution_time REAL,
                total_tests INTEGER,
                success_rate REAL,
                quality_score REAL
            )
        """)

        conn.commit()
        conn.close()

        logger.info("Quality metrics database initialized")

    def run_comprehensive_quality_analysis(self) -> Dict:
        """Run complete quality analysis and monitoring."""
        logger.info("🔍 Starting comprehensive quality analysis")

        analysis_results = {
            "timestamp": datetime.now().isoformat(),
            "test_execution": self._analyze_test_execution(),
            "performance_metrics": self._analyze_performance_metrics(),
            "coverage_analysis": self._analyze_coverage_metrics(),
            "quality_trends": self._analyze_quality_trends(),
            "regression_detection": self._detect_performance_regressions(),
            "quality_gates": self._evaluate_quality_gates()
        }

        # Calculate overall quality score
        analysis_results["overall_quality_score"] = self._calculate_quality_score(
            analysis_results)
        analysis_results["quality_grade"] = self._determine_quality_grade(
            analysis_results["overall_quality_score"])

        # Store results in database
        self._store_analysis_results(analysis_results)

        # Check for alerts
        alerts = self._check_quality_alerts(analysis_results)
        analysis_results["alerts"] = alerts

        # Generate recommendations
        analysis_results["recommendations"] = self._generate_recommendations(
            analysis_results)

        # Save detailed report
        report_file = self.reports_dir / \
            f"quality_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(analysis_results, f, indent=2)

        logger.info(
            f"✅ Quality analysis complete. Report saved: {report_file}")
        return analysis_results

    def _analyze_test_execution(self) -> Dict:
        """Analyze current test execution metrics."""
        logger.info("Analyzing test execution metrics...")

        try:
            # Run pytest with coverage and timing
            cmd = [
                'python', '-m', 'pytest',
                '--cov=.claude',
                '--cov-report=json:coverage.json',
                '--durations=10',
                '--json-report',
                '--json-report-file=test_results.json',
                'tests/',
                '-v'
            ]

            start_time = time.time()
            subprocess.run(
                cmd, capture_output=True, text=True, timeout=300)
            execution_time = (time.time() - start_time) * \
                1000  # Convert to milliseconds

            # Parse test results
            test_metrics = {"execution_time_ms": execution_time}

            if Path("test_results.json").exists():
                try:
                    with open("test_results.json", 'r') as f:
                        test_data = json.load(f)

                    summary = test_data.get("summary", {})
                    test_metrics.update(
                        {
                            "total_tests": summary.get(
                                "total",
                                0),
                            "passed_tests": summary.get(
                                "passed",
                                0),
                            "failed_tests": summary.get(
                                "failed",
                                0),
                            "skipped_tests": summary.get(
                                "skipped",
                                0),
                            "error_tests": summary.get(
                                "error",
                                0),
                            "success_rate": (
                                summary.get(
                                    "passed",
                                    0) /
                                summary.get(
                                    "total",
                                    1)) *
                            100 if summary.get(
                                "total",
                                0) > 0 else 0})
                except Exception as e:
                    logger.error(f"Failed to parse test results: {e}")

            # Parse coverage results
            if Path("coverage.json").exists():
                try:
                    with open("coverage.json", 'r') as f:
                        coverage_data = json.load(f)

                    test_metrics["coverage_percentage"] = coverage_data.get(
                        "totals", {}).get("percent_covered", 0)
                except Exception as e:
                    logger.error(f"Failed to parse coverage results: {e}")

            return test_metrics

        except subprocess.TimeoutExpired:
            logger.error("Test execution timed out")
            return {"status": "timeout", "execution_time_ms": 300000}
        except Exception as e:
            logger.error(f"Test execution failed: {e}")
            return {"status": "error", "error": str(e)}

    def _analyze_performance_metrics(self) -> Dict:
        """Analyze test performance metrics."""
        logger.info("Analyzing performance metrics...")

        performance_data = {
            "test_suite_performance": [],
            "slow_tests": [],
            "memory_usage": self._get_memory_usage(),
            "cpu_usage": self._get_cpu_usage()
        }

        # Analyze individual test performance
        if Path("test_results.json").exists():
            try:
                with open("test_results.json", 'r') as f:
                    test_data = json.load(f)

                tests = test_data.get("tests", [])
                durations = [test.get("duration", 0)
                             for test in tests if test.get("duration")]

                if durations:
                    performance_data.update({
                        "avg_test_duration": statistics.mean(durations),
                        "max_test_duration": max(durations),
                        "min_test_duration": min(durations),
                        "median_test_duration": statistics.median(durations),
                        "total_test_duration": sum(durations)
                    })

                    # Identify slow tests (top 10% by duration)
                    slow_threshold = statistics.quantile(
                        durations, 0.9) if len(durations) > 10 else max(durations)
                    slow_tests = [
                        {
                            "test_name": test.get("nodeid", ""),
                            "duration": test.get("duration", 0),
                            "status": test.get("outcome", "")
                        }
                        for test in tests
                        if test.get("duration", 0) >= slow_threshold
                    ]
                    performance_data["slow_tests"] = sorted(
                        slow_tests, key=lambda x: x["duration"], reverse=True)[:10]

            except Exception as e:
                logger.error(f"Failed to analyze performance metrics: {e}")

        return performance_data

    def _analyze_coverage_metrics(self) -> Dict:
        """Analyze code coverage metrics."""
        logger.info("Analyzing coverage metrics...")

        coverage_data = {}

        if Path("coverage.json").exists():
            try:
                with open("coverage.json", 'r') as f:
                    coverage_json = json.load(f)

                totals = coverage_json.get("totals", {})
                coverage_data.update({
                    "overall_coverage": totals.get("percent_covered", 0),
                    "lines_covered": totals.get("covered_lines", 0),
                    "lines_missing": totals.get("missing_lines", 0),
                    "total_lines": totals.get("num_statements", 0),
                    "branches_covered": totals.get("covered_branches", 0),
                    "branches_missing": totals.get("missing_branches", 0),
                    "total_branches": totals.get("num_branches", 0)
                })

                # Analyze per-file coverage
                files = coverage_json.get("files", {})
                file_coverage = []

                for file_path, file_data in files.items():
                    summary = file_data.get("summary", {})
                    file_coverage.append({
                        "file": file_path,
                        "coverage": summary.get("percent_covered", 0),
                        "lines_covered": summary.get("covered_lines", 0),
                        "lines_missing": summary.get("missing_lines", 0)
                    })

                # Sort by lowest coverage first
                coverage_data["low_coverage_files"] = sorted(
                    [f for f in file_coverage if f["coverage"]
                        < self.coverage_threshold],
                    key=lambda x: x["coverage"]
                )[:10]

                # Files with good coverage
                coverage_data["high_coverage_files"] = [
                    f for f in file_coverage if f["coverage"] >= 95
                ]

            except Exception as e:
                logger.error(f"Failed to analyze coverage metrics: {e}")

        return coverage_data

    def _analyze_quality_trends(self) -> Dict:
        """Analyze quality trends over time."""
        logger.info("Analyzing quality trends...")

        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row

        # Get trends for the last N days
        cutoff_date = datetime.now() - timedelta(days=self.trend_analysis_days)

        trends_query = """
            SELECT date, avg_coverage, avg_execution_time, total_tests, success_rate, quality_score
            FROM quality_trends
            WHERE date >= ?
            ORDER BY date DESC
        """

        trends = []
        try:
            cursor = conn.execute(trends_query, (cutoff_date.date(),))
            trends = [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to analyze trends: {e}")
        finally:
            conn.close()

        if not trends:
            return {"status": "no_data", "trends": []}

        # Calculate trend analysis
        coverages = [t["avg_coverage"] for t in trends if t["avg_coverage"]]
        execution_times = [t["avg_execution_time"]
                           for t in trends if t["avg_execution_time"]]
        success_rates = [t["success_rate"]
                         for t in trends if t["success_rate"]]

        trend_analysis = {
            "total_data_points": len(trends),
            "date_range": {
                "start": trends[-1]["date"] if trends else None,
                "end": trends[0]["date"] if trends else None
            }
        }

        if coverages:
            trend_analysis["coverage_trend"] = {
                "current": coverages[0],
                "average": statistics.mean(coverages),
                "trend": "improving" if len(coverages) > 1 and coverages[0] > coverages[-1] else "declining" if len(coverages) > 1 else "stable",
                "change_percent": ((coverages[0] - coverages[-1]) / coverages[-1] * 100) if len(coverages) > 1 and coverages[-1] > 0 else 0
            }

        if execution_times:
            trend_analysis["performance_trend"] = {
                "current_ms": execution_times[0],
                "average_ms": statistics.mean(execution_times),
                "trend": "improving" if len(execution_times) > 1 and execution_times[0] < execution_times[-1] else "declining" if len(execution_times) > 1 else "stable",
                "change_percent": ((execution_times[0] - execution_times[-1]) / execution_times[-1] * 100) if len(execution_times) > 1 and execution_times[-1] > 0 else 0
            }

        if success_rates:
            trend_analysis["success_rate_trend"] = {
                "current": success_rates[0],
                "average": statistics.mean(success_rates),
                "trend": "improving" if len(success_rates) > 1 and success_rates[0] > success_rates[-1] else "declining" if len(success_rates) > 1 else "stable",
                "change_percent": ((success_rates[0] - success_rates[-1]) / success_rates[-1] * 100) if len(success_rates) > 1 and success_rates[-1] > 0 else 0
            }

        trend_analysis["historical_data"] = trends[:30]  # Last 30 data points

        return trend_analysis

    def _detect_performance_regressions(self) -> Dict:
        """Detect performance regressions."""
        logger.info("Detecting performance regressions...")

        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row

        regressions = []

        try:
            # Get recent performance data
            recent_query = """
                SELECT avg_execution_time_ms, timestamp
                FROM performance_metrics
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
                LIMIT 10
            """

            cutoff_time = datetime.now() - timedelta(hours=24)
            cursor = conn.execute(recent_query, (cutoff_time,))
            recent_data = [dict(row) for row in cursor.fetchall()]

            if len(recent_data) >= 5:
                recent_times = [d["avg_execution_time_ms"]
                                for d in recent_data[:5]]
                baseline_times = [d["avg_execution_time_ms"]
                                  for d in recent_data[5:]]

                recent_avg = statistics.mean(recent_times)
                baseline_avg = statistics.mean(
                    baseline_times) if baseline_times else recent_avg

                if baseline_avg > 0:
                    regression_percent = (
                        (recent_avg - baseline_avg) / baseline_avg) * 100

                    if regression_percent > self.regression_threshold:
                        regressions.append(
                            {
                                "type": "performance_regression",
                                "severity": "high" if regression_percent > 50 else "medium",
                                "regression_percent": regression_percent,
                                "recent_avg_ms": recent_avg,
                                "baseline_avg_ms": baseline_avg,
                                "description": f"Performance regression detected: {
                                    regression_percent:.1f}% slower than baseline"})

        except Exception as e:
            logger.error(f"Failed to detect regressions: {e}")
        finally:
            conn.close()

        return {
            "regressions_detected": len(regressions),
            "regressions": regressions
        }

    def _evaluate_quality_gates(self) -> Dict:
        """Evaluate quality gates against current metrics."""
        logger.info("Evaluating quality gates...")

        # Get current metrics
        current_execution = self._analyze_test_execution()
        current_coverage = self._analyze_coverage_metrics()
        self._analyze_performance_metrics()

        gates = {
            "coverage_gate": {
                "threshold": self.coverage_threshold,
                "current": current_coverage.get("overall_coverage", 0),
                "passed": current_coverage.get("overall_coverage", 0) >= self.coverage_threshold,
                "description": f"Code coverage must be >= {self.coverage_threshold}%"
            },
            "performance_gate": {
                "threshold_ms": self.performance_threshold,
                "current_ms": current_execution.get("execution_time_ms", 0),
                "passed": current_execution.get("execution_time_ms", 0) <= self.performance_threshold,
                "description": f"Test execution time must be <= {self.performance_threshold}ms"
            },
            "success_rate_gate": {
                "threshold": 95.0,
                "current": current_execution.get("success_rate", 0),
                "passed": current_execution.get("success_rate", 0) >= 95.0,
                "description": "Test success rate must be >= 95%"
            },
            "no_failed_tests_gate": {
                "threshold": 0,
                "current": current_execution.get("failed_tests", 0),
                "passed": current_execution.get("failed_tests", 0) == 0,
                "description": "No failed tests allowed"
            }
        }

        gates_passed = sum(1 for gate in gates.values() if gate["passed"])
        total_gates = len(gates)

        return {
            "gates_passed": gates_passed,
            "total_gates": total_gates,
            "overall_passed": gates_passed == total_gates,
            "pass_rate": (gates_passed / total_gates) * 100,
            "gates": gates
        }

    def _calculate_quality_score(self, analysis_results: Dict) -> float:
        """Calculate overall quality score (0-100)."""
        100.0

        # Coverage score (30% weight)
        coverage = analysis_results.get(
            "coverage_analysis", {}).get("overall_coverage", 0)
        coverage_score = min(coverage, 100) * 0.3

        # Performance score (25% weight)
        execution_time = analysis_results.get(
            "test_execution", {}).get("execution_time_ms", 0)
        performance_score = max(
            0, 100 - (execution_time / self.performance_threshold * 100)) * 0.25

        # Success rate score (25% weight)
        success_rate = analysis_results.get(
            "test_execution", {}).get("success_rate", 0)
        success_score = success_rate * 0.25

        # Quality gates score (20% weight)
        gates_passed = analysis_results.get(
            "quality_gates", {}).get("pass_rate", 0)
        gates_score = gates_passed * 0.2

        final_score = coverage_score + performance_score + success_score + gates_score
        return max(0.0, min(100.0, final_score))

    def _determine_quality_grade(self, score: float) -> str:
        """Determine quality grade based on score."""
        if score >= 95:
            return "A+"
        elif score >= 90:
            return "A"
        elif score >= 85:
            return "B+"
        elif score >= 80:
            return "B"
        elif score >= 75:
            return "C+"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"

    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024  # Convert to MB
        except BaseException:
            return 0.0

    def _get_cpu_usage(self) -> float:
        """Get current CPU usage percentage."""
        try:
            import psutil
            return psutil.cpu_percent(interval=1)
        except BaseException:
            return 0.0

    def _store_analysis_results(self, results: Dict):
        """Store analysis results in database."""
        conn = sqlite3.connect(str(self.db_path))

        try:
            # Store test execution metrics
            test_data = results.get("test_execution", {})
            if test_data:
                conn.execute("""
                    INSERT INTO test_executions
                    (timestamp, total_tests, passed_tests, failed_tests, skipped_tests,
                     execution_time_ms, coverage_percentage, branch, commit_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    datetime.now(),
                    test_data.get("total_tests", 0),
                    test_data.get("passed_tests", 0),
                    test_data.get("failed_tests", 0),
                    test_data.get("skipped_tests", 0),
                    test_data.get("execution_time_ms", 0),
                    test_data.get("coverage_percentage", 0),
                    self._get_current_branch(),
                    self._get_current_commit()
                ))

            # Store performance metrics
            perf_data = results.get("performance_metrics", {})
            if perf_data:
                conn.execute("""
                    INSERT INTO performance_metrics
                    (timestamp, test_suite, avg_execution_time_ms, max_execution_time_ms,
                     min_execution_time_ms, memory_usage_mb, cpu_usage_percent)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    datetime.now(),
                    "comprehensive",
                    perf_data.get("avg_test_duration", 0),
                    perf_data.get("max_test_duration", 0),
                    perf_data.get("min_test_duration", 0),
                    perf_data.get("memory_usage", 0),
                    perf_data.get("cpu_usage", 0)
                ))

            # Store daily quality trends
            today = datetime.now().date()
            conn.execute("""
                INSERT OR REPLACE INTO quality_trends
                (date, avg_coverage, avg_execution_time, total_tests, success_rate, quality_score)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                today,
                results.get("coverage_analysis", {}).get(
                    "overall_coverage", 0),
                test_data.get("execution_time_ms", 0),
                test_data.get("total_tests", 0),
                test_data.get("success_rate", 0),
                results.get("overall_quality_score", 0)
            ))

            conn.commit()

        except Exception as e:
            logger.error(f"Failed to store analysis results: {e}")
        finally:
            conn.close()

    def _check_quality_alerts(self, results: Dict) -> List[Dict]:
        """Check for quality alerts and store them."""
        alerts = []

        # Coverage alerts
        coverage = results.get("coverage_analysis", {}
                               ).get("overall_coverage", 0)
        if coverage < self.coverage_threshold:
            alerts.append({
                "type": "coverage_below_threshold",
                "severity": "high" if coverage < self.coverage_threshold - 10 else "medium",
                "message": f"Code coverage ({coverage:.1f}%) below threshold ({self.coverage_threshold}%)",
                "current_value": coverage,
                "threshold": self.coverage_threshold
            })

        # Performance alerts
        execution_time = results.get(
            "test_execution", {}).get("execution_time_ms", 0)
        if execution_time > self.performance_threshold:
            alerts.append(
                {
                    "type": "performance_regression",
                    "severity": "high" if execution_time > self.performance_threshold *
                    1.5 else "medium",
                    "message": f"Test execution time ({execution_time}ms) exceeds threshold ({
                        self.performance_threshold}ms)",
                    "current_value": execution_time,
                    "threshold": self.performance_threshold})

        # Failed tests alerts
        failed_tests = results.get("test_execution", {}).get("failed_tests", 0)
        if failed_tests > 0:
            alerts.append({
                "type": "test_failures",
                "severity": "critical" if failed_tests > 5 else "high",
                "message": f"{failed_tests} test(s) are currently failing",
                "current_value": failed_tests,
                "threshold": 0
            })

        # Quality score alerts
        quality_score = results.get("overall_quality_score", 100)
        if quality_score < 80:
            alerts.append({
                "type": "low_quality_score",
                "severity": "medium" if quality_score >= 70 else "high",
                "message": f"Overall quality score ({quality_score:.1f}) is below acceptable level",
                "current_value": quality_score,
                "threshold": 80
            })

        # Store alerts in database
        if alerts:
            self._store_alerts(alerts)

        return alerts

    def _store_alerts(self, alerts: List[Dict]):
        """Store quality alerts in database."""
        conn = sqlite3.connect(str(self.db_path))

        try:
            for alert in alerts:
                conn.execute("""
                    INSERT INTO quality_alerts
                    (timestamp, alert_type, severity, message, metrics)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    datetime.now(),
                    alert["type"],
                    alert["severity"],
                    alert["message"],
                    json.dumps(alert)
                ))

            conn.commit()
            logger.info(f"Stored {len(alerts)} quality alerts")

        except Exception as e:
            logger.error(f"Failed to store alerts: {e}")
        finally:
            conn.close()

    def _generate_recommendations(self, results: Dict) -> List[Dict]:
        """Generate improvement recommendations based on analysis."""
        recommendations = []

        # Coverage recommendations
        coverage = results.get("coverage_analysis", {}
                               ).get("overall_coverage", 0)
        if coverage < self.coverage_threshold:
            low_coverage_files = results.get(
                "coverage_analysis", {}).get("low_coverage_files", [])
            recommendations.append({
                "category": "coverage",
                "priority": "high",
                "title": "Improve Test Coverage",
                "description": f"Code coverage ({coverage:.1f}%) is below threshold ({self.coverage_threshold}%)",
                "actions": [
                    "Add unit tests for uncovered code paths",
                    f"Focus on files with low coverage: {', '.join([f['file'] for f in low_coverage_files[:3]])}",
                    "Consider integration tests for complex workflows",
                    "Review and remove dead code if applicable"
                ]
            })

        # Performance recommendations
        slow_tests = results.get(
            "performance_metrics", {}).get("slow_tests", [])
        if slow_tests:
            recommendations.append({
                "category": "performance",
                "priority": "medium",
                "title": "Optimize Slow Tests",
                "description": f"Found {len(slow_tests)} slow-running tests",
                "actions": [
                    "Optimize slow test setup and teardown",
                    "Consider mocking external dependencies",
                    "Review test data generation efficiency",
                    f"Focus on: {', '.join([t['test_name'].split('::')[-1] for t in slow_tests[:3]])}"
                ]
            })

        # Quality gate recommendations
        quality_gates = results.get("quality_gates", {})
        if not quality_gates.get("overall_passed", True):
            failed_gates = [name for name, gate in quality_gates.get(
                "gates", {}).items() if not gate["passed"]]
            recommendations.append({
                "category": "quality_gates",
                "priority": "high",
                "title": "Fix Quality Gate Failures",
                "description": f"Quality gates failing: {', '.join(failed_gates)}",
                "actions": [
                    "Address failing quality gates before deployment",
                    "Review quality gate thresholds if needed",
                    "Implement automated quality gate enforcement",
                    "Monitor quality gates in CI/CD pipeline"
                ]
            })

        # Trend-based recommendations
        trends = results.get("quality_trends", {})
        coverage_trend = trends.get("coverage_trend", {})
        if coverage_trend.get("trend") == "declining":
            recommendations.append({
                "category": "trends",
                "priority": "medium",
                "title": "Address Declining Coverage Trend",
                "description": f"Coverage has declined by {abs(coverage_trend.get('change_percent', 0)):.1f}% recently",
                "actions": [
                    "Investigate recent code changes affecting coverage",
                    "Ensure new features include adequate tests",
                    "Review and update testing strategy",
                    "Set up coverage monitoring alerts"
                ]
            })

        return recommendations

    def _get_current_branch(self) -> str:
        """Get current git branch."""
        try:
            result = subprocess.run(['git', 'branch', '--show-current'],
                                    capture_output=True, text=True, timeout=5)
            return result.stdout.strip() if result.returncode == 0 else "unknown"
        except BaseException:
            return "unknown"

    def _get_current_commit(self) -> str:
        """Get current git commit hash."""
        try:
            result = subprocess.run(['git', 'rev-parse', 'HEAD'],
                                    capture_output=True, text=True, timeout=5)
            return result.stdout.strip()[
                :8] if result.returncode == 0 else "unknown"
        except BaseException:
            return "unknown"

    def generate_quality_dashboard(self, results: Dict) -> str:
        """Generate HTML quality dashboard."""
        timestamp = results.get("timestamp", datetime.now().isoformat())
        quality_score = results.get("overall_quality_score", 0)
        quality_grade = results.get("quality_grade", "F")

        dashboard_html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>LeanVibe Quality Dashboard</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .dashboard {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }}
        .metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
        .metric-card {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .metric-value {{ font-size: 2em; font-weight: bold; color: #333; }}
        .metric-label {{ color: #666; font-size: 0.9em; margin-top: 5px; }}
        .quality-score {{ text-align: center; }}
        .score-circle {{ width: 120px; height: 120px; border-radius: 50%; margin: 0 auto; display: flex; align-items: center; justify-content: center; font-size: 2em; font-weight: bold; color: white; }}
        .grade-a {{ background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }}
        .grade-b {{ background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }}
        .grade-c {{ background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }}
        .grade-d {{ background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%); }}
        .grade-f {{ background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%); }}
        .alert {{ padding: 10px; margin: 10px 0; border-radius: 5px; }}
        .alert-critical {{ background-color: #ffebee; border-left: 4px solid #f44336; }}
        .alert-high {{ background-color: #fff3e0; border-left: 4px solid #ff9800; }}
        .alert-medium {{ background-color: #f3e5f5; border-left: 4px solid #9c27b0; }}
        .recommendations {{ background: white; padding: 20px; border-radius: 10px; margin-top: 20px; }}
        .recommendation {{ margin: 15px 0; padding: 15px; background: #f8f9fa; border-radius: 5px; }}
    </style>
</head>
<body>
    <div class="dashboard">
        <div class="header">
            <h1>🔍 LeanVibe Quality Dashboard</h1>
            <p>Generated: {timestamp}</p>
            <p>Overall Quality Score: {quality_score:.1f}/100 (Grade: {quality_grade})</p>
        </div>

        <div class="metrics-grid">
            <div class="metric-card quality-score">
                <div class="score-circle grade-{quality_grade.lower().replace('+', '').replace('-', '')}">
                    {quality_grade}
                </div>
                <div class="metric-label">Quality Grade</div>
            </div>
"""

        # Add test execution metrics
        test_data = results.get("test_execution", {})
        dashboard_html += f"""
            <div class="metric-card">
                <div class="metric-value">{test_data.get('total_tests', 0)}</div>
                <div class="metric-label">Total Tests</div>
            </div>

            <div class="metric-card">
                <div class="metric-value" style="color: green;">{test_data.get('passed_tests', 0)}</div>
                <div class="metric-label">Passed Tests</div>
            </div>

            <div class="metric-card">
                <div class="metric-value" style="color: red;">{test_data.get('failed_tests', 0)}</div>
                <div class="metric-label">Failed Tests</div>
            </div>
"""

        # Add coverage metrics
        coverage_data = results.get("coverage_analysis", {})
        dashboard_html += f"""
            <div class="metric-card">
                <div class="metric-value">{coverage_data.get('overall_coverage', 0):.1f}%</div>
                <div class="metric-label">Code Coverage</div>
            </div>

            <div class="metric-card">
                <div class="metric-value">{test_data.get('execution_time_ms', 0):.0f}ms</div>
                <div class="metric-label">Execution Time</div>
            </div>
        """

        dashboard_html += """
        </div>

        <!-- Alerts Section -->
        <div class="recommendations">
            <h2>🚨 Quality Alerts</h2>
"""

        alerts = results.get("alerts", [])
        if alerts:
            for alert in alerts:
                severity_class = f"alert-{alert['severity']}"
                dashboard_html += f"""
            <div class="alert {severity_class}">
                <strong>{alert['type'].replace('_', ' ').title()}:</strong> {alert['message']}
            </div>
"""
        else:
            dashboard_html += "<p>✅ No quality alerts detected</p>"

        # Add recommendations
        dashboard_html += """
            <h2>💡 Recommendations</h2>
"""

        recommendations = results.get("recommendations", [])
        if recommendations:
            for rec in recommendations:
                dashboard_html += f"""
            <div class="recommendation">
                <h3>{rec['title']} ({rec['priority'].upper()} priority)</h3>
                <p>{rec['description']}</p>
                <ul>
"""
                for action in rec['actions']:
                    dashboard_html += f"<li>{action}</li>"

                dashboard_html += """
                </ul>
            </div>
"""
        else:
            dashboard_html += "<p>✅ No specific recommendations at this time</p>"

        dashboard_html += """
        </div>
    </div>
</body>
</html>
"""

        # Save dashboard
        dashboard_file = self.reports_dir / \
            f"quality_dashboard_{
    datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        with open(dashboard_file, 'w') as f:
            f.write(dashboard_html)

        logger.info(f"Quality dashboard generated: {dashboard_file}")
        return str(dashboard_file)

    def generate_quality_report(self, results: Dict) -> str:
        """Generate comprehensive quality report."""
        timestamp = results.get("timestamp", datetime.now().isoformat())
        quality_score = results.get("overall_quality_score", 0)
        quality_grade = results.get("quality_grade", "F")

        report = f"""
# 🔍 LeanVibe Quality Monitoring Report

**Generated**: {timestamp}
**Overall Quality Score**: {quality_score:.1f}/100
**Quality Grade**: {quality_grade}

## 📊 Executive Summary

"""

        # Test execution summary
        test_data = results.get("test_execution", {})
        report += f"""
### Test Execution Results
- **Total Tests**: {test_data.get('total_tests', 0)}
- **Passed**: {test_data.get('passed_tests', 0)}
- **Failed**: {test_data.get('failed_tests', 0)}
- **Skipped**: {test_data.get('skipped_tests', 0)}
- **Success Rate**: {test_data.get('success_rate', 0):.1f}%
- **Execution Time**: {test_data.get('execution_time_ms', 0):.0f}ms

"""

        # Coverage analysis
        coverage_data = results.get("coverage_analysis", {})
        report += f"""
### Code Coverage Analysis
- **Overall Coverage**: {coverage_data.get('overall_coverage', 0):.1f}%
- **Lines Covered**: {coverage_data.get('lines_covered', 0)}
- **Lines Missing**: {coverage_data.get('lines_missing', 0)}
- **Total Lines**: {coverage_data.get('total_lines', 0)}

"""

        # Performance metrics
        perf_data = results.get("performance_metrics", {})
        report += f"""
### Performance Metrics
- **Average Test Duration**: {perf_data.get('avg_test_duration', 0):.3f}s
- **Slowest Test**: {perf_data.get('max_test_duration', 0):.3f}s
- **Fastest Test**: {perf_data.get('min_test_duration', 0):.3f}s
- **Memory Usage**: {perf_data.get('memory_usage', 0):.1f}MB

"""

        # Quality gates
        gates_data = results.get("quality_gates", {})
        report += f"""
### Quality Gates Status
- **Gates Passed**: {gates_data.get('gates_passed', 0)}/{gates_data.get('total_gates', 0)}
- **Overall Status**: {'✅ PASSED' if gates_data.get('overall_passed') else '❌ FAILED'}
- **Pass Rate**: {gates_data.get('pass_rate', 0):.1f}%

"""

        # Alerts
        alerts = results.get("alerts", [])
        if alerts:
            report += "### 🚨 Quality Alerts\n\n"
            for alert in alerts:
                severity_emoji = {"critical": "🔴", "high": "🟠",
                                  "medium": "🟡"}.get(alert["severity"], "🔵")
                report += f"- {severity_emoji} **{
                    alert['type'].replace(
                        '_', ' ').title()}**: {
                    alert['message']}\n"
        else:
            report += "### ✅ No Quality Alerts\n\nAll quality metrics are within acceptable thresholds.\n"

        report += "\n"

        # Recommendations
        recommendations = results.get("recommendations", [])
        if recommendations:
            report += "### 💡 Improvement Recommendations\n\n"
            for i, rec in enumerate(recommendations, 1):
                priority_emoji = {"high": "🔴", "medium": "🟠",
                                  "low": "🟡"}.get(rec["priority"], "🔵")
                report += f"{i}. {priority_emoji} **{
                    rec['title']}** ({
                    rec['priority'].upper()} priority)\n"
                report += f"   - {rec['description']}\n"
                for action in rec['actions']:
                    report += f"   - {action}\n"
                report += "\n"

        return report


def main():
    """Main function for quality metrics monitoring."""
    import argparse

    parser = argparse.ArgumentParser(
        description="LeanVibe Quality Metrics Monitoring")
    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument("--analyze", action="store_true",
                        help="Run quality analysis")
    parser.add_argument("--dashboard", action="store_true",
                        help="Generate HTML dashboard")
    parser.add_argument("--monitor", action="store_true",
                        help="Start continuous monitoring")

    args = parser.parse_args()

    monitor = QualityMetricsMonitor(args.config)

    if args.analyze:
        logger.info("🔍 Running quality analysis")
        results = monitor.run_comprehensive_quality_analysis()

        # Generate and display report
        report = monitor.generate_quality_report(results)
        print(report)

        if args.dashboard:
            dashboard_file = monitor.generate_quality_dashboard(results)
            logger.info(f"📊 Dashboard generated: {dashboard_file}")

    else:
        logger.info("🔍 Running default quality analysis")
        results = monitor.run_comprehensive_quality_analysis()
        report = monitor.generate_quality_report(results)
        print(report)


if __name__ == "__main__":
    main()
