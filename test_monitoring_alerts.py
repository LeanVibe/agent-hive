#!/usr/bin/env python3
"""
Test Suite for Monitoring Alerts
Foundation Epic Phase 1: Micro-component testing

Comprehensive test coverage for alert management system.
Following compliant micro-component testing pattern.
"""

import unittest
from datetime import datetime, timedelta
from monitoring_alerts import (
    AlertManager, Alert, AlertThreshold, AlertLevel, AlertStatus,
    check_system_alerts, get_active_alerts, resolve_alert, get_alert_summary
)


class TestAlertThreshold(unittest.TestCase):
    """Test cases for AlertThreshold class."""

    def test_threshold_creation(self):
        """Test alert threshold creation."""
        threshold = AlertThreshold("cpu_percent", 80.0, 95.0, ">")

        self.assertEqual(threshold.metric_name, "cpu_percent")
        self.assertEqual(threshold.warning_value, 80.0)
        self.assertEqual(threshold.critical_value, 95.0)
        self.assertEqual(threshold.comparison, ">")

    def test_check_threshold_no_breach(self):
        """Test threshold check with no breach."""
        threshold = AlertThreshold("cpu_percent", 80.0, 95.0, ">")

        result = threshold.check_threshold(70.0)
        self.assertIsNone(result)

    def test_check_threshold_warning(self):
        """Test threshold check triggering warning."""
        threshold = AlertThreshold("cpu_percent", 80.0, 95.0, ">")

        result = threshold.check_threshold(85.0)
        self.assertEqual(result, AlertLevel.WARNING)

    def test_check_threshold_critical(self):
        """Test threshold check triggering critical."""
        threshold = AlertThreshold("cpu_percent", 80.0, 95.0, ">")

        result = threshold.check_threshold(96.0)
        self.assertEqual(result, AlertLevel.CRITICAL)

    def test_check_threshold_less_than(self):
        """Test threshold with less-than comparison."""
        threshold = AlertThreshold("health_score", 50.0, 30.0, "<")

        # No breach
        result = threshold.check_threshold(60.0)
        self.assertIsNone(result)

        # Warning
        result = threshold.check_threshold(45.0)
        self.assertEqual(result, AlertLevel.WARNING)

        # Critical
        result = threshold.check_threshold(25.0)
        self.assertEqual(result, AlertLevel.CRITICAL)


class TestAlert(unittest.TestCase):
    """Test cases for Alert class."""

    def test_alert_creation(self):
        """Test alert creation."""
        timestamp = datetime.now()
        alert = Alert(
            alert_id="test_alert_001",
            level=AlertLevel.WARNING,
            message="Test alert message",
            source="test_source",
            timestamp=timestamp
        )

        self.assertEqual(alert.alert_id, "test_alert_001")
        self.assertEqual(alert.level, AlertLevel.WARNING)
        self.assertEqual(alert.message, "Test alert message")
        self.assertEqual(alert.source, "test_source")
        self.assertEqual(alert.timestamp, timestamp)
        self.assertEqual(alert.status, AlertStatus.ACTIVE)
        self.assertIsNone(alert.resolved_at)

    def test_alert_to_dict(self):
        """Test alert serialization to dictionary."""
        timestamp = datetime.now()
        alert = Alert(
            alert_id="test_alert_001",
            level=AlertLevel.CRITICAL,
            message="Critical test alert",
            source="test_source",
            timestamp=timestamp,
            metadata={"test": "data"}
        )

        alert_dict = alert.to_dict()

        self.assertEqual(alert_dict['alert_id'], "test_alert_001")
        self.assertEqual(alert_dict['level'], "critical")
        self.assertEqual(alert_dict['message'], "Critical test alert")
        self.assertEqual(alert_dict['source'], "test_source")
        self.assertEqual(alert_dict['status'], "active")
        self.assertEqual(alert_dict['metadata'], {"test": "data"})
        self.assertIn('timestamp', alert_dict)


class TestAlertManager(unittest.TestCase):
    """Test cases for AlertManager class."""

    def setUp(self):
        """Set up test fixtures."""
        self.manager = AlertManager()

    def test_default_thresholds(self):
        """Test default thresholds are set up."""
        self.assertIn("cpu_percent", self.manager.thresholds)
        self.assertIn("memory_percent", self.manager.thresholds)
        self.assertIn("disk_percent", self.manager.thresholds)
        self.assertIn("health_score", self.manager.thresholds)

        cpu_threshold = self.manager.thresholds["cpu_percent"]
        self.assertEqual(cpu_threshold.warning_value, 80.0)
        self.assertEqual(cpu_threshold.critical_value, 95.0)

    def test_add_threshold(self):
        """Test adding custom threshold."""
        self.manager.add_threshold("custom_metric", 50.0, 80.0, ">")

        self.assertIn("custom_metric", self.manager.thresholds)
        threshold = self.manager.thresholds["custom_metric"]
        self.assertEqual(threshold.warning_value, 50.0)
        self.assertEqual(threshold.critical_value, 80.0)

    def test_check_metrics_no_alerts(self):
        """Test checking metrics with no alerts triggered."""
        metrics = {
            "cpu_percent": 50.0,
            "memory_percent": 60.0,
            "disk_percent": 70.0,
            "health_score": 80.0
        }

        alerts = self.manager.check_metrics(metrics)

        self.assertEqual(len(alerts), 0)
        self.assertEqual(len(self.manager.active_alerts), 0)

    def test_check_metrics_with_alerts(self):
        """Test checking metrics that trigger alerts."""
        metrics = {
            "cpu_percent": 85.0,  # Warning
            "memory_percent": 96.0,  # Critical
            "disk_percent": 70.0,  # No alert
            "health_score": 25.0  # Critical
        }

        alerts = self.manager.check_metrics(metrics)

        self.assertEqual(len(alerts), 3)
        self.assertEqual(len(self.manager.active_alerts), 3)

        # Check alert levels
        alert_levels = [alert.level for alert in alerts]
        self.assertIn(AlertLevel.WARNING, alert_levels)
        self.assertEqual(alert_levels.count(AlertLevel.CRITICAL), 2)

    def test_resolve_alert(self):
        """Test resolving an alert."""
        # Create an alert first
        metrics = {"cpu_percent": 85.0}
        alerts = self.manager.check_metrics(metrics)
        self.assertEqual(len(alerts), 1)

        alert_id = alerts[0].alert_id

        # Resolve the alert
        success = self.manager.resolve_alert(alert_id)

        self.assertTrue(success)
        self.assertEqual(len(self.manager.active_alerts), 0)
        # Should be in history
        self.assertGreater(len(self.manager.alert_history), 0)

    def test_resolve_nonexistent_alert(self):
        """Test resolving a non-existent alert."""
        success = self.manager.resolve_alert("nonexistent_alert")

        self.assertFalse(success)

    def test_acknowledge_alert(self):
        """Test acknowledging an alert."""
        # Create an alert first
        metrics = {"cpu_percent": 85.0}
        alerts = self.manager.check_metrics(metrics)
        alert_id = alerts[0].alert_id

        # Acknowledge the alert
        success = self.manager.acknowledge_alert(alert_id)

        self.assertTrue(success)
        self.assertEqual(self.manager.active_alerts[alert_id].status, AlertStatus.ACKNOWLEDGED)
        # Should still be in active alerts
        self.assertEqual(len(self.manager.active_alerts), 1)

    def test_get_active_alerts_filtered(self):
        """Test getting active alerts filtered by level."""
        metrics = {
            "cpu_percent": 85.0,  # Warning
            "memory_percent": 96.0,  # Critical
            "health_score": 25.0  # Critical
        }

        self.manager.check_metrics(metrics)

        # Get all alerts
        all_alerts = self.manager.get_active_alerts()
        self.assertEqual(len(all_alerts), 3)

        # Get only critical alerts
        critical_alerts = self.manager.get_active_alerts(AlertLevel.CRITICAL)
        self.assertEqual(len(critical_alerts), 2)

        # Get only warning alerts
        warning_alerts = self.manager.get_active_alerts(AlertLevel.WARNING)
        self.assertEqual(len(warning_alerts), 1)

    def test_get_alert_summary(self):
        """Test getting alert summary."""
        metrics = {
            "cpu_percent": 85.0,  # Warning
            "memory_percent": 96.0,  # Critical
            "health_score": 25.0  # Critical
        }

        self.manager.check_metrics(metrics)
        summary = self.manager.get_alert_summary()

        self.assertEqual(summary['active_alerts_total'], 3)
        self.assertEqual(summary['active_by_level']['warning'], 1)
        self.assertEqual(summary['active_by_level']['critical'], 2)
        self.assertEqual(summary['active_by_level']['info'], 0)
        self.assertEqual(summary['active_by_level']['error'], 0)
        self.assertIn('timestamp', summary)

    def test_clear_resolved_alerts(self):
        """Test clearing old resolved alerts."""
        # Create and resolve an alert
        metrics = {"cpu_percent": 85.0}
        alerts = self.manager.check_metrics(metrics)
        alert_id = alerts[0].alert_id

        # Manually set resolved time to be old
        self.manager.resolve_alert(alert_id)
        old_alert = next(a for a in self.manager.alert_history if a.alert_id == alert_id)
        old_alert.resolved_at = datetime.now() - timedelta(hours=25)

        # Clear old alerts
        self.manager.clear_resolved_alerts(24)

        # Should be removed from history
        remaining_alerts = [a for a in self.manager.alert_history if a.alert_id == alert_id]
        self.assertEqual(len(remaining_alerts), 0)


class TestAlertAPI(unittest.TestCase):
    """Test cases for alert API functions."""

    def setUp(self):
        """Set up fresh alert manager for each test."""
        # Reset global alert manager
        from monitoring_alerts import alert_manager
        alert_manager.active_alerts.clear()
        alert_manager.alert_history.clear()

    def test_check_system_alerts_api(self):
        """Test check_system_alerts API function."""
        metrics = {
            "cpu_percent": 85.0,
            "memory_percent": 50.0
        }

        alerts = check_system_alerts(metrics)

        self.assertIsInstance(alerts, list)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]['level'], 'warning')

    def test_get_active_alerts_api(self):
        """Test get_active_alerts API function."""
        # Create some alerts first
        metrics = {"cpu_percent": 96.0, "memory_percent": 96.0}
        check_system_alerts(metrics)

        # Get all active alerts
        alerts = get_active_alerts()
        self.assertGreater(len(alerts), 0)

        # Get only critical alerts
        critical_alerts = get_active_alerts("critical")
        self.assertEqual(len(critical_alerts), 2)

    def test_resolve_alert_api(self):
        """Test resolve_alert API function."""
        # Create an alert first
        metrics = {"cpu_percent": 85.0}
        alerts = check_system_alerts(metrics)

        # Should have at least one alert
        self.assertGreater(len(alerts), 0)
        alert_id = alerts[0]['alert_id']

        # Resolve via API
        success = resolve_alert(alert_id)

        self.assertTrue(success)

    def test_get_alert_summary_api(self):
        """Test get_alert_summary API function."""
        summary = get_alert_summary()

        self.assertIn('active_alerts_total', summary)
        self.assertIn('active_by_level', summary)
        self.assertIn('timestamp', summary)


if __name__ == '__main__':
    unittest.main()
