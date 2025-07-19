#!/usr/bin/env python3
"""
Integration tests for advanced security features (PR #6).

Tests core functionality without external dependencies like qrcode, pyotp.
Focuses on architectural integration and basic functionality validation.
"""

import asyncio
import pytest
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Import security components that don't require external dependencies
from security.api_key_manager import ApiKeyManager, ApiKeyType, ApiKeyScope, ApiKeyStatus
from security.compliance_reporter import ComplianceReporter, ComplianceStandard, ComplianceStatus
from security.threat_detector import MLThreatDetector, ThreatCategory, ThreatLevel
from config.auth_models import Permission


class TestApiKeyManagerCore:
    """Test API Key Manager core functionality."""
    
    @pytest.fixture
    def api_key_manager(self):
        """Create ApiKeyManager for testing."""
        config = {
            "key_length": 32,
            "default_expiry_days": 365,
            "max_keys_per_user": 50,
            "encryption_salt": "test-salt-for-testing"
        }
        return ApiKeyManager(config=config)
    
    @pytest.mark.asyncio
    async def test_api_key_creation_basic(self, api_key_manager):
        """Test basic API key creation without external dependencies."""
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
        
        # Verify key is stored
        assert len(api_key_manager.api_keys) == 1
        
        # Get user's keys
        user_keys = await api_key_manager.get_user_api_keys(user_id)
        assert len(user_keys) == 1
        assert user_keys[0]["name"] == "Test API Key"
    
    @pytest.mark.asyncio
    async def test_api_key_validation_basic(self, api_key_manager):
        """Test basic API key validation."""
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
        assert auth_result.metadata["key_name"] == "Test API Key"
    
    @pytest.mark.asyncio
    async def test_api_key_revocation_basic(self, api_key_manager):
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
        
        assert key_id is not None
        
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
        assert "revoked" in auth_result.error.lower()


class TestComplianceReporterCore:
    """Test Compliance Reporter core functionality."""
    
    @pytest.fixture
    def compliance_reporter(self):
        """Create ComplianceReporter for testing."""
        config = {
            "assessment_frequency_days": 90,
            "minimum_compliance_score": 0.8,
            "automated_assessment_enabled": True
        }
        return ComplianceReporter(config=config)
    
    @pytest.mark.asyncio
    async def test_compliance_frameworks_initialization(self, compliance_reporter):
        """Test that compliance frameworks are properly initialized."""
        # Check that compliance controls are loaded
        assert ComplianceStandard.SOC2_TYPE2.value in compliance_reporter.compliance_controls
        assert ComplianceStandard.OWASP_TOP10.value in compliance_reporter.compliance_controls
        assert ComplianceStandard.ISO27001.value in compliance_reporter.compliance_controls
        
        # Check specific controls exist
        soc2_controls = compliance_reporter.compliance_controls[ComplianceStandard.SOC2_TYPE2.value]
        assert "CC6.1" in soc2_controls
        assert "CC6.2" in soc2_controls
        
        owasp_controls = compliance_reporter.compliance_controls[ComplianceStandard.OWASP_TOP10.value]
        assert "A01" in owasp_controls
        assert "A02" in owasp_controls
    
    @pytest.mark.asyncio
    async def test_compliance_report_generation_basic(self, compliance_reporter):
        """Test basic compliance report generation."""
        success, message, report = await compliance_reporter.generate_compliance_report(
            standard=ComplianceStandard.SOC2_TYPE2,
            generated_by="test_system",
            include_evidence=False
        )
        
        assert success is True
        assert report is not None
        assert report.standard == ComplianceStandard.SOC2_TYPE2
        assert report.total_controls > 0
        assert len(report.control_assessments) > 0
        assert 0.0 <= report.overall_score <= 1.0
        
        # Check that assessments have required fields
        for assessment in report.control_assessments:
            assert assessment.control_id is not None
            assert assessment.status in [ComplianceStatus.COMPLIANT, 
                                       ComplianceStatus.NON_COMPLIANT,
                                       ComplianceStatus.PARTIALLY_COMPLIANT,
                                       ComplianceStatus.UNDER_REVIEW]
            assert 0.0 <= assessment.score <= 1.0
    
    @pytest.mark.asyncio
    async def test_owasp_compliance_basic(self, compliance_reporter):
        """Test OWASP compliance assessment."""
        success, message, report = await compliance_reporter.generate_compliance_report(
            standard=ComplianceStandard.OWASP_TOP10,
            generated_by="test_system"
        )
        
        assert success is True
        assert report.standard == ComplianceStandard.OWASP_TOP10
        
        # Check for expected OWASP controls
        control_ids = [assessment.control_id for assessment in report.control_assessments]
        assert "A01" in control_ids  # Broken Access Control
        assert "A02" in control_ids  # Cryptographic Failures
        assert "A03" in control_ids  # Injection
    
    @pytest.mark.asyncio
    async def test_compliance_status_summary_basic(self, compliance_reporter):
        """Test compliance status summary."""
        # Generate a couple of reports
        await compliance_reporter.generate_compliance_report(
            standard=ComplianceStandard.SOC2_TYPE2,
            generated_by="test_system"
        )
        
        await compliance_reporter.generate_compliance_report(
            standard=ComplianceStandard.OWASP_TOP10,
            generated_by="test_system"
        )
        
        summary = await compliance_reporter.get_compliance_status_summary()
        
        assert "overview" in summary
        assert "standards" in summary
        assert summary["overview"]["total_reports"] >= 2
        assert summary["overview"]["standards_assessed"] >= 2


