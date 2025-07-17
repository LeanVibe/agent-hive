#!/usr/bin/env python3
"""
Test Suite for Monitoring Core
Foundation Epic Phase 1: Micro-component testing

Comprehensive test coverage for minimal monitoring core.
Following frontend blueprint pattern: focused, compliant testing.
"""

import unittest
import os
import tempfile
from unittest.mock import patch, MagicMock
from monitoring_core import MonitoringCore, get_system_health, collect_metrics


class TestMonitoringCore(unittest.TestCase):
    """Test cases for MonitoringCore micro-component."""

    def setUp(self):
        """Set up test fixtures with temporary database."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.monitor = MonitoringCore(db_path=self.temp_db.name)

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

    def test_database_initialization(self):
        """Test database is properly initialized."""
        # Database should exist and have correct structure
        import sqlite3
        with sqlite3.connect(self.temp_db.name) as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='metrics'")
            self.assertIsNotNone(cursor.fetchone())

    def test_record_metric(self):
        """Test metric recording functionality."""
        self.monitor.record_metric("test_metric", 42.5)

        import sqlite3
        with sqlite3.connect(self.temp_db.name) as conn:
            cursor = conn.execute("SELECT metric_name, value FROM metrics WHERE metric_name='test_metric'")
            row = cursor.fetchone()

        self.assertIsNotNone(row)
        self.assertEqual(row[0], "test_metric")
        self.assertEqual(row[1], 42.5)

    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    def test_get_latest_metrics(self, mock_disk, mock_memory, mock_cpu):
        """Test latest metrics collection."""
        # Mock system metrics
        mock_cpu.return_value = 25.5
        mock_memory.return_value = MagicMock(percent=60.0, used=8589934592)  # 8GB
        mock_disk.return_value = MagicMock(percent=45.0)

        metrics = self.monitor.get_latest_metrics()

        self.assertEqual(metrics['cpu_percent'], 25.5)
        self.assertEqual(metrics['memory_percent'], 60.0)
        self.assertEqual(metrics['memory_mb'], 8192.0)  # 8GB in MB
        self.assertEqual(metrics['disk_percent'], 45.0)

    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    def test_collect_and_store(self, mock_disk, mock_memory, mock_cpu):
        """Test metric collection and storage."""
        # Mock system metrics
        mock_cpu.return_value = 30.0
        mock_memory.return_value = MagicMock(percent=50.0, used=4294967296)  # 4GB
        mock_disk.return_value = MagicMock(percent=40.0)

        metrics = self.monitor.collect_and_store()

        # Check returned metrics
        self.assertEqual(metrics['cpu_percent'], 30.0)
        self.assertEqual(metrics['memory_percent'], 50.0)

        # Check database storage
        import sqlite3
        with sqlite3.connect(self.temp_db.name) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM metrics")
            count = cursor.fetchone()[0]

        self.assertEqual(count, 4)  # 4 metrics stored

    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    def test_get_health_status_healthy(self, mock_disk, mock_memory, mock_cpu):
        """Test health status with healthy metrics."""
        # Mock healthy system metrics
        mock_cpu.return_value = 20.0
        mock_memory.return_value = MagicMock(percent=40.0, used=2147483648)  # 2GB
        mock_disk.return_value = MagicMock(percent=30.0)

        health = self.monitor.get_health_status()

        self.assertEqual(health['status'], 'healthy')
        self.assertEqual(health['health_score'], 100.0)
        self.assertIn('metrics', health)
        self.assertIn('timestamp', health)

    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    def test_get_health_status_warning(self, mock_disk, mock_memory, mock_cpu):
        """Test health status with warning metrics."""
        # Mock warning level metrics
        mock_cpu.return_value = 85.0  # High CPU
        mock_memory.return_value = MagicMock(percent=60.0, used=6442450944)  # 6GB
        mock_disk.return_value = MagicMock(percent=50.0)

        health = self.monitor.get_health_status()

        self.assertEqual(health['status'], 'warning')
        self.assertEqual(health['health_score'], 70.0)  # 100 - 30 for CPU

    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    def test_get_health_status_critical(self, mock_disk, mock_memory, mock_cpu):
        """Test health status with critical metrics."""
        # Mock critical metrics
        mock_cpu.return_value = 90.0  # High CPU
        mock_memory.return_value = MagicMock(percent=90.0, used=19327352832)  # 18GB
        mock_disk.return_value = MagicMock(percent=95.0)  # High disk

        health = self.monitor.get_health_status()

        self.assertEqual(health['status'], 'critical')
        self.assertEqual(health['health_score'], 0.0)  # 100 - 30 - 30 - 40

    def test_start_stop_monitoring(self):
        """Test monitoring start/stop functionality."""
        self.assertFalse(self.monitor.running)

        self.monitor.start_monitoring()
        self.assertTrue(self.monitor.running)

        self.monitor.stop_monitoring()
        self.assertFalse(self.monitor.running)


class TestMonitoringAPI(unittest.TestCase):
    """Test cases for monitoring API functions."""

    @patch('monitoring_core.monitoring')
    def test_get_system_health_api(self, mock_monitoring):
        """Test get_system_health API function."""
        mock_monitoring.get_health_status.return_value = {
            'status': 'healthy',
            'health_score': 95.0,
            'metrics': {'cpu_percent': 15.0},
            'timestamp': '2025-01-01T00:00:00'
        }

        health = get_system_health()

        self.assertEqual(health['status'], 'healthy')
        self.assertEqual(health['health_score'], 95.0)
        mock_monitoring.get_health_status.assert_called_once()

    @patch('monitoring_core.monitoring')
    def test_collect_metrics_api(self, mock_monitoring):
        """Test collect_metrics API function."""
        mock_monitoring.collect_and_store.return_value = {
            'cpu_percent': 25.0,
            'memory_percent': 55.0,
            'memory_mb': 5120.0,
            'disk_percent': 35.0
        }

        metrics = collect_metrics()

        self.assertEqual(metrics['cpu_percent'], 25.0)
        self.assertEqual(metrics['memory_percent'], 55.0)
        mock_monitoring.collect_and_store.assert_called_once()


if __name__ == '__main__':
    unittest.main()
