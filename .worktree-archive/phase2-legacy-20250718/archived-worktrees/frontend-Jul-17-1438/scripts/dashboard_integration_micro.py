#!/usr/bin/env python3
"""
Dashboard Integration Micro-Component - XP Methodology Enforcement
Part of PM/XP Methodology Enforcer (Micro-Component #3)

This micro-component handles ONLY integration with enhanced dashboard.
Follows XP Small Releases principle: ≤400 lines, single responsibility.
"""

import requests
import sqlite3
from datetime import datetime
from typing import Dict, List
from dataclasses import dataclass


@dataclass
class DashboardMetric:
    """Minimal dashboard metric for micro-component."""
    metric_id: str
    metric_type: str  # 'pr_size', 'xp_compliance', 'velocity', 'quality'
    value: float
    status: str  # 'compliant', 'warning', 'violation'
    timestamp: str


class DashboardIntegrationMicro:
    """Micro-component for enhanced dashboard integration only."""

    def __init__(self, dashboard_url: str = "http://localhost:8002",
                 db_path: str = "dashboard_micro.db"):
        self.dashboard_url = dashboard_url
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize minimal database for dashboard integration."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS dashboard_metrics (
                    metric_id TEXT PRIMARY KEY,
                    metric_type TEXT NOT NULL,
                    value REAL NOT NULL,
                    status TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    sent_to_dashboard BOOLEAN DEFAULT FALSE
                )
            """)
            conn.commit()

    def push_xp_compliance_metric(self, compliance_score: float) -> bool:
        """Push XP compliance metric to dashboard - core functionality."""
        metric = DashboardMetric(
            metric_id=f"xp-compliance-{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            metric_type="xp_compliance",
            value=compliance_score,
            status=self._get_compliance_status(compliance_score),
            timestamp=datetime.now().isoformat()
        )

        # Save locally first
        self.save_metric(metric)

        # Try to push to dashboard
        return self._push_to_dashboard(metric)

    def push_pr_size_metric(self, pr_number: int, line_count: int) -> bool:
        """Push PR size metric to dashboard - core functionality."""
        metric = DashboardMetric(
            metric_id=f"pr-size-{pr_number}-{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            metric_type="pr_size",
            value=float(line_count),
            status=self._get_pr_size_status(line_count),
            timestamp=datetime.now().isoformat()
        )

        self.save_metric(metric)
        return self._push_to_dashboard(metric)

    def push_velocity_metric(self, velocity: float) -> bool:
        """Push velocity metric to dashboard - core functionality."""
        metric = DashboardMetric(
            metric_id=f"velocity-{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            metric_type="velocity",
            value=velocity,
            status=self._get_velocity_status(velocity),
            timestamp=datetime.now().isoformat()
        )

        self.save_metric(metric)
        return self._push_to_dashboard(metric)

    def get_dashboard_status(self) -> Dict:
        """Get dashboard connection status - core functionality."""
        try:
            response = requests.get(f"{self.dashboard_url}/api/health", timeout=5)
            if response.status_code == 200:
                return {
                    "status": "connected",
                    "dashboard_url": self.dashboard_url,
                    "response_time_ms": response.elapsed.total_seconds() * 1000
                }
        except Exception:
            pass

        return {
            "status": "disconnected",
            "dashboard_url": self.dashboard_url,
            "error": "Dashboard not available"
        }

    def get_recent_metrics(self, limit: int = 10) -> List[DashboardMetric]:
        """Get recent metrics - core functionality."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT metric_id, metric_type, value, status, timestamp
                FROM dashboard_metrics
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))

            return [DashboardMetric(*row) for row in cursor.fetchall()]

    def retry_failed_pushes(self) -> int:
        """Retry pushing failed metrics to dashboard."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT metric_id, metric_type, value, status, timestamp
                FROM dashboard_metrics
                WHERE sent_to_dashboard = FALSE
                ORDER BY timestamp ASC
                LIMIT 50
            """)

            failed_metrics = [DashboardMetric(*row) for row in cursor.fetchall()]
            successful_pushes = 0

            for metric in failed_metrics:
                if self._push_to_dashboard(metric):
                    successful_pushes += 1

            return successful_pushes

    def save_metric(self, metric: DashboardMetric):
        """Save metric to local database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO dashboard_metrics
                (metric_id, metric_type, value, status, timestamp, sent_to_dashboard)
                VALUES (?, ?, ?, ?, ?, FALSE)
            """, (
                metric.metric_id, metric.metric_type, metric.value,
                metric.status, metric.timestamp
            ))
            conn.commit()

    def _push_to_dashboard(self, metric: DashboardMetric) -> bool:
        """Push single metric to dashboard API."""
        try:
            payload = {
                "metric_id": metric.metric_id,
                "type": metric.metric_type,
                "value": metric.value,
                "status": metric.status,
                "timestamp": metric.timestamp,
                "source": "pm_xp_enforcer"
            }

            response = requests.post(
                f"{self.dashboard_url}/api/metrics",
                json=payload,
                timeout=10
            )

            if response.status_code in [200, 201]:
                self._mark_as_sent(metric.metric_id)
                return True

        except Exception:
            # Fail silently - metric saved locally for retry
            pass

        return False

    def _mark_as_sent(self, metric_id: str):
        """Mark metric as successfully sent to dashboard."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE dashboard_metrics
                SET sent_to_dashboard = TRUE
                WHERE metric_id = ?
            """, (metric_id,))
            conn.commit()

    def _get_compliance_status(self, score: float) -> str:
        """Get XP compliance status based on score."""
        if score >= 80:
            return "compliant"
        elif score >= 60:
            return "warning"
        else:
            return "violation"

    def _get_pr_size_status(self, line_count: int) -> str:
        """Get PR size status based on XP limits."""
        if line_count <= 500:
            return "compliant"
        elif line_count <= 1000:
            return "warning"
        else:
            return "violation"

    def _get_velocity_status(self, velocity: float) -> str:
        """Get velocity status based on targets."""
        if velocity >= 8.0:
            return "compliant"
        elif velocity >= 5.0:
            return "warning"
        else:
            return "violation"


