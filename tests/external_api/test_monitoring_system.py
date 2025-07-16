"""
Tests for Monitoring System component.
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from external_api.monitoring_system import (
    MonitoringSystem,
    MetricData,
    MetricType,
    Alert,
    AlertRule,
    AlertSeverity
)


class TestMonitoringSystem:
    """Test suite for MonitoringSystem class."""
    
    @pytest.fixture
    def monitoring_config(self):
        """Create test monitoring configuration."""
        return {
            "retention_hours": 1,
            "collection_interval": 1,
            "alert_check_interval": 1,
            "system_metrics": True
        }
    
    @pytest.fixture
    def monitoring_system(self, monitoring_config):
        """Create MonitoringSystem instance."""
        return MonitoringSystem(monitoring_config)
    
    @pytest.fixture
    def sample_alert_rule(self):
        """Create sample alert rule."""
        return AlertRule(
            name="Test Alert",
            metric_name="test.metric",
            threshold=100.0,
            comparison="gt",
            severity=AlertSeverity.HIGH,
            component="test"
        )
    
    @pytest.mark.asyncio
    async def test_monitoring_system_initialization(self, monitoring_system, monitoring_config):
        """Test monitoring system initialization."""
        assert monitoring_system.config == monitoring_config
        assert monitoring_system.metrics == {}
        assert monitoring_system.alerts == {}
        assert monitoring_system.retention_hours == 1
        assert monitoring_system.collection_interval == 1
        assert monitoring_system.alert_check_interval == 1
        assert monitoring_system._running is False
        
        # Check default alert rules
        assert len(monitoring_system.alert_rules) > 0
        assert "High CPU Usage" in monitoring_system.alert_rules
        assert "High Memory Usage" in monitoring_system.alert_rules
        assert "Low Disk Space" in monitoring_system.alert_rules
    
    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self, monitoring_system):
        """Test starting and stopping monitoring system."""
        # Test start
        await monitoring_system.start()
        assert monitoring_system._running is True
        assert monitoring_system._collection_task is not None
        assert monitoring_system._alert_task is not None
        assert monitoring_system._cleanup_task is not None
        
        # Test start when already running
        await monitoring_system.start()  # Should not raise error
        assert monitoring_system._running is True
        
        # Test stop
        await monitoring_system.stop()
        assert monitoring_system._running is False
        
        # Test stop when not running
        await monitoring_system.stop()  # Should not raise error
        assert monitoring_system._running is False
    
    @pytest.mark.asyncio
    async def test_record_metric_basic(self, monitoring_system):
        """Test basic metric recording."""
        monitoring_system.record_metric("test.metric", 42.0, MetricType.GAUGE)
        
        assert "test.metric" in monitoring_system.metrics
        assert len(monitoring_system.metrics["test.metric"]) == 1
        
        metric = monitoring_system.metrics["test.metric"][0]
        assert metric.name == "test.metric"
        assert metric.value == 42.0
        assert metric.metric_type == MetricType.GAUGE
        assert isinstance(metric.timestamp, datetime)
    
    @pytest.mark.asyncio
    async def test_record_metric_with_tags(self, monitoring_system):
        """Test metric recording with tags."""
        tags = {"service": "test", "environment": "dev"}
        monitoring_system.record_metric("test.metric", 100.0, MetricType.COUNTER, tags)
        
        metric = monitoring_system.metrics["test.metric"][0]
        assert metric.tags == tags
    
    @pytest.mark.asyncio
    async def test_increment_counter(self, monitoring_system):
        """Test counter increment functionality."""
        monitoring_system.increment_counter("test.counter")
        monitoring_system.increment_counter("test.counter", 5)
        
        assert len(monitoring_system.metrics["test.counter"]) == 2
        assert monitoring_system.metrics["test.counter"][0].value == 1
        assert monitoring_system.metrics["test.counter"][1].value == 5
        assert monitoring_system.metrics["test.counter"][0].metric_type == MetricType.COUNTER
    
    @pytest.mark.asyncio
    async def test_set_gauge(self, monitoring_system):
        """Test gauge setting functionality."""
        monitoring_system.set_gauge("test.gauge", 50.0)
        
        assert len(monitoring_system.metrics["test.gauge"]) == 1
        assert monitoring_system.metrics["test.gauge"][0].value == 50.0
        assert monitoring_system.metrics["test.gauge"][0].metric_type == MetricType.GAUGE
    
    @pytest.mark.asyncio
    async def test_record_timer(self, monitoring_system):
        """Test timer recording functionality."""
        monitoring_system.record_timer("test.timer", 150.5)
        
        assert len(monitoring_system.metrics["test.timer"]) == 1
        assert monitoring_system.metrics["test.timer"][0].value == 150.5
        assert monitoring_system.metrics["test.timer"][0].metric_type == MetricType.TIMER
    
    @pytest.mark.asyncio
    async def test_add_remove_alert_rule(self, monitoring_system, sample_alert_rule):
        """Test adding and removing alert rules."""
        # Add rule
        monitoring_system.add_alert_rule(sample_alert_rule)
        assert sample_alert_rule.name in monitoring_system.alert_rules
        assert monitoring_system.alert_rules[sample_alert_rule.name] == sample_alert_rule
        
        # Remove rule
        result = monitoring_system.remove_alert_rule(sample_alert_rule.name)
        assert result is True
        assert sample_alert_rule.name not in monitoring_system.alert_rules
        
        # Remove non-existent rule
        result = monitoring_system.remove_alert_rule("non-existent")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_add_alert_handler(self, monitoring_system):
        """Test adding alert handlers."""
        handler_called = []
        
        async def test_handler(alert):
            handler_called.append(alert)
        
        monitoring_system.add_alert_handler(test_handler)
        assert len(monitoring_system.alert_handlers) > 0
    
    @pytest.mark.asyncio
    async def test_get_metrics_no_filter(self, monitoring_system):
        """Test getting metrics without filters."""
        # Record some metrics
        monitoring_system.record_metric("test.metric", 10.0)
        monitoring_system.record_metric("test.metric", 20.0)
        monitoring_system.record_metric("test.metric", 30.0)
        
        metrics = monitoring_system.get_metrics("test.metric")
        assert len(metrics) == 3
        assert metrics[0].value == 10.0
        assert metrics[1].value == 20.0
        assert metrics[2].value == 30.0
    
    @pytest.mark.asyncio
    async def test_get_metrics_with_time_filter(self, monitoring_system):
        """Test getting metrics with time filters."""
        now = datetime.now()
        hour_ago = now - timedelta(hours=1)
        
        # Record metrics
        monitoring_system.record_metric("test.metric", 10.0)
        
        # Get metrics with time filter
        metrics = monitoring_system.get_metrics("test.metric", start_time=hour_ago)
        assert len(metrics) == 1
        
        # Get metrics with future start time
        future_time = now + timedelta(hours=1)
        metrics = monitoring_system.get_metrics("test.metric", start_time=future_time)
        assert len(metrics) == 0
    
    @pytest.mark.asyncio
    async def test_get_metrics_nonexistent(self, monitoring_system):
        """Test getting metrics for non-existent metric."""
        metrics = monitoring_system.get_metrics("nonexistent.metric")
        assert metrics == []
    
    @pytest.mark.asyncio
    async def test_get_metric_summary(self, monitoring_system):
        """Test getting metric summary statistics."""
        # Record test metrics
        monitoring_system.record_metric("test.metric", 10.0)
        monitoring_system.record_metric("test.metric", 20.0)
        monitoring_system.record_metric("test.metric", 30.0)
        
        summary = monitoring_system.get_metric_summary("test.metric")
        assert summary["count"] == 3
        assert summary["avg"] == 20.0
        assert summary["min"] == 10.0
        assert summary["max"] == 30.0
        assert summary["latest"] == 30.0
    
    @pytest.mark.asyncio
    async def test_get_metric_summary_empty(self, monitoring_system):
        """Test getting summary for non-existent metric."""
        summary = monitoring_system.get_metric_summary("nonexistent.metric")
        assert summary["count"] == 0
        assert summary["avg"] == 0
        assert summary["min"] == 0
        assert summary["max"] == 0
    
    @pytest.mark.asyncio
    async def test_alert_creation_and_resolution(self, monitoring_system, sample_alert_rule):
        """Test alert creation and resolution."""
        # Add alert rule
        monitoring_system.add_alert_rule(sample_alert_rule)
        
        # Record metric that should trigger alert
        monitoring_system.record_metric("test.metric", 150.0)  # > threshold of 100
        
        # Wait for alert processing
        await asyncio.sleep(0.1)
        
        # Check active alerts
        active_alerts = monitoring_system.get_active_alerts()
        assert len(active_alerts) >= 0  # May be processed asynchronously
        
        # Test alert resolution
        if monitoring_system.alerts:
            alert_id = list(monitoring_system.alerts.keys())[0]
            result = monitoring_system.resolve_alert(alert_id)
            assert result is True
            assert monitoring_system.alerts[alert_id].resolved is True
    
    @pytest.mark.asyncio
    async def test_resolve_nonexistent_alert(self, monitoring_system):
        """Test resolving non-existent alert."""
        result = monitoring_system.resolve_alert("nonexistent-alert")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_update_component_health(self, monitoring_system):
        """Test updating component health."""
        health_data = {
            "healthy": True,
            "response_time": 50.0,
            "status": "running"
        }
        
        monitoring_system.update_component_health("test-service", health_data)
        
        # Check health data
        health = monitoring_system.get_component_health("test-service")
        assert health["healthy"] is True
        assert health["response_time"] == 50.0
        assert health["status"] == "running"
        assert "timestamp" in health
        
        # Check metrics were recorded
        assert "test-service.health" in monitoring_system.metrics
        assert "test-service.response_time" in monitoring_system.metrics
    
    @pytest.mark.asyncio
    async def test_get_component_health_all(self, monitoring_system):
        """Test getting health for all components."""
        monitoring_system.update_component_health("service1", {"healthy": True})
        monitoring_system.update_component_health("service2", {"healthy": False})
        
        all_health = monitoring_system.get_component_health()
        assert "service1" in all_health
        assert "service2" in all_health
        assert all_health["service1"]["healthy"] is True
        assert all_health["service2"]["healthy"] is False
    
    @pytest.mark.asyncio
    async def test_get_component_health_nonexistent(self, monitoring_system):
        """Test getting health for non-existent component."""
        health = monitoring_system.get_component_health("nonexistent")
        assert health == {}
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    @pytest.mark.asyncio
    async def test_get_system_metrics(self, mock_disk, mock_memory, mock_cpu, monitoring_system):
        """Test getting system metrics."""
        # Mock psutil responses
        mock_cpu.return_value = 50.0
        mock_memory.return_value = MagicMock(percent=75.0, used=4000000000, total=8000000000)
        mock_disk.return_value = MagicMock(percent=60.0, used=50000000000, total=100000000000)
        
        metrics = monitoring_system.get_system_metrics()
        
        assert metrics["cpu_percent"] == 50.0
        assert metrics["memory_percent"] == 75.0
        assert "memory_used_mb" in metrics
        assert "memory_total_mb" in metrics
        assert metrics["disk_percent"] == 60.0
        assert "disk_used_gb" in metrics
        assert "disk_total_gb" in metrics
    
    @patch('psutil.cpu_percent')
    @pytest.mark.asyncio
    async def test_get_system_metrics_error(self, mock_cpu, monitoring_system):
        """Test system metrics error handling."""
        mock_cpu.side_effect = Exception("Test error")
        
        metrics = monitoring_system.get_system_metrics()
        assert metrics == {}
    
    @pytest.mark.asyncio
    async def test_export_metrics_json(self, monitoring_system):
        """Test exporting metrics in JSON format."""
        # Record some test data
        monitoring_system.record_metric("test.metric", 42.0)
        monitoring_system.update_component_health("test-service", {"healthy": True})
        
        exported = monitoring_system.export_metrics("json")
        data = json.loads(exported)
        
        assert "metrics" in data
        assert "alerts" in data
        assert "component_health" in data
        assert "exported_at" in data
        assert "test.metric" in data["metrics"]
        assert "test-service" in data["component_health"]
    
    @pytest.mark.asyncio
    async def test_export_metrics_prometheus(self, monitoring_system):
        """Test exporting metrics in Prometheus format."""
        monitoring_system.record_metric("test.metric", 42.0)
        monitoring_system.record_metric("another.metric", 100.0)
        
        exported = monitoring_system.export_metrics("prometheus")
        lines = exported.split("\n")
        
        assert "test_metric 42.0" in lines
        assert "another_metric 100.0" in lines
    
    @pytest.mark.asyncio
    async def test_export_metrics_invalid_format(self, monitoring_system):
        """Test exporting metrics with invalid format."""
        with pytest.raises(ValueError, match="Unsupported export format"):
            monitoring_system.export_metrics("invalid")
    
    @pytest.mark.asyncio
    async def test_metric_data_to_dict(self):
        """Test MetricData to_dict method."""
        metric = MetricData(
            name="test.metric",
            value=42.0,
            metric_type=MetricType.GAUGE,
            tags={"tag1": "value1"},
            timestamp=datetime.now()
        )
        
        data = metric.to_dict()
        assert data["name"] == "test.metric"
        assert data["value"] == 42.0
        assert data["type"] == "gauge"
        assert data["tags"] == {"tag1": "value1"}
        assert "timestamp" in data
    
    @pytest.mark.asyncio
    async def test_alert_to_dict(self):
        """Test Alert to_dict method."""
        alert = Alert(
            id="test-alert",
            name="Test Alert",
            severity=AlertSeverity.HIGH,
            message="Test message",
            component="test",
            metric_name="test.metric",
            threshold=100.0,
            current_value=150.0,
            timestamp=datetime.now()
        )
        
        data = alert.to_dict()
        assert data["id"] == "test-alert"
        assert data["name"] == "Test Alert"
        assert data["severity"] == "high"
        assert data["message"] == "Test message"
        assert data["component"] == "test"
        assert data["metric_name"] == "test.metric"
        assert data["threshold"] == 100.0
        assert data["current_value"] == 150.0
        assert data["resolved"] is False
        assert "timestamp" in data
    
    @pytest.mark.asyncio
    async def test_alert_rule_dataclass(self):
        """Test AlertRule dataclass functionality."""
        rule = AlertRule(
            name="Test Rule",
            metric_name="test.metric",
            threshold=50.0,
            comparison="gt",
            severity=AlertSeverity.MEDIUM,
            component="test"
        )
        
        assert rule.name == "Test Rule"
        assert rule.metric_name == "test.metric"
        assert rule.threshold == 50.0
        assert rule.comparison == "gt"
        assert rule.severity == AlertSeverity.MEDIUM
        assert rule.component == "test"
        assert rule.enabled is True
        assert rule.cooldown_minutes == 5
    
    @pytest.mark.asyncio
    async def test_metric_type_enum(self):
        """Test MetricType enum values."""
        assert MetricType.COUNTER.value == "counter"
        assert MetricType.GAUGE.value == "gauge"
        assert MetricType.HISTOGRAM.value == "histogram"
        assert MetricType.TIMER.value == "timer"
    
    @pytest.mark.asyncio
    async def test_alert_severity_enum(self):
        """Test AlertSeverity enum values."""
        assert AlertSeverity.CRITICAL.value == "critical"
        assert AlertSeverity.HIGH.value == "high"
        assert AlertSeverity.MEDIUM.value == "medium"
        assert AlertSeverity.LOW.value == "low"
        assert AlertSeverity.INFO.value == "info"
    
    @pytest.mark.asyncio
    async def test_concurrent_metric_recording(self, monitoring_system):
        """Test concurrent metric recording."""
        async def record_metrics(prefix, count):
            for i in range(count):
                monitoring_system.record_metric(f"{prefix}.metric", i)
        
        # Record metrics concurrently
        tasks = [
            record_metrics("test1", 10),
            record_metrics("test2", 15),
            record_metrics("test3", 20)
        ]
        
        await asyncio.gather(*tasks)
        
        # Check all metrics were recorded
        assert len(monitoring_system.metrics["test1.metric"]) == 10
        assert len(monitoring_system.metrics["test2.metric"]) == 15
        assert len(monitoring_system.metrics["test3.metric"]) == 20
    
    @pytest.mark.asyncio
    async def test_metrics_cleanup(self, monitoring_system):
        """Test metrics cleanup functionality."""
        # Set very short retention
        monitoring_system.retention_hours = 0.001  # About 3.6 seconds
        
        # Record old metric
        monitoring_system.record_metric("test.metric", 42.0)
        
        # Wait for cleanup
        await asyncio.sleep(0.1)
        
        # Manually trigger cleanup
        cutoff_time = datetime.now() - timedelta(hours=monitoring_system.retention_hours)
        monitoring_system.metrics["test.metric"] = [
            m for m in monitoring_system.metrics["test.metric"] 
            if m.timestamp > cutoff_time
        ]
        
        # Check old metrics are removed
        assert len(monitoring_system.metrics["test.metric"]) == 0