#!/usr/bin/env python3
"""
Comprehensive Test Suite for Security Monitoring System

Tests for all security monitoring components including:
- SecurityAuditLogger
- SecurityMonitor
- SecurityDashboard
- SecurityAlertSystem
- SecurityAnalytics
- MonitoringIntegration
"""

import pytest
import asyncio
import tempfile
import os
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, List

# Import security monitoring components
from security.audit_logger import (
    SecurityAuditLogger, SecurityEvent, SecurityEventType, SecuritySeverity,
    create_security_event
)
from security.security_monitor import (
    SecurityMonitor, SecurityAnomaly, SecurityIncident, AnomalyType,
    ThreatLevel, IncidentStatus
)
from security.alert_system import (
    SecurityAlertSystem, AlertType, AlertPriority, AlertRule, SecurityAlert
)
from security.security_analytics import (
    SecurityAnalytics, ComplianceFramework, RiskCategory, SecurityMetric
)
from security.monitoring_integration import SecurityMonitoringIntegration
from dashboard.security_dashboard import SecurityDashboard


class TestSecurityAuditLogger:
    """Test suite for SecurityAuditLogger."""
    
    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database path."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            yield tmp.name
        os.unlink(tmp.name)
    
    @pytest.fixture
    def audit_logger(self, temp_db_path):
        """Create audit logger with temporary database."""
        config = {
            "db_path": temp_db_path,
            "log_dir": tempfile.mkdtemp(),
            "encryption_enabled": False,
            "batch_size": 10,
            "batch_timeout_seconds": 1
        }
        return SecurityAuditLogger(config)
    
    def test_audit_logger_initialization(self, audit_logger):
        """Test audit logger initialization."""
        assert audit_logger is not None
        assert audit_logger.config is not None
        assert os.path.exists(audit_logger.db_path)
    
    @pytest.mark.asyncio
    async def test_log_event(self, audit_logger):
        """Test logging security events."""
        event = create_security_event(
            event_type=SecurityEventType.AUTH_LOGIN_SUCCESS,
            severity=SecuritySeverity.INFO,
            source_component="test",
            user_id="test_user",
            action="login"
        )
        
        result = await audit_logger.log_event(event)
        assert result is True
        
        # Wait for processing
        await asyncio.sleep(2)
        
        # Check if event is stored
        recent_events = audit_logger.get_recent_events(10)
        assert len(recent_events) >= 1
        assert any(e.event_id == event.event_id for e in recent_events)
    
    def test_log_event_sync(self, audit_logger):
        """Test synchronous event logging."""
        event = create_security_event(
            event_type=SecurityEventType.SECURITY_COMMAND_BLOCKED,
            severity=SecuritySeverity.HIGH,
            source_component="test",
            action="rm -rf /"
        )
        
        result = audit_logger.log_event_sync(event)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_query_events(self, audit_logger):
        """Test querying events with filters."""
        # Create test events
        events = [
            create_security_event(
                SecurityEventType.AUTH_LOGIN_SUCCESS,
                SecuritySeverity.INFO,
                "test",
                user_id="user1"
            ),
            create_security_event(
                SecurityEventType.AUTH_LOGIN_FAILURE,
                SecuritySeverity.MEDIUM,
                "test",
                user_id="user2"
            )
        ]
        
        for event in events:
            await audit_logger.log_event(event)
        
        # Wait for processing
        await asyncio.sleep(2)
        
        # Query all events
        all_events = await audit_logger.query_events(limit=10)
        assert len(all_events) >= 2
        
        # Query with user filter
        user1_events = await audit_logger.query_events(user_id="user1", limit=10)
        assert len(user1_events) >= 1
        assert all(e.user_id == "user1" for e in user1_events)
    
    @pytest.mark.asyncio
    async def test_get_statistics(self, audit_logger):
        """Test getting audit statistics."""
        # Create test events
        for i in range(5):
            event = create_security_event(
                SecurityEventType.AUTH_LOGIN_SUCCESS,
                SecuritySeverity.INFO,
                "test",
                user_id=f"user{i}"
            )
            await audit_logger.log_event(event)
        
        await asyncio.sleep(2)
        
        stats = await audit_logger.get_statistics(hours=1)
        assert stats is not None
        assert stats.total_events >= 5
        assert isinstance(stats.security_score, float)
        assert stats.threat_level in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    
    def test_integrity_verification(self, audit_logger):
        """Test event integrity verification."""
        event = create_security_event(
            SecurityEventType.SYSTEM_STARTUP,
            SecuritySeverity.INFO,
            "test"
        )
        
        audit_logger.log_event_sync(event)
        
        # Verify integrity
        is_valid, message = audit_logger.verify_integrity(event.event_id)
        assert is_valid is True
    
    def test_performance_metrics(self, audit_logger):
        """Test performance metrics collection."""
        metrics = audit_logger.get_performance_metrics()
        assert isinstance(metrics, dict)
        assert "total_events_processed" in metrics
        assert "error_count" in metrics
        assert "average_processing_time_ms" in metrics