class TestThreatDetectorCore:
    """Test Threat Detector core functionality."""
    
    @pytest.fixture
    def threat_detector(self):
        """Create MLThreatDetector for testing."""
        config = {
            "anomaly_threshold": 2.5,
            "min_baseline_samples": 10,
            "threat_score_threshold": 0.7,
            "behavioral_learning_enabled": True,
            "real_time_detection": True
        }
        return MLThreatDetector(config=config)
    
    @pytest.mark.asyncio
    async def test_threat_detector_initialization(self, threat_detector):
        """Test threat detector initialization."""
        # Check that detection rules are loaded
        assert "brute_force" in threat_detector.detection_rules
        assert "credential_stuffing" in threat_detector.detection_rules
        assert "geo_anomaly" in threat_detector.detection_rules
        assert "rate_violation" in threat_detector.detection_rules
        
        # Check configuration
        assert threat_detector.config["anomaly_threshold"] == 2.5
        assert threat_detector.config["behavioral_learning_enabled"] is True
    
    @pytest.mark.asyncio
    async def test_brute_force_detection_basic(self, threat_detector):
        """Test basic brute force detection."""
        ip_address = "192.168.1.100"
        base_time = datetime.utcnow()
        
        # Simulate multiple failed login attempts from same IP
        threats = []
        for i in range(6):  # Exceed threshold (5)
            event_data = {
                "event_type": "login_failed",
                "ip_address": ip_address,
                "user_id": f"user_{i % 3}",  # Target few users
                "success": False,
                "timestamp": (base_time + timedelta(seconds=i * 30)).isoformat()
            }
            
            detected_threats = await threat_detector.analyze_authentication_event(event_data)
            threats.extend(detected_threats)
        
        # Should detect brute force attack
        brute_force_threats = [t for t in threats if t.category == ThreatCategory.BRUTE_FORCE]
        assert len(brute_force_threats) > 0
        
        threat = brute_force_threats[0]
        assert threat.level in [ThreatLevel.HIGH, ThreatLevel.MEDIUM]
        assert threat.source_ip == ip_address
        assert "brute force" in threat.description.lower()
        assert threat.score > 0.5
    
    @pytest.mark.asyncio
    async def test_credential_stuffing_detection_basic(self, threat_detector):
        """Test basic credential stuffing detection."""
        ip_address = "192.168.1.200"
        base_time = datetime.utcnow()
        
        # Simulate attempts against many different users from same IP
        threats = []
        for i in range(12):  # Exceed threshold (10)
            event_data = {
                "event_type": "login_failed",
                "ip_address": ip_address,
                "user_id": f"different_user_{i}",  # Many different users
                "success": False,
                "timestamp": (base_time + timedelta(seconds=i * 10)).isoformat()
            }
            
            detected_threats = await threat_detector.analyze_authentication_event(event_data)
            threats.extend(detected_threats)
        
        # Should detect credential stuffing
        credential_stuffing_threats = [t for t in threats if t.category == ThreatCategory.CREDENTIAL_STUFFING]
        assert len(credential_stuffing_threats) > 0
        
        threat = credential_stuffing_threats[0]
        assert threat.level == ThreatLevel.HIGH
        assert threat.source_ip == ip_address
        assert "credential stuffing" in threat.description.lower()
    
    @pytest.mark.asyncio
    async def test_rate_limit_violation_basic(self, threat_detector):
        """Test rate limit violation detection."""
        ip_address = "192.168.1.300"
        base_time = datetime.utcnow()
        
        # Simulate high-frequency API requests
        threats = []
        for i in range(120):  # Exceed threshold (100 per minute)
            event_data = {
                "event_type": "api_request",
                "ip_address": ip_address,
                "user_id": "api_user",
                "endpoint": "/api/data",
                "method": "GET",
                "timestamp": (base_time + timedelta(seconds=i * 0.5)).isoformat()  # 2 requests per second
            }
            
            detected_threats = await threat_detector.analyze_api_access_event(event_data)
            threats.extend(detected_threats)
        
        # Should detect rate limit violation
        rate_violations = [t for t in threats if t.category == ThreatCategory.RATE_LIMITING_VIOLATION]
        assert len(rate_violations) > 0
        
        threat = rate_violations[0]
        assert threat.level == ThreatLevel.MEDIUM
        assert "rate limiting violation" in threat.description.lower()
    
    @pytest.mark.asyncio
    async def test_threat_analytics_basic(self, threat_detector):
        """Test threat analytics generation."""
        # Generate some test events first
        for i in range(5):
            event_data = {
                "event_type": "login_failed",
                "ip_address": f"192.168.1.{i}",
                "user_id": f"user_{i}",
                "success": False,
                "timestamp": datetime.utcnow().isoformat()
            }
            await threat_detector.analyze_authentication_event(event_data)
        
        analytics = await threat_detector.get_threat_analytics()
        
        assert "overview" in analytics
        assert "threat_distribution" in analytics
        assert "detection_rules" in analytics
        assert "configuration" in analytics
        
        # Check overview data
        overview = analytics["overview"]
        assert "total_threat_events" in overview
        assert "users_monitored" in overview
        
        # Check configuration
        config = analytics["configuration"]
        assert config["anomaly_threshold"] == 2.5
        assert config["behavioral_learning_enabled"] is True


class TestSecurityIntegrationBasic:
    """Test basic integration between security components."""
    
    @pytest.mark.asyncio
    async def test_component_initialization(self):
        """Test that all components can be initialized together."""
        # Initialize all components
        api_key_manager = ApiKeyManager()
        compliance_reporter = ComplianceReporter()
        threat_detector = MLThreatDetector()
        
        assert api_key_manager is not None
        assert compliance_reporter is not None
        assert threat_detector is not None
        
        # Test basic functionality of each
        analytics_api = await api_key_manager.get_api_key_analytics()
        assert "overview" in analytics_api
        
        status_compliance = await compliance_reporter.get_compliance_status_summary()
        assert "overview" in status_compliance
        
        analytics_threat = await threat_detector.get_threat_analytics()
        assert "overview" in analytics_threat
    
    @pytest.mark.asyncio
    async def test_cross_component_data_flow(self):
        """Test data flow between components."""
        # Initialize components
        api_key_manager = ApiKeyManager()
        threat_detector = MLThreatDetector()
        
        # Create API key
        success, message, api_key = await api_key_manager.create_api_key(
            user_id="test_user",
            name="Test Key",
            description="Test",
            key_type=ApiKeyType.PERSONAL,
            scope=ApiKeyScope.READ_ONLY,
            permissions=[Permission.READ]
        )
        
        assert success is True
        
        # Simulate API usage that generates events for threat detection
        for i in range(5):
            event_data = {
                "event_type": "api_request",
                "user_id": "test_user",
                "ip_address": "192.168.1.100",
                "endpoint": "/api/test",
                "method": "GET",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Analyze event for threats
            threats = await threat_detector.analyze_api_access_event(event_data)
            assert isinstance(threats, list)
        
        # Verify both systems have data
        api_analytics = await api_key_manager.get_api_key_analytics()
        assert api_analytics["overview"]["total_keys"] >= 1
        
        threat_analytics = await threat_detector.get_threat_analytics()
        assert isinstance(threat_analytics["overview"]["total_threat_events"], int)
    
    @pytest.mark.asyncio
    async def test_compliance_integration_basic(self):
        """Test compliance integration with other components."""
        # Initialize compliance reporter with mock components
        compliance_reporter = ComplianceReporter()
        
        # Generate compliance report
        success, message, report = await compliance_reporter.generate_compliance_report(
            standard=ComplianceStandard.SOC2_TYPE2,
            generated_by="integration_test"
        )
        
        assert success is True
        assert report is not None
        
        # Test report export
        export_success, export_message, exported_data = await compliance_reporter.export_compliance_report(
            report_id=report.report_id,
            format_type="json"
        )
        
        assert export_success is True
        assert exported_data is not None
        
        # Verify exported data contains expected fields
        import json
        report_data = json.loads(exported_data)
        assert "report_id" in report_data
        assert "standard" in report_data
        assert "overall_score" in report_data


if __name__ == "__main__":
    # Run specific tests to validate core functionality
    pytest.main([__file__, "-v", "-k", "test_api_key_creation_basic or test_compliance_report_generation_basic or test_brute_force_detection_basic"])