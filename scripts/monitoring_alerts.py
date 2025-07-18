#!/usr/bin/env python3
"""
Monitoring Alerts - Micro-component for alerting system
Foundation Epic Phase 1: Alert management and notification

Focused alert system with threshold management and notification handling.
Compliant micro-component: <300 lines alert functionality.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """Alert status states."""
    ACTIVE = "active"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"


@dataclass
class Alert:
    """Alert data structure."""
    alert_id: str
    level: AlertLevel
    message: str
    source: str
    timestamp: datetime
    status: AlertStatus = AlertStatus.ACTIVE
    resolved_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary."""
        data = asdict(self)
        data['level'] = self.level.value
        data['status'] = self.status.value
        data['timestamp'] = self.timestamp.isoformat()
        if self.resolved_at:
            data['resolved_at'] = self.resolved_at.isoformat()
        return data


class AlertThreshold:
    """Alert threshold configuration."""

    def __init__(self, metric_name: str, warning_value: float,
                 critical_value: float, comparison: str = ">"):
        self.metric_name = metric_name
        self.warning_value = warning_value
        self.critical_value = critical_value
        self.comparison = comparison  # >, <, >=, <=, ==, !=

    def check_threshold(self, value: float) -> Optional[AlertLevel]:
        """Check if value breaches threshold."""
        if self._compare(value, self.critical_value):
            return AlertLevel.CRITICAL
        elif self._compare(value, self.warning_value):
            return AlertLevel.WARNING
        return None

    def _compare(self, value: float, threshold: float) -> bool:
        """Compare value against threshold."""
        if self.comparison == ">":
            return value > threshold
        elif self.comparison == "<":
            return value < threshold
        elif self.comparison == ">=":
            return value >= threshold
        elif self.comparison == "<=":
            return value <= threshold
        elif self.comparison == "==":
            return value == threshold
        elif self.comparison == "!=":
            return value != threshold
        return False


class AlertManager:
    """Alert management system."""

    def __init__(self):
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.thresholds: Dict[str, AlertThreshold] = {}
        self.max_history = 1000
        self._setup_default_thresholds()

    def _setup_default_thresholds(self):
        """Setup default alert thresholds."""
        self.thresholds = {
            "cpu_percent": AlertThreshold("cpu_percent", 80.0, 95.0, ">"),
            "memory_percent": AlertThreshold("memory_percent", 85.0, 95.0, ">"),
            "disk_percent": AlertThreshold("disk_percent", 90.0, 98.0, ">"),
            "health_score": AlertThreshold("health_score", 50.0, 30.0, "<")
        }

    def add_threshold(self, metric_name: str, warning_value: float,
                     critical_value: float, comparison: str = ">"):
        """Add or update alert threshold."""
        self.thresholds[metric_name] = AlertThreshold(
            metric_name, warning_value, critical_value, comparison
        )

    def check_metrics(self, metrics: Dict[str, float]) -> List[Alert]:
        """Check metrics against thresholds and generate alerts."""
        new_alerts = []

        for metric_name, value in metrics.items():
            if metric_name in self.thresholds:
                threshold = self.thresholds[metric_name]
                level = threshold.check_threshold(value)

                if level:
                    alert_id = f"{metric_name}_{level.value}_{int(datetime.now().timestamp())}"
                    alert = Alert(
                        alert_id=alert_id,
                        level=level,
                        message=f"{metric_name} {threshold.comparison} {threshold.warning_value if level == AlertLevel.WARNING else threshold.critical_value} (current: {value})",
                        source="monitoring_alerts",
                        timestamp=datetime.now(),
                        metadata={"metric": metric_name, "value": value, "threshold": threshold.warning_value if level == AlertLevel.WARNING else threshold.critical_value}
                    )

                    # Check if similar alert already exists
                    existing_key = f"{metric_name}_{level.value}"
                    if not any(existing_key in aid for aid in self.active_alerts.keys()):
                        self.active_alerts[alert_id] = alert
                        new_alerts.append(alert)
                        self._add_to_history(alert)

        return new_alerts

    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an active alert."""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = datetime.now()
            del self.active_alerts[alert_id]
            self._add_to_history(alert)
            return True
        return False

    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an active alert."""
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id].status = AlertStatus.ACKNOWLEDGED
            return True
        return False

    def get_active_alerts(self, level: Optional[AlertLevel] = None) -> List[Alert]:
        """Get active alerts, optionally filtered by level."""
        alerts = list(self.active_alerts.values())
        if level:
            alerts = [a for a in alerts if a.level == level]
        return sorted(alerts, key=lambda x: x.timestamp, reverse=True)

    def get_alert_summary(self) -> Dict[str, Any]:
        """Get alert summary statistics."""
        active_by_level = {}
        for level in AlertLevel:
            active_by_level[level.value] = len([a for a in self.active_alerts.values() if a.level == level])

        return {
            "active_alerts_total": len(self.active_alerts),
            "active_by_level": active_by_level,
            "history_count": len(self.alert_history),
            "thresholds_configured": len(self.thresholds),
            "timestamp": datetime.now().isoformat()
        }

    def _add_to_history(self, alert: Alert):
        """Add alert to history with size management."""
        self.alert_history.append(alert)
        while len(self.alert_history) > self.max_history:
            self.alert_history.pop(0)

    def clear_resolved_alerts(self, older_than_hours: int = 24):
        """Clear resolved alerts older than specified hours."""
        cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
        self.alert_history = [
            alert for alert in self.alert_history
            if not (alert.status == AlertStatus.RESOLVED and
                   alert.resolved_at and alert.resolved_at < cutoff_time)
        ]


# Global alert manager instance
alert_manager = AlertManager()


def check_system_alerts(metrics: Dict[str, float]) -> List[Dict[str, Any]]:
    """API function to check system metrics for alerts."""
    alerts = alert_manager.check_metrics(metrics)
    return [alert.to_dict() for alert in alerts]


def get_active_alerts(level: str = None) -> List[Dict[str, Any]]:
    """API function to get active alerts."""
    alert_level = AlertLevel(level) if level else None
    alerts = alert_manager.get_active_alerts(alert_level)
    return [alert.to_dict() for alert in alerts]


def resolve_alert(alert_id: str) -> bool:
    """API function to resolve an alert."""
    return alert_manager.resolve_alert(alert_id)


def get_alert_summary() -> Dict[str, Any]:
    """API function to get alert summary."""
    return alert_manager.get_alert_summary()


if __name__ == "__main__":
    print("Monitoring Alerts - Micro Component Test")
    print("=" * 45)

    # Test alert system
    test_metrics = {
        "cpu_percent": 85.0,  # Should trigger warning
        "memory_percent": 96.0,  # Should trigger critical
        "disk_percent": 45.0,  # Should be fine
        "health_score": 25.0  # Should trigger critical
    }

    # Check for alerts
    new_alerts = check_system_alerts(test_metrics)
    print(f"Generated {len(new_alerts)} alerts")

    for alert in new_alerts:
        print(f"- {alert['level'].upper()}: {alert['message']}")

    # Get summary
    summary = get_alert_summary()
    print(f"\nAlert Summary:")
    print(f"Active Alerts: {summary['active_alerts_total']}")
    print(f"Critical: {summary['active_by_level']['critical']}")
    print(f"Warning: {summary['active_by_level']['warning']}")

    print("\nMonitoring alerts test complete!")