def main():
    """CLI interface for dashboard integration micro-component."""
    import sys

    if len(sys.argv) < 2:
        print("Dashboard Integration Micro-Component")
        print("Commands:")
        print("  status                           - Check dashboard connection")
        print("  push-xp <score>                  - Push XP compliance metric")
        print("  push-pr <pr_number> <lines>      - Push PR size metric")
        print("  push-velocity <velocity>         - Push velocity metric")
        print("  metrics [limit]                  - Show recent metrics")
        print("  retry                            - Retry failed pushes")
        return

    dashboard = DashboardIntegrationMicro()
    command = sys.argv[1]

    if command == "status":
        status = dashboard.get_dashboard_status()
        print(f"Dashboard Status: {status['status']}")
        print(f"URL: {status['dashboard_url']}")
        if status['status'] == 'connected':
            print(f"Response Time: {status['response_time_ms']:.1f}ms")
        elif 'error' in status:
            print(f"Error: {status['error']}")

    elif command == "push-xp":
        if len(sys.argv) < 3:
            print("Usage: push-xp <score>")
            return

        score = float(sys.argv[2])
        success = dashboard.push_xp_compliance_metric(score)
        print(f"{'✅' if success else '❌'} XP compliance metric: {score}%")

    elif command == "push-pr":
        if len(sys.argv) < 4:
            print("Usage: push-pr <pr_number> <lines>")
            return

        pr_number = int(sys.argv[2])
        lines = int(sys.argv[3])
        success = dashboard.push_pr_size_metric(pr_number, lines)
        print(f"{'✅' if success else '❌'} PR size metric: PR #{pr_number} ({lines} lines)")

    elif command == "push-velocity":
        if len(sys.argv) < 3:
            print("Usage: push-velocity <velocity>")
            return

        velocity = float(sys.argv[2])
        success = dashboard.push_velocity_metric(velocity)
        print(f"{'✅' if success else '❌'} Velocity metric: {velocity} points/person")

    elif command == "metrics":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        metrics = dashboard.get_recent_metrics(limit)

        print(f"Recent Dashboard Metrics (last {limit}):")
        for metric in metrics:
            print(f"  {metric.metric_type}: {metric.value} [{metric.status}] - {metric.timestamp}")

    elif command == "retry":
        pushed = dashboard.retry_failed_pushes()
        print(f"✅ Retried failed pushes: {pushed} metrics sent")

    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