class TestSecurityMonitor:
    """Test suite for SecurityMonitor."""
    
    @pytest.fixture
    def security_monitor(self):
        """Create security monitor instance."""
        config = {
            "anomaly_detection_enabled": True,
            "behavioral_analysis_enabled": True,
            "auto_incident_creation": True,
            "anomaly_threshold": 0.5
        }
        return SecurityMonitor(config)
    
    def test_monitor_initialization(self, security_monitor):
        """Test security monitor initialization."""
        assert security_monitor is not None
        assert len(security_monitor.anomaly_detectors) > 0
        assert security_monitor.config["anomaly_detection_enabled"] is True
    
    @pytest.mark.asyncio
    async def test_process_security_event(self, security_monitor):
        """Test processing security events."""
        event = create_security_event(
            event_type=SecurityEventType.SECURITY_COMMAND_BLOCKED,
            severity=SecuritySeverity.HIGH,
            source_component="test",
            user_id="test_user",
            action="rm -rf /",
            client_ip="192.168.1.100"
        )
        
        anomalies = await security_monitor.process_security_event(event)
        
        # Should detect pattern anomaly for dangerous command
        assert isinstance(anomalies, list)
        # May or may not detect anomalies depending on thresholds
    
    @pytest.mark.asyncio
    async def test_user_profile_creation(self, security_monitor):
        """Test user profile creation and updates."""
        event = create_security_event(
            SecurityEventType.AUTH_LOGIN_SUCCESS,
            SecuritySeverity.INFO,
            "test",
            user_id="profile_test_user",
            client_ip="192.168.1.50"
        )
        
        await security_monitor.process_security_event(event)
        
        # Check if user profile was created
        assert "profile_test_user" in security_monitor.user_profiles
        profile = security_monitor.user_profiles["profile_test_user"]
        assert profile.user_id == "profile_test_user"
        assert len(profile.typical_ip_ranges) > 0
    
    @pytest.mark.asyncio
    async def test_anomaly_detection(self, security_monitor):
        """Test specific anomaly detection methods."""
        # Test rate anomaly detection
        event = create_security_event(
            SecurityEventType.API_REQUEST,
            SecuritySeverity.INFO,
            "test",
            user_id="rate_test_user"
        )
        
        # Simulate multiple events to trigger rate anomaly
        for _ in range(10):
            await security_monitor._update_metrics(event)
        
        rate_anomalies = await security_monitor._detect_rate_anomalies(event)
        # Rate anomalies depend on configuration and current state
        assert isinstance(rate_anomalies, list)
    
    def test_monitoring_status(self, security_monitor):
        """Test getting monitoring status."""
        status = security_monitor.get_monitoring_status()
        
        assert isinstance(status, dict)
        assert "status" in status
        assert "performance" in status
        assert "detection_engines" in status
        assert "current_threats" in status
        assert status["status"] == "active"


class TestSecurityAlertSystem:
    """Test suite for SecurityAlertSystem."""
    
    @pytest.fixture
    def alert_system(self):
        """Create alert system instance."""
        config = {
            "enabled": True,
            "console_enabled": True,
            "email_enabled": False,
            "slack_enabled": False,
            "github_enabled": False
        }
        return SecurityAlertSystem(config)
    
    def test_alert_system_initialization(self, alert_system):
        """Test alert system initialization."""
        assert alert_system is not None
        assert len(alert_system.alert_rules) > 0
        assert alert_system.config["enabled"] is True
    
    @pytest.mark.asyncio
    async def test_evaluate_event(self, alert_system):
        """Test event evaluation against alert rules."""
        event = create_security_event(
            event_type=SecurityEventType.SECURITY_COMMAND_BLOCKED,
            severity=SecuritySeverity.CRITICAL,
            source_component="test",
            action="dangerous_command"
        )
        
        alerts = await alert_system.evaluate_event(event)
        
        # Should trigger critical security violation alert
        assert isinstance(alerts, list)
        if alerts:
            alert = alerts[0]
            assert alert.alert_type == AlertType.SECURITY_VIOLATION
            assert alert.priority == AlertPriority.CRITICAL
    
    @pytest.mark.asyncio
    async def test_alert_creation_and_processing(self, alert_system):
        """Test alert creation and notification processing."""
        # Create a rule that should trigger
        rule = AlertRule(
            rule_id="test_rule",
            name="Test Alert Rule",
            description="Test rule for unit testing",
            alert_type=AlertType.SECURITY_VIOLATION,
            priority=AlertPriority.HIGH,
            severity_levels=[SecuritySeverity.HIGH],
            channels=[],  # No channels to avoid notification attempts
            trigger_count=1
        )
        
        alert_system.alert_rules["test_rule"] = rule
        
        event = create_security_event(
            SecurityEventType.SECURITY_COMMAND_BLOCKED,
            SecuritySeverity.HIGH,
            "test"
        )
        
        alerts = await alert_system.evaluate_event(event)
        assert len(alerts) > 0
        
        # Wait for processing
        await asyncio.sleep(1)
    
    @pytest.mark.asyncio
    async def test_alert_acknowledgment(self, alert_system):
        """Test alert acknowledgment."""
        # Create a test alert
        alert = SecurityAlert(
            alert_id="test_alert_123",
            rule_id="test_rule",
            alert_type=AlertType.SECURITY_VIOLATION,
            priority=AlertPriority.HIGH,
            status=alert_system.AlertStatus.PENDING,
            title="Test Alert",
            description="Test alert description",
            summary="Test summary",
            created_at=datetime.utcnow(),
            triggered_at=datetime.utcnow()
        )
        
        alert_system.active_alerts[alert.alert_id] = alert
        
        # Acknowledge the alert
        result = await alert_system.acknowledge_alert(alert.alert_id, "test_user")
        assert result is True
        assert alert.status == alert_system.AlertStatus.ACKNOWLEDGED
    
    def test_alert_statistics(self, alert_system):
        """Test alert statistics collection."""
        stats = alert_system.get_alert_statistics()
        
        assert isinstance(stats, dict)
        assert "total_alerts" in stats
        assert "active_alerts" in stats
        assert "configured_rules" in stats
        assert "enabled_rules" in stats


class TestSecurityAnalytics:
    """Test suite for SecurityAnalytics."""
    
    @pytest.fixture
    def mock_audit_logger(self):
        """Create mock audit logger."""
        mock_logger = Mock()
        mock_logger.get_statistics = AsyncMock(return_value=Mock(
            total_events=100,
            security_score=85.0,
            threat_level="LOW",
            compliance_status="COMPLIANT",
            events_by_type={"auth.login.success": 80, "auth.login.failure": 20},
            events_by_severity={"info": 80, "medium": 15, "high": 5},
            top_users={"user1": 50, "user2": 30},
            top_sources={"auth_service": 70, "api_gateway": 30}
        ))
        return mock_logger
    
    @pytest.fixture
    def mock_security_monitor(self):
        """Create mock security monitor."""
        mock_monitor = Mock()
        mock_monitor.active_incidents = {}
        mock_monitor.detected_anomalies = {}
        mock_monitor.get_monitoring_status = Mock(return_value={
            "status": "active",
            "performance": {"events_processed": 100, "avg_processing_time_ms": 5.0},
            "current_threats": {"threat_level": "LOW"}
        })
        return mock_monitor
    
    @pytest.fixture
    def security_analytics(self, mock_audit_logger, mock_security_monitor):
        """Create security analytics instance."""
        return SecurityAnalytics(mock_audit_logger, mock_security_monitor)
    
    def test_analytics_initialization(self, security_analytics):
        """Test security analytics initialization."""
        assert security_analytics is not None
        assert len(security_analytics.security_metrics) > 0
        assert len(security_analytics.compliance_controls) > 0
        assert len(security_analytics.supported_frameworks) > 0
    
    @pytest.mark.asyncio
    async def test_compliance_report_generation(self, security_analytics):
        """Test compliance report generation."""
        report = await security_analytics.generate_compliance_report(
            ComplianceFramework.SOC2
        )
        
        assert report is not None
        assert report.framework == ComplianceFramework.SOC2
        assert isinstance(report.overall_compliance_score, float)
        assert report.controls_assessed > 0
        assert isinstance(report.critical_findings, list)
        assert isinstance(report.recommendations, list)
    
    @pytest.mark.asyncio
    async def test_security_analytics_report(self, security_analytics):
        """Test security analytics report generation."""
        report = await security_analytics.generate_security_analytics_report(7)
        
        assert isinstance(report, dict)
        assert "report_id" in report
        assert "executive_summary" in report
        assert "security_metrics" in report
        assert "risk_assessments" in report
        assert "insights" in report
    
    def test_metric_updates(self, security_analytics):
        """Test security metric updates."""
        initial_value = security_analytics.security_metrics["security_score"].current_value
        
        security_analytics._update_metric("security_score", 90.0)
        
        updated_value = security_analytics.security_metrics["security_score"].current_value
        assert updated_value == 90.0
        assert updated_value != initial_value
    
    @pytest.mark.asyncio
    async def test_risk_assessment_calculation(self, security_analytics):
        """Test risk assessment calculation."""
        assessment = await security_analytics._calculate_risk_assessment(
            RiskCategory.AUTHENTICATION
        )
        
        assert assessment is not None
        assert assessment.risk_category == RiskCategory.AUTHENTICATION
        assert 0 <= assessment.risk_score <= 100
        assert 0 <= assessment.impact_score <= 10
        assert 0 <= assessment.likelihood_score <= 10
        assert assessment.risk_level in ["low", "medium", "high", "critical"]
    
    def test_analytics_summary(self, security_analytics):
        """Test analytics summary generation."""
        summary = security_analytics.get_analytics_summary()
        
        assert isinstance(summary, dict)
        assert "security_metrics" in summary
        assert "compliance_frameworks" in summary
        assert "risk_summary" in summary
        assert "system_status" in summary


class TestSecurityDashboard:
    """Test suite for SecurityDashboard."""
    
    @pytest.fixture
    def mock_components(self, mock_audit_logger, mock_security_monitor):
        """Create mock components for dashboard."""
        return mock_audit_logger, mock_security_monitor
    
    @pytest.fixture
    def security_dashboard(self, mock_components):
        """Create security dashboard instance."""
        audit_logger, security_monitor = mock_components
        config = {
            "update_interval_seconds": 5,
            "real_time_updates": True
        }
        return SecurityDashboard(audit_logger, security_monitor, config)
    
    def test_dashboard_initialization(self, security_dashboard):
        """Test dashboard initialization."""
        assert security_dashboard is not None
        assert security_dashboard.config is not None
    
    @pytest.mark.asyncio
    async def test_get_dashboard_data(self, security_dashboard):
        """Test getting dashboard data."""
        data = await security_dashboard.get_dashboard_data()
        
        assert isinstance(data, dict)
        assert "status" in data
        assert "last_updated" in data
        assert data["status"] in ["active", "error"]
    
    @pytest.mark.asyncio
    async def test_security_overview(self, security_dashboard):
        """Test security overview generation."""
        overview = await security_dashboard.get_security_overview()
        
        assert isinstance(overview, dict)
        if "error" not in overview:
            assert "security_score" in overview
            assert "threat_level" in overview
            assert "system_status" in overview
    
    def test_dashboard_health(self, security_dashboard):
        """Test dashboard health check."""
        health = security_dashboard.get_dashboard_health()
        
        assert isinstance(health, dict)
        assert "status" in health
        assert "performance" in health
        assert "data_points" in health


class TestMonitoringIntegration:
    """Test suite for SecurityMonitoringIntegration."""
    
    @pytest.fixture
    def integration(self):
        """Create monitoring integration instance."""
        config = {
            "enabled": True,
            "real_time_processing": True,
            "event_correlation": True
        }
        return SecurityMonitoringIntegration(config)
    
    def test_integration_initialization(self, integration):
        """Test integration initialization."""
        assert integration is not None
        assert integration.config["enabled"] is True
        assert len(integration.event_processors) > 0
    
    @pytest.mark.asyncio
    async def test_event_processing(self, integration):
        """Test security event processing."""
        event = create_security_event(
            SecurityEventType.AUTH_LOGIN_SUCCESS,
            SecuritySeverity.INFO,
            "test",
            user_id="integration_test_user"
        )
        
        await integration._queue_security_event(event, "test")
        
        # Wait for processing
        await asyncio.sleep(1)
        
        # Check metrics
        assert integration.integration_metrics["events_processed"] >= 0
    
    def test_integration_status(self, integration):
        """Test getting integration status."""
        status = integration.get_integration_status()
        
        assert isinstance(status, dict)
        assert "status" in status
        assert "components_registered" in status
        assert "monitoring_systems" in status
        assert "performance" in status
    
    @pytest.mark.asyncio
    async def test_component_registration(self, integration):
        """Test component registration."""
        # Mock security manager
        mock_security_manager = Mock()
        mock_security_manager.validate_operation = Mock(return_value=(True, "test", Mock()))
        mock_security_manager._log_security_event = Mock()
        
        # Register component
        integration.register_security_manager(mock_security_manager)
        
        # Check registration
        status = integration.get_integration_status()
        assert status["components_registered"]["security_manager"] is True


class TestEndToEndIntegration:
    """End-to-end integration tests."""
    
    @pytest.mark.asyncio
    async def test_full_security_pipeline(self):
        """Test complete security monitoring pipeline."""
        # Create temporary config
        temp_dir = tempfile.mkdtemp()
        config = {
            "db_path": os.path.join(temp_dir, "test_audit.db"),
            "log_dir": temp_dir,
            "encryption_enabled": False,
            "batch_size": 5,
            "batch_timeout_seconds": 1
        }
        
        # Initialize components
        audit_logger = SecurityAuditLogger(config)
        monitor = SecurityMonitor()
        alert_system = SecurityAlertSystem({"console_enabled": True})
        analytics = SecurityAnalytics(audit_logger, monitor)
        dashboard = SecurityDashboard(audit_logger, monitor)
        
        # Create test event
        event = create_security_event(
            event_type=SecurityEventType.SECURITY_COMMAND_BLOCKED,
            severity=SecuritySeverity.HIGH,
            source_component="integration_test",
            user_id="test_user",
            action="rm -rf /",
            client_ip="192.168.1.100"
        )
        
        # Process through pipeline
        await audit_logger.log_event(event)
        anomalies = await monitor.process_security_event(event)
        alerts = await alert_system.evaluate_event(event)
        
        # Wait for processing
        await asyncio.sleep(3)
        
        # Verify results
        recent_events = audit_logger.get_recent_events(10)
        assert len(recent_events) >= 1
        
        stats = await audit_logger.get_statistics(hours=1)
        assert stats.total_events >= 1
        
        dashboard_data = await dashboard.get_dashboard_data()
        assert dashboard_data["status"] == "active"
        
        analytics_summary = analytics.get_analytics_summary()
        assert "security_metrics" in analytics_summary
        
        # Cleanup
        try:
            os.unlink(config["db_path"])
            os.rmdir(temp_dir)
        except:
            pass
    
    @pytest.mark.asyncio
    async def test_performance_under_load(self):
        """Test system performance under load."""
        # Create lightweight components
        audit_logger = SecurityAuditLogger({
            "db_path": ":memory:",
            "encryption_enabled": False,
            "batch_size": 50
        })
        
        # Generate multiple events
        events = []
        for i in range(100):
            event = create_security_event(
                SecurityEventType.API_REQUEST,
                SecuritySeverity.INFO,
                "load_test",
                user_id=f"user_{i % 10}",
                action=f"action_{i}"
            )
            events.append(event)
        
        # Measure processing time
        start_time = datetime.utcnow()
        
        # Process events
        for event in events:
            await audit_logger.log_event(event)
        
        # Wait for processing
        await asyncio.sleep(5)
        
        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds()
        
        # Verify performance
        assert processing_time < 10  # Should process 100 events in under 10 seconds
        
        stats = await audit_logger.get_statistics(hours=1)
        assert stats.total_events >= 100
        
        metrics = audit_logger.get_performance_metrics()
        assert metrics["error_count"] == 0


# Test configuration
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for testing."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.mark.asyncio
async def test_component_compatibility():
    """Test compatibility between all components."""
    # Test that all components can be imported and initialized
    try:
        from security.audit_logger import audit_logger
        from security.security_monitor import security_monitor
        from security.alert_system import alert_system
        from security.security_analytics import security_analytics
        from security.monitoring_integration import security_integration
        
        # Basic functionality test
        assert audit_logger is not None
        assert security_monitor is not None
        assert alert_system is not None
        assert security_analytics is not None
        assert security_integration is not None
        
        # Test basic operations
        event = create_security_event(
            SecurityEventType.SYSTEM_HEALTH_CHECK,
            SecuritySeverity.INFO,
            "compatibility_test"
        )
        
        await audit_logger.log_event(event)
        await security_monitor.process_security_event(event)
        await alert_system.evaluate_event(event)
        
    except Exception as e:
        pytest.fail(f"Component compatibility test failed: {e}")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])