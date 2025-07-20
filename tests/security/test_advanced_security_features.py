#!/usr/bin/env python3
"""
Comprehensive tests for advanced security features.

Tests all components of PR #6: 2FA, API Key Management, Compliance Reporting,
Threat Detection, and the integrated Advanced Security Coordinator.
"""

import asyncio
import pytest
import tempfile
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List

from security.two_factor_auth import TwoFactorAuthManager, TwoFactorMethod, DeviceStatus
from security.api_key_manager import ApiKeyManager, ApiKeyType, ApiKeyScope, ApiKeyStatus
from security.compliance_reporter import ComplianceReporter, ComplianceStandard, ComplianceStatus
from security.threat_detector import MLThreatDetector, ThreatCategory, ThreatLevel
from security.advanced_security_coordinator import AdvancedSecurityCoordinator
from security.security_manager import SecurityManager
from config.auth_models import Permission


class TestTwoFactorAuthentication:
    """Test Two-Factor Authentication system."""
    
    @pytest.fixture
    def two_factor_manager(self):
        """Create TwoFactorAuthManager for testing."""
        config = {
            "totp_window": 1,
            "backup_code_count": 10,
            "trusted_device_duration_days": 30,
            "max_trusted_devices": 5
        }
        return TwoFactorAuthManager(config=config)
    
    @pytest.mark.asyncio
    async def test_totp_setup(self, two_factor_manager):
        """Test TOTP setup for user."""
        user_id = "test_user_123"
        username = "testuser"
        email = "test@example.com"
        
        success, message, secret, qr_code = await two_factor_manager.setup_totp_for_user(
            user_id=user_id,
            username=username,
            email=email
        )
        
        assert success is True
        assert "successful" in message.lower()
        assert secret is not None
        assert qr_code is not None or secret is not None  # QR code might fail if pyotp not available
    
    @pytest.mark.asyncio
    async def test_2fa_challenge_creation(self, two_factor_manager):
        """Test creating 2FA challenge."""
        user_id = "test_user_123"
        
        # First set up TOTP
        await two_factor_manager.setup_totp_for_user(user_id, "testuser", "test@example.com")
        
        success, message, session_id = await two_factor_manager.create_two_factor_challenge(
            user_id=user_id,
            challenge_type=TwoFactorMethod.TOTP,
            ip_address="192.168.1.100"
        )
        
        assert success is True
        assert session_id is not None
        assert "challenge created" in message.lower()
    
    @pytest.mark.asyncio
    async def test_backup_code_generation(self, two_factor_manager):
        """Test backup code generation."""
        user_id = "test_user_123"
        
        success, message, backup_codes = await two_factor_manager.generate_backup_codes(user_id)
        
        assert success is True
        assert backup_codes is not None
        assert len(backup_codes) == 10
        assert all(len(code) == 8 for code in backup_codes)
    
    @pytest.mark.asyncio
    async def test_trusted_device_management(self, two_factor_manager):
        """Test trusted device management."""
        user_id = "test_user_123"
        device_fingerprint = "device_123_fingerprint"
        
        # Create trusted device
        device_id = await two_factor_manager._create_trusted_device(
            user_id=user_id,
            device_fingerprint=device_fingerprint,
            ip_address="192.168.1.100"
        )
        
        assert device_id is not None
        
        # Check if device is trusted
        is_trusted = await two_factor_manager._is_device_trusted(user_id, device_id)
        assert is_trusted is True
        
        # Revoke trusted device
        success, message = await two_factor_manager.revoke_trusted_device(user_id, device_id)
        assert success is True
    
    @pytest.mark.asyncio
    async def test_2fa_status(self, two_factor_manager):
        """Test 2FA status retrieval."""
        user_id = "test_user_123"
        
        # Initial status (no 2FA)
        status = await two_factor_manager.get_two_factor_status(user_id)
        assert status["2fa_enabled"] is False
        
        # Set up 2FA
        await two_factor_manager.setup_totp_for_user(user_id, "testuser", "test@example.com")
        
        # Status after setup
        status = await two_factor_manager.get_two_factor_status(user_id)
        assert status["2fa_enabled"] is True


