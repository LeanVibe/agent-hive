#!/usr/bin/env python3
"""
Observability Baseline Metrics for LeanVibe Agent Hive

Establishes baseline performance metrics and monitors system health
to track improvements and detect regressions in the agent orchestration system.
"""

import time
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import sqlite3
from statistics import mean, median, stdev
import threading
from contextlib import contextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class BaselineMetric:
    """Represents a baseline metric measurement."""
    metric_name: str
    value: float
    unit: str
    timestamp: datetime
    agent_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


@dataclass
class PerformanceBaseline:
    """Represents performance baseline measurements."""
    # Agent Coordination Metrics
    agent_coordination_success_rate: float = 0.95  # Target: 95% → 99%
    avg_task_assignment_time: float = 0.5  # Target: <500ms
    avg_task_completion_time: float = 300.0  # Target: 5 minutes

    # Development Velocity Metrics
    features_per_week: float = 7.5  # Target: 5-10 → 15-20
    bug_rate: float = 0.03  # Target: <5% → <2%
    mttr_seconds: float = 240.0  # Target: <5 minutes → <2 minutes

    # System Performance Metrics
    memory_usage_mb: float = 256.0  # Target: <500MB
    cpu_usage_percent: float = 25.0  # Target: <50%
    response_time_ms: float = 150.0  # Target: <200ms

    # Token Efficiency (to be improved)
    tokens_per_request: float = 1000.0  # Target: 70% reduction
    context_utilization: float = 0.60  # Target: optimized usage

    # Quality Metrics
    test_coverage: float = 0.85  # Target: >90%
    code_quality_score: float = 8.0  # Target: >9.0

    # Reliability Metrics
    uptime_percentage: float = 0.95  # Target: 99.9%
    error_rate: float = 0.05  # Target: <1%

    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class MetricsCollector:
    """Collects and tracks system metrics for baseline establishment."""

    def __init__(self, db_path: str = "baseline_metrics.db"):
        self.db_path = db_path
        self.metrics_history: List[BaselineMetric] = []
        self.current_baseline = PerformanceBaseline()
        self.collection_interval = 60  # seconds
        self.running = False
        self.collection_thread = None
        self._init_database()

    def _init_database(self):
        """Initialize the metrics database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS baseline_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_name TEXT NOT NULL,
                    value REAL NOT NULL,
                    unit TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    agent_id TEXT,
                    session_id TEXT,
                    metadata TEXT
                )
            ''')

            conn.execute('''
                CREATE TABLE IF NOT EXISTS performance_baselines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    baseline_data TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    version TEXT DEFAULT '1.0.0'
                )
            ''')

            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_metrics_timestamp
                ON baseline_metrics(timestamp)
            ''')

            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_metrics_name
                ON baseline_metrics(metric_name)
            ''')

    def start_collection(self):
        """Start automatic metrics collection."""
        if self.running:
            logger.warning("Metrics collection already running")
            return

        self.running = True
        self.collection_thread = threading.Thread(target=self._collection_loop)
        self.collection_thread.daemon = True
        self.collection_thread.start()
        logger.info("Metrics collection started")

    def stop_collection(self):
        """Stop automatic metrics collection."""
        self.running = False
        if self.collection_thread and self.collection_thread.is_alive():
            self.collection_thread.join(timeout=5)
        logger.info("Metrics collection stopped")

    def _collection_loop(self):
        """Main metrics collection loop."""
        while self.running:
            try:
                self._collect_system_metrics()
                time.sleep(self.collection_interval)
            except Exception as e:
                logger.error(f"Error in metrics collection: {e}")
                time.sleep(self.collection_interval)

    def _collect_system_metrics(self):
        """Collect current system metrics."""
        timestamp = datetime.now()

        # System resource metrics
        import psutil

        # Memory usage
        memory = psutil.virtual_memory()
        self.record_metric("memory_usage_mb", memory.used / (1024 * 1024), "MB", timestamp)
        self.record_metric("memory_usage_percent", memory.percent, "%", timestamp)

        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        self.record_metric("cpu_usage_percent", cpu_percent, "%", timestamp)

        # Disk usage
        disk = psutil.disk_usage('/')
        self.record_metric("disk_usage_percent", disk.percent, "%", timestamp)

        # Load average (Unix systems)
        try:
            load_avg = psutil.getloadavg()
            self.record_metric("load_average_1min", load_avg[0], "load", timestamp)
            self.record_metric("load_average_5min", load_avg[1], "load", timestamp)
            self.record_metric("load_average_15min", load_avg[2], "load", timestamp)
        except AttributeError:
            # getloadavg not available on Windows
            pass

        # Network I/O
        net_io = psutil.net_io_counters()
        self.record_metric("network_bytes_sent", net_io.bytes_sent, "bytes", timestamp)
        self.record_metric("network_bytes_recv", net_io.bytes_recv, "bytes", timestamp)

        # Process count
        self.record_metric("process_count", len(psutil.pids()), "count", timestamp)

        logger.debug(f"Collected system metrics at {timestamp}")

    def record_metric(self, metric_name: str, value: float, unit: str,
                     timestamp: datetime = None, agent_id: str = None,
                     session_id: str = None, metadata: Dict[str, Any] = None):
        """Record a single metric measurement."""
        if timestamp is None:
            timestamp = datetime.now()

        metric = BaselineMetric(
            metric_name=metric_name,
            value=value,
            unit=unit,
            timestamp=timestamp,
            agent_id=agent_id,
            session_id=session_id,
            metadata=metadata
        )

        self.metrics_history.append(metric)

        # Store in database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO baseline_metrics
                (metric_name, value, unit, timestamp, agent_id, session_id, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                metric.metric_name,
                metric.value,
                metric.unit,
                metric.timestamp.isoformat(),
                metric.agent_id,
                metric.session_id,
                json.dumps(metric.metadata) if metric.metadata else None
            ))

    def get_metric_stats(self, metric_name: str, hours: int = 24) -> Dict[str, Any]:
        """Get statistics for a specific metric over time period."""
        cutoff_time = datetime.now() - timedelta(hours=hours)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT value FROM baseline_metrics
                WHERE metric_name = ? AND timestamp > ?
                ORDER BY timestamp DESC
            ''', (metric_name, cutoff_time.isoformat()))

            values = [row[0] for row in cursor.fetchall()]

        if not values:
            return {"error": f"No data found for metric {metric_name}"}

        return {
            "metric_name": metric_name,
            "count": len(values),
            "mean": mean(values),
            "median": median(values),
            "min": min(values),
            "max": max(values),
            "std_dev": stdev(values) if len(values) > 1 else 0,
            "latest": values[0] if values else None,
            "time_period_hours": hours
        }

    def get_baseline_summary(self) -> Dict[str, Any]:
        """Get comprehensive baseline summary."""
        summary = {
            "timestamp": datetime.now().isoformat(),
            "metrics_collected": len(self.metrics_history),
            "collection_running": self.running,
            "baseline_version": "1.0.0"
        }

        # Key metrics statistics
        key_metrics = [
            "memory_usage_mb",
            "cpu_usage_percent",
            "disk_usage_percent",
            "load_average_1min",
            "process_count"
        ]

        summary["key_metrics"] = {}
        for metric in key_metrics:
            stats = self.get_metric_stats(metric)
            if "error" not in stats:
                summary["key_metrics"][metric] = stats

        # Current baseline
        summary["current_baseline"] = asdict(self.current_baseline)
        summary["current_baseline"]["timestamp"] = self.current_baseline.timestamp.isoformat()

        return summary

    def save_baseline_snapshot(self, version: str = "1.0.0"):
        """Save current baseline as a snapshot."""
        baseline_data = asdict(self.current_baseline)
        baseline_data["timestamp"] = self.current_baseline.timestamp.isoformat()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO performance_baselines (baseline_data, timestamp, version)
                VALUES (?, ?, ?)
            ''', (
                json.dumps(baseline_data),
                datetime.now().isoformat(),
                version
            ))

        logger.info(f"Baseline snapshot saved with version {version}")

    def load_baseline_snapshot(self, version: str = None) -> Optional[PerformanceBaseline]:
        """Load a baseline snapshot by version."""
        with sqlite3.connect(self.db_path) as conn:
            if version:
                cursor = conn.execute('''
                    SELECT baseline_data FROM performance_baselines
                    WHERE version = ?
                    ORDER BY timestamp DESC LIMIT 1
                ''', (version,))
            else:
                cursor = conn.execute('''
                    SELECT baseline_data FROM performance_baselines
                    ORDER BY timestamp DESC LIMIT 1
                ''')

            row = cursor.fetchone()
            if row:
                baseline_data = json.loads(row[0])
                baseline_data["timestamp"] = datetime.fromisoformat(baseline_data["timestamp"])
                return PerformanceBaseline(**baseline_data)

        return None

    def export_metrics(self, output_path: str, format: str = "json", hours: int = 24):
        """Export metrics to file."""
        cutoff_time = datetime.now() - timedelta(hours=hours)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT * FROM baseline_metrics
                WHERE timestamp > ?
                ORDER BY timestamp DESC
            ''', (cutoff_time.isoformat(),))

            metrics = []
            for row in cursor.fetchall():
                metric = {
                    "id": row[0],
                    "metric_name": row[1],
                    "value": row[2],
                    "unit": row[3],
                    "timestamp": row[4],
                    "agent_id": row[5],
                    "session_id": row[6],
                    "metadata": json.loads(row[7]) if row[7] else None
                }
                metrics.append(metric)

        if format.lower() == "json":
            with open(output_path, 'w') as f:
                json.dump({
                    "export_timestamp": datetime.now().isoformat(),
                    "time_period_hours": hours,
                    "metrics_count": len(metrics),
                    "metrics": metrics
                }, f, indent=2)
        elif format.lower() == "csv":
            import csv
            with open(output_path, 'w', newline='') as f:
                if metrics:
                    writer = csv.DictWriter(f, fieldnames=metrics[0].keys())
                    writer.writeheader()
                    writer.writerows(metrics)

        logger.info(f"Exported {len(metrics)} metrics to {output_path}")


class BaselineAnalyzer:
    """Analyzes baseline metrics to identify trends and opportunities."""

    def __init__(self, metrics_collector: MetricsCollector):
        self.collector = metrics_collector

    def analyze_trends(self, metric_name: str, hours: int = 168) -> Dict[str, Any]:
        """Analyze trends for a specific metric over time."""
        # Get hourly averages
        cutoff_time = datetime.now() - timedelta(hours=hours)

        with sqlite3.connect(self.collector.db_path) as conn:
            cursor = conn.execute('''
                SELECT
                    strftime('%Y-%m-%d %H', timestamp) as hour,
                    AVG(value) as avg_value
                FROM baseline_metrics
                WHERE metric_name = ? AND timestamp > ?
                GROUP BY hour
                ORDER BY hour
            ''', (metric_name, cutoff_time.isoformat()))

            hourly_data = cursor.fetchall()

        if len(hourly_data) < 2:
            return {"error": "Insufficient data for trend analysis"}

        values = [row[1] for row in hourly_data]
        hours_list = [row[0] for row in hourly_data]

        # Calculate trend
        n = len(values)
        x = list(range(n))
        y = values

        # Linear regression
        x_mean = mean(x)
        y_mean = mean(y)

        slope = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n)) / sum((x[i] - x_mean) ** 2 for i in range(n))
        intercept = y_mean - slope * x_mean

        # Determine trend direction
        if abs(slope) < 0.01:
            trend = "stable"
        elif slope > 0:
            trend = "increasing"
        else:
            trend = "decreasing"

        # Calculate variance
        variance = sum((y[i] - y_mean) ** 2 for i in range(n)) / n

        return {
            "metric_name": metric_name,
            "trend": trend,
            "slope": slope,
            "intercept": intercept,
            "variance": variance,
            "data_points": n,
            "time_period_hours": hours,
            "latest_value": values[-1],
            "average_value": y_mean,
            "min_value": min(values),
            "max_value": max(values)
        }

    def identify_performance_opportunities(self) -> Dict[str, Any]:
        """Identify performance improvement opportunities."""
        opportunities = []

        # Memory usage analysis
        memory_stats = self.collector.get_metric_stats("memory_usage_mb")
        if "error" not in memory_stats and memory_stats["mean"] > 400:
            opportunities.append({
                "category": "memory",
                "severity": "medium",
                "description": f"High memory usage: {memory_stats['mean']:.1f}MB average",
                "recommendation": "Optimize memory usage, implement garbage collection",
                "target": "<256MB average"
            })

        # CPU usage analysis
        cpu_stats = self.collector.get_metric_stats("cpu_usage_percent")
        if "error" not in cpu_stats and cpu_stats["mean"] > 70:
            opportunities.append({
                "category": "cpu",
                "severity": "high",
                "description": f"High CPU usage: {cpu_stats['mean']:.1f}% average",
                "recommendation": "Optimize algorithms, implement async processing",
                "target": "<50% average"
            })

        # Load average analysis (Unix systems)
        load_stats = self.collector.get_metric_stats("load_average_1min")
        if "error" not in load_stats and load_stats["mean"] > 2.0:
            opportunities.append({
                "category": "load",
                "severity": "medium",
                "description": f"High system load: {load_stats['mean']:.2f} average",
                "recommendation": "Distribute workload, optimize resource usage",
                "target": "<1.0 average"
            })

        return {
            "analysis_timestamp": datetime.now().isoformat(),
            "opportunities_count": len(opportunities),
            "opportunities": opportunities,
            "overall_health": "good" if len(opportunities) == 0 else "needs_attention"
        }

    def generate_baseline_report(self) -> Dict[str, Any]:
        """Generate comprehensive baseline report."""
        report = {
            "report_timestamp": datetime.now().isoformat(),
            "baseline_version": "1.0.0",
            "system_summary": self.collector.get_baseline_summary(),
            "performance_opportunities": self.identify_performance_opportunities()
        }

        # Key metrics trends
        key_metrics = [
            "memory_usage_mb",
            "cpu_usage_percent",
            "disk_usage_percent",
            "load_average_1min"
        ]

        report["trends"] = {}
        for metric in key_metrics:
            trend = self.analyze_trends(metric)
            if "error" not in trend:
                report["trends"][metric] = trend

        # Enhancement roadmap progress
        current_baseline = self.collector.current_baseline
        report["roadmap_progress"] = {
            "agent_coordination_success_rate": {
                "current": current_baseline.agent_coordination_success_rate,
                "target": 0.99,
                "progress": (current_baseline.agent_coordination_success_rate - 0.95) / (0.99 - 0.95) * 100
            },
            "features_per_week": {
                "current": current_baseline.features_per_week,
                "target": 17.5,  # Mid-point of 15-20
                "progress": (current_baseline.features_per_week - 7.5) / (17.5 - 7.5) * 100
            },
            "mttr_seconds": {
                "current": current_baseline.mttr_seconds,
                "target": 120.0,  # 2 minutes
                "progress": (240.0 - current_baseline.mttr_seconds) / (240.0 - 120.0) * 100
            }
        }

        return report


# Global metrics collector instance
metrics_collector = MetricsCollector()
baseline_analyzer = BaselineAnalyzer(metrics_collector)


def start_baseline_monitoring():
    """Start baseline metrics monitoring."""
    metrics_collector.start_collection()
    logger.info("Baseline monitoring started")


def stop_baseline_monitoring():
    """Stop baseline metrics monitoring."""
    metrics_collector.stop_collection()
    logger.info("Baseline monitoring stopped")


def get_baseline_report() -> Dict[str, Any]:
    """Get comprehensive baseline report."""
    return baseline_analyzer.generate_baseline_report()


def export_baseline_metrics(output_path: str, format: str = "json", hours: int = 24):
    """Export baseline metrics to file."""
    metrics_collector.export_metrics(output_path, format, hours)


if __name__ == "__main__":
    # Example usage and demonstration
    print("LeanVibe Agent Hive - Baseline Metrics System")
    print("=" * 50)

    # Start monitoring
    start_baseline_monitoring()

    # Wait for some metrics to be collected
    print("Collecting baseline metrics...")
    time.sleep(65)  # Wait for at least one collection cycle

    # Generate report
    report = get_baseline_report()
    print("\nBaseline Report:")
    print(json.dumps(report, indent=2))

    # Export metrics
    export_baseline_metrics("baseline_metrics_export.json")
    print("\nMetrics exported to baseline_metrics_export.json")

    # Stop monitoring
    stop_baseline_monitoring()

    print("\nBaseline metrics demonstration complete!")