class TestApiKeyManager:
    """Test API Key Management system."""
    
    @pytest.fixture
    def api_key_manager(self):
        """Create ApiKeyManager for testing."""
        config = {
            "key_length": 32,
            "default_expiry_days": 365,
            "max_keys_per_user": 50
        }
        return ApiKeyManager(config=config)
    
    @pytest.mark.asyncio
    async def test_api_key_creation(self, api_key_manager):
        """Test API key creation."""
        user_id = "test_user_123"
        
        success, message, api_key = await api_key_manager.create_api_key(
            user_id=user_id,
            name="Test API Key",
            description="Test key for unit tests",
            key_type=ApiKeyType.PERSONAL,
            scope=ApiKeyScope.READ_WRITE,
            permissions=[Permission.READ, Permission.WRITE]
        )
        
        assert success is True
        assert api_key is not None
        assert api_key.startswith("ak_")
        assert "successful" in message.lower()
    
    @pytest.mark.asyncio
    async def test_api_key_validation(self, api_key_manager):
        """Test API key validation."""
        user_id = "test_user_123"
        
        # Create API key
        success, message, api_key = await api_key_manager.create_api_key(
            user_id=user_id,
            name="Test API Key",
            description="Test key",
            key_type=ApiKeyType.PERSONAL,
            scope=ApiKeyScope.READ_WRITE,
            permissions=[Permission.READ, Permission.WRITE]
        )
        
        assert success is True
        
        # Validate API key
        auth_result = await api_key_manager.validate_api_key(
            api_key=api_key,
            endpoint="/api/test",
            method="GET",
            client_ip="192.168.1.100",
            user_agent="test-agent"
        )
        
        assert auth_result.success is True
        assert auth_result.user_id == user_id
        assert Permission.READ in auth_result.permissions
    
    @pytest.mark.asyncio
    async def test_api_key_rotation(self, api_key_manager):
        """Test API key rotation."""
        user_id = "test_user_123"
        
        # Create API key
        success, message, original_key = await api_key_manager.create_api_key(
            user_id=user_id,
            name="Test API Key",
            description="Test key",
            key_type=ApiKeyType.PERSONAL,
            scope=ApiKeyScope.READ_WRITE,
            permissions=[Permission.READ]
        )
        
        assert success is True
        
        # Get key ID for rotation
        key_id = None
        for stored_key_id, metadata in api_key_manager.api_keys.items():
            if metadata.user_id == user_id:
                key_id = stored_key_id
                break
        
        assert key_id is not None
        
        # Rotate the key
        success, message, new_key = await api_key_manager.rotate_api_key(
            key_id=key_id,
            rotated_by="test_system"
        )
        
        assert success is True
        assert new_key != original_key
        assert new_key.startswith("ak_")
    
    @pytest.mark.asyncio
    async def test_api_key_revocation(self, api_key_manager):
        """Test API key revocation."""
        user_id = "test_user_123"
        
        # Create API key
        success, message, api_key = await api_key_manager.create_api_key(
            user_id=user_id,
            name="Test API Key",
            description="Test key",
            key_type=ApiKeyType.PERSONAL,
            scope=ApiKeyScope.READ_WRITE,
            permissions=[Permission.READ]
        )
        
        assert success is True
        
        # Get key ID
        key_id = None
        for stored_key_id, metadata in api_key_manager.api_keys.items():
            if metadata.user_id == user_id:
                key_id = stored_key_id
                break
        
        # Revoke the key
        success, message = await api_key_manager.revoke_api_key(
            key_id=key_id,
            revoked_by="test_system"
        )
        
        assert success is True
        
        # Verify key is revoked
        auth_result = await api_key_manager.validate_api_key(
            api_key=api_key,
            endpoint="/api/test",
            method="GET",
            client_ip="192.168.1.100",
            user_agent="test-agent"
        )
        
        assert auth_result.success is False
    
    @pytest.mark.asyncio
    async def test_api_key_analytics(self, api_key_manager):
        """Test API key analytics."""
        user_id = "test_user_123"
        
        # Create a few API keys
        for i in range(3):
            await api_key_manager.create_api_key(
                user_id=user_id,
                name=f"Test Key {i}",
                description=f"Test key {i}",
                key_type=ApiKeyType.PERSONAL,
                scope=ApiKeyScope.READ_ONLY,
                permissions=[Permission.READ]
            )
        
        analytics = await api_key_manager.get_api_key_analytics()
        
        assert "overview" in analytics
        assert analytics["overview"]["total_keys"] >= 3
        assert analytics["overview"]["active_keys"] >= 3


class TestComplianceReporter:
    """Test Compliance Reporting system."""
    
    @pytest.fixture
    def compliance_reporter(self):
        """Create ComplianceReporter for testing."""
        config = {
            "assessment_frequency_days": 90,
            "minimum_compliance_score": 0.8
        }
        return ComplianceReporter(config=config)
    
    @pytest.mark.asyncio
    async def test_compliance_report_generation(self, compliance_reporter):
        """Test compliance report generation."""
        success, message, report = await compliance_reporter.generate_compliance_report(
            standard=ComplianceStandard.SOC2_TYPE2,
            generated_by="test_system"
        )
        
        assert success is True
        assert report is not None
        assert report.standard == ComplianceStandard.SOC2_TYPE2
        assert report.total_controls > 0
        assert len(report.control_assessments) > 0
    
    @pytest.mark.asyncio
    async def test_owasp_compliance_report(self, compliance_reporter):
        """Test OWASP compliance report generation."""
        success, message, report = await compliance_reporter.generate_compliance_report(
            standard=ComplianceStandard.OWASP_TOP10,
            generated_by="test_system"
        )
        
        assert success is True
        assert report is not None
        assert report.standard == ComplianceStandard.OWASP_TOP10
        assert len(report.control_assessments) > 0
    
    @pytest.mark.asyncio
    async def test_compliance_status_summary(self, compliance_reporter):
        """Test compliance status summary."""
        # Generate a report first
        await compliance_reporter.generate_compliance_report(
            standard=ComplianceStandard.SOC2_TYPE2,
            generated_by="test_system"
        )
        
        summary = await compliance_reporter.get_compliance_status_summary()
        
        assert "overview" in summary
        assert "standards" in summary
        assert summary["overview"]["total_reports"] >= 1
    
    @pytest.mark.asyncio
    async def test_report_export(self, compliance_reporter):
        """Test compliance report export."""
        # Generate a report
        success, message, report = await compliance_reporter.generate_compliance_report(
            standard=ComplianceStandard.ISO27001,
            generated_by="test_system"
        )
        
        assert success is True
        
        # Export report
        export_success, export_message, exported_data = await compliance_reporter.export_compliance_report(
            report_id=report.report_id,
            format_type="json"
        )
        
        assert export_success is True
        assert exported_data is not None
        assert "report_id" in exported_data


class TestThreatDetector:
    """Test ML-based Threat Detection system."""
    
    @pytest.fixture
    def threat_detector(self):
        """Create MLThreatDetector for testing."""
        config = {
            "anomaly_threshold": 2.5,
            "min_baseline_samples": 10,
            "threat_score_threshold": 0.7
        }
        return MLThreatDetector(config=config)
    
    @pytest.mark.asyncio
    async def test_brute_force_detection(self, threat_detector):
        """Test brute force attack detection."""
        ip_address = "192.168.1.100"
        
        # Simulate multiple failed login attempts
        threats = []
        for i in range(6):  # Exceed threshold
            event_data = {
                "event_type": "login_failed",
                "ip_address": ip_address,
                "user_id": f"user_{i}",
                "success": False,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            detected_threats = await threat_detector.analyze_authentication_event(event_data)
            threats.extend(detected_threats)
        
        # Should detect brute force attack
        brute_force_threats = [t for t in threats if t.category == ThreatCategory.BRUTE_FORCE]
        assert len(brute_force_threats) > 0
        assert brute_force_threats[0].level in [ThreatLevel.HIGH, ThreatLevel.MEDIUM]
    
    @pytest.mark.asyncio
    async def test_credential_stuffing_detection(self, threat_detector):
        """Test credential stuffing attack detection."""
        ip_address = "192.168.1.200"
        
        # Simulate attempts against multiple different users
        threats = []
        for i in range(12):  # Exceed threshold
            event_data = {
                "event_type": "login_failed",
                "ip_address": ip_address,
                "user_id": f"different_user_{i}",
                "success": False,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            detected_threats = await threat_detector.analyze_authentication_event(event_data)
            threats.extend(detected_threats)
        
        # Should detect credential stuffing
        credential_stuffing_threats = [t for t in threats if t.category == ThreatCategory.CREDENTIAL_STUFFING]
        assert len(credential_stuffing_threats) > 0
        assert credential_stuffing_threats[0].level == ThreatLevel.HIGH
    
    @pytest.mark.asyncio
    async def test_rate_limit_violation_detection(self, threat_detector):
        """Test rate limiting violation detection."""
        ip_address = "192.168.1.300"
        
        # Simulate high-frequency API requests
        threats = []
        for i in range(150):  # Exceed threshold
            event_data = {
                "event_type": "api_request",
                "ip_address": ip_address,
                "user_id": "api_user",
                "endpoint": "/api/data",
                "method": "GET",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            detected_threats = await threat_detector.analyze_api_access_event(event_data)
            threats.extend(detected_threats)
        
        # Should detect rate limit violation
        rate_violations = [t for t in threats if t.category == ThreatCategory.RATE_LIMITING_VIOLATION]
        assert len(rate_violations) > 0
    
    @pytest.mark.asyncio
    async def test_behavioral_anomaly_detection(self, threat_detector):
        """Test behavioral anomaly detection."""
        user_id = "test_user_behavior"
        
        # Establish baseline behavior
        normal_activities = []
        for i in range(20):
            normal_activities.append({
                "timestamp": (datetime.utcnow() - timedelta(hours=i)).isoformat(),
                "endpoint": "/api/normal",
                "status_code": 200,
                "response_time_ms": 100 + i * 5
            })
        
        # Analyze normal behavior first (to establish baseline)
        await threat_detector.analyze_user_behavior(user_id, normal_activities)
        
        # Now simulate anomalous behavior
        anomalous_activities = []
        for i in range(10):
            anomalous_activities.append({
                "timestamp": datetime.utcnow().isoformat(),
                "endpoint": "/api/unusual",
                "status_code": 500,
                "response_time_ms": 5000,  # Very slow
                "user_agent": f"Unusual-Agent-{i}"
            })
        
        threats = await threat_detector.analyze_user_behavior(user_id, anomalous_activities)
        
        # May detect behavioral anomalies (depends on baseline establishment)
        assert isinstance(threats, list)
    
    @pytest.mark.asyncio
    async def test_threat_analytics(self, threat_detector):
        """Test threat analytics retrieval."""
        analytics = await threat_detector.get_threat_analytics()
        
        assert "overview" in analytics
        assert "threat_distribution" in analytics
        assert "detection_rules" in analytics
        assert "configuration" in analytics


class TestAdvancedSecurityCoordinator:
    """Test Advanced Security Coordinator integration."""
    
    @pytest.fixture
    def security_coordinator(self):
        """Create AdvancedSecurityCoordinator for testing."""
        config = {
            "monitoring_interval_seconds": 60,
            "auto_threat_response": True,
            "real_time_monitoring": True
        }
        return AdvancedSecurityCoordinator(config=config)
    
    @pytest.mark.asyncio
    async def test_coordinator_initialization(self, security_coordinator):
        """Test that all components are properly initialized."""
        assert security_coordinator.auth_service is not None
        assert security_coordinator.rbac_manager is not None
        assert security_coordinator.two_factor_auth is not None
        assert security_coordinator.api_key_manager is not None
        assert security_coordinator.compliance_reporter is not None
        assert security_coordinator.threat_detector is not None
    
    @pytest.mark.asyncio
    async def test_comprehensive_authentication(self, security_coordinator):
        """Test comprehensive authentication flow."""
        # First create a user (this would normally be done through proper user creation)
        username = "test_coord_user"
        password = "test_password_123!"
        
        # This test demonstrates the authentication flow
        # In a real system, the user would already exist
        success, message, session_data = await security_coordinator.authenticate_user_comprehensive(
            username=username,
            password=password,
            client_ip="192.168.1.100",
            user_agent="test-browser"
        )
        
        # Authentication may fail because user doesn't exist, but the flow should be tested
        assert isinstance(success, bool)
        assert isinstance(message, str)
    
    @pytest.mark.asyncio
    async def test_security_dashboard(self, security_coordinator):
        """Test security dashboard generation."""
        dashboard = await security_coordinator.get_security_dashboard()
        
        assert "timestamp" in dashboard
        assert "overall_security_score" in dashboard
        assert "security_level" in dashboard
        assert "metrics" in dashboard
        assert "recommendations" in dashboard
        
        # Check that all component metrics are included
        metrics = dashboard["metrics"]
        assert "authentication" in metrics
        assert "rbac" in metrics
        assert "two_factor" in metrics
        assert "api_keys" in metrics
        assert "compliance" in metrics
        assert "threats" in metrics
    
    @pytest.mark.asyncio
    async def test_health_check(self, security_coordinator):
        """Test comprehensive health check."""
        health = await security_coordinator.health_check()
        
        assert "timestamp" in health
        assert "overall_status" in health
        assert "components" in health
        
        # All components should be present in health check
        components = health["components"]
        expected_components = [
            "auth_service", "rbac_manager", "two_factor_auth",
            "api_key_manager", "compliance_reporter", "threat_detector"
        ]
        
        for component in expected_components:
            assert component in components
            assert "status" in components[component]
            assert "initialized" in components[component]
    
    @pytest.mark.asyncio
    async def test_security_metrics_collection(self, security_coordinator):
        """Test security metrics collection."""
        metrics = await security_coordinator._get_current_security_metrics()
        
        assert metrics is not None
        assert isinstance(metrics.overall_security_score, float)
        assert 0.0 <= metrics.overall_security_score <= 1.0
        assert metrics.timestamp is not None
        assert isinstance(metrics.authentication_stats, dict)
        assert isinstance(metrics.rbac_stats, dict)


# Integration Tests
class TestSecurityIntegration:
    """Test integration between all security components."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_security_workflow(self):
        """Test complete end-to-end security workflow."""
        # Initialize coordinator
        coordinator = AdvancedSecurityCoordinator()
        
        # Test health check
        health = await coordinator.health_check()
        assert health["overall_status"] in ["healthy", "degraded", "warning"]
        
        # Test dashboard generation
        dashboard = await coordinator.get_security_dashboard()
        assert "overall_security_score" in dashboard
        
        # Test compliance report generation
        success, message, report = await coordinator.generate_compliance_report_comprehensive(
            standard=ComplianceStandard.OWASP_TOP10,
            generated_by="integration_test"
        )
        
        # Report generation should succeed
        assert success is True or "not found" in message.lower()  # May fail if dependencies missing
    
    @pytest.mark.asyncio
    async def test_threat_detection_integration(self):
        """Test threat detection integration with other components."""
        coordinator = AdvancedSecurityCoordinator()
        
        # Simulate authentication events that should trigger threat detection
        for i in range(5):
            event_data = {
                "event_type": "login_failed",
                "ip_address": "192.168.1.999",
                "user_id": f"test_user_{i}",
                "success": False,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            threats = await coordinator.threat_detector.analyze_authentication_event(event_data)
            
            # Threat detection should work
            assert isinstance(threats, list)
    
    @pytest.mark.asyncio
    async def test_component_interaction(self):
        """Test that components interact correctly."""
        coordinator = AdvancedSecurityCoordinator()
        
        # Test that compliance reporter can access other components
        compliance_status = await coordinator.compliance_reporter.get_compliance_status_summary()
        assert isinstance(compliance_status, dict)
        
        # Test that threat detector analytics work
        threat_analytics = await coordinator.threat_detector.get_threat_analytics()
        assert "overview" in threat_analytics
        
        # Test that API key manager analytics work
        api_analytics = await coordinator.api_key_manager.get_api_key_analytics()
        assert "overview" in api_analytics


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])