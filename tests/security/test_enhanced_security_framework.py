#!/usr/bin/env python3
"""
Enhanced Security Framework Tests

Tests for the JWT authentication system, bcrypt integration, 
quality gates, and vulnerability scanning components.
"""

import pytest
import asyncio
import tempfile
import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

# Import new security components
from security.auth_service import AuthenticationService, UserRole, User, UserSession
from security.token_manager import SecureTokenManager, TokenType, TokenStatus
from security.quality_gates import SecurityQualityGates, SeverityLevel, QualityGateStatus
from security.vulnerability_scanner import VulnerabilityScanner
from security.enhanced_middleware import EnhancedSecurityMiddleware, SecurityLevel
from external_api.auth_middleware import AuthenticationMiddleware, Permission, AuthResult
from external_api.models import ApiRequest


class TestEnhancedSecurityFramework:
    """Test suite for enhanced security framework."""
    
    @pytest.fixture
    def auth_config(self):
        """Authentication service configuration."""
        return {
            "bcrypt_rounds": 10,  # Lower for testing
            "jwt_secret": "test_secret_key_32_characters_long",
            "jwt_algorithm": "HS256",
            "token_expiry_minutes": 15,
            "max_failed_attempts": 3,
            "lockout_duration_minutes": 5,
            "session_timeout_minutes": 30,
            "password_expiry_days": 90,
            "require_2fa": False
        }
    
    @pytest.fixture
    def auth_service(self, auth_config):
        """Authentication service instance."""
        return AuthenticationService(auth_config)
    
    @pytest.fixture
    def token_manager(self, auth_config):
        """Token manager instance."""
        return SecureTokenManager(auth_config)
    
    @pytest.fixture
    def temp_dir(self):
        """Temporary directory for test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def quality_gates(self, temp_dir):
        """Security quality gates instance."""
        # Create a temporary config file
        config_file = temp_dir / "security_config.json"
        config = {
            "security_monitoring": {
                "thresholds": {"critical_threshold": 0, "high_threshold": 3},
                "scan_configuration": {
                    "bandit": {"enabled": True},
                    "safety": {"enabled": True},
                    "custom_checks": {"enabled": True}
                }
            }
        }
        with open(config_file, 'w') as f:
            json.dump(config, f)
        
        return SecurityQualityGates(str(config_file))
    
    async def test_complete_authentication_flow(self, auth_service):
        """Test complete authentication flow from user creation to session validation."""
        # Create user
        success, message, user = await auth_service.create_user(
            username="testuser",
            email="test@example.com",
            password="SecurePassword123!",
            roles=[UserRole.DEVELOPER],
            active=True
        )
        
        assert success is True
        assert user is not None
        assert user.username == "testuser"
        assert len(user.roles) == 1
        assert UserRole.DEVELOPER in user.roles
        
        # Authenticate user
        success, message, session = await auth_service.authenticate_user(
            username="testuser",
            password="SecurePassword123!",
            client_ip="192.168.1.100",
            user_agent="Test Agent"
        )
        
        assert success is True
        assert session is not None
        assert session.user_id == user.user_id
        assert session.ip_address == "192.168.1.100"
        
        # Validate session
        auth_result = await auth_service.validate_session(
            access_token=session.access_token,
            client_ip="192.168.1.100",
            required_permissions=[Permission.READ]
        )
        
        assert auth_result.success is True
        assert auth_result.user_id == user.user_id
        assert Permission.READ in auth_result.permissions
        
        # Test session refresh
        success, message, new_session = await auth_service.refresh_session(
            refresh_token=session.refresh_token,
            client_ip="192.168.1.100"
        )
        
        assert success is True
        assert new_session.access_token != session.access_token
        
        # Logout user
        success, message = await auth_service.logout_user(new_session.access_token)
        assert success is True
    
    async def test_password_security_features(self, auth_service):
        """Test password security features including policy validation and history."""
        # Test weak password rejection
        success, message, user = await auth_service.create_user(
            username="weakuser",
            email="weak@example.com",
            password="weak",
            roles=[UserRole.VIEWER]
        )
        
        assert success is False
        assert "policy violation" in message.lower()
        
        # Create user with strong password
        success, message, user = await auth_service.create_user(
            username="stronguser",
            email="strong@example.com",
            password="VerySecurePassword123!",
            roles=[UserRole.DEVELOPER]
        )
        
        assert success is True
        
        # Test password change
        success, message = await auth_service.change_password(
            user_id=user.user_id,
            current_password="VerySecurePassword123!",
            new_password="NewSecurePassword456!"
        )
        
        assert success is True
        
        # Test password reuse prevention
        success, message = await auth_service.change_password(
            user_id=user.user_id,
            current_password="NewSecurePassword456!",
            new_password="VerySecurePassword123!"  # Original password
        )
        
        assert success is False
        assert "recently used" in message.lower()
    
    async def test_account_lockout_mechanism(self, auth_service):
        """Test account lockout after multiple failed attempts."""
        # Create test user
        success, message, user = await auth_service.create_user(
            username="lockoutuser",
            email="lockout@example.com",
            password="SecurePassword123!",
            roles=[UserRole.VIEWER]
        )
        
        assert success is True
        
        # Attempt multiple failed logins
        for i in range(3):  # max_failed_attempts = 3 in config
            success, message, session = await auth_service.authenticate_user(
                username="lockoutuser",
                password="WrongPassword",
                client_ip="192.168.1.100",
                user_agent="Test Agent"
            )
            assert success is False
        
        # Account should now be locked
        success, message, session = await auth_service.authenticate_user(
            username="lockoutuser",
            password="SecurePassword123!",  # Correct password
            client_ip="192.168.1.100",
            user_agent="Test Agent"
        )
        
        assert success is False
        assert "locked" in message.lower()
    
    async def test_jwt_token_security(self, token_manager):
        """Test JWT token security features."""
        # Create secure token
        token, token_id = await token_manager.create_secure_token(
            user_id="test_user",
            token_type=TokenType.ACCESS,
            permissions=[Permission.READ, Permission.WRITE],
            expires_in_hours=1
        )
        
        assert token is not None
        assert token_id is not None
        
        # Validate token
        auth_result = await token_manager.validate_token_secure(
            token=token,
            required_permissions=[Permission.READ],
            client_ip="192.168.1.100"
        )
        
        assert auth_result.success is True
        assert auth_result.user_id == "test_user"
        
        # Test token rotation
        new_token, new_token_id = await token_manager.rotate_token(token)
        assert new_token is not None
        assert new_token != token
        
        # Original token should be blacklisted
        old_auth_result = await token_manager.validate_token_secure(
            token=token,
            client_ip="192.168.1.100"
        )
        
        assert old_auth_result.success is False
        
        # New token should work
        new_auth_result = await token_manager.validate_token_secure(
            token=new_token,
            client_ip="192.168.1.100"
        )
        
        assert new_auth_result.success is True
    
    async def test_rbac_authorization(self, auth_service):
        """Test role-based access control."""
        # Create users with different roles
        admin_success, _, admin_user = await auth_service.create_user(
            username="admin",
            email="admin@example.com",
            password="AdminPassword123!",
            roles=[UserRole.ADMIN]
        )
        
        viewer_success, _, viewer_user = await auth_service.create_user(
            username="viewer",
            email="viewer@example.com",
            password="ViewerPassword123!",
            roles=[UserRole.VIEWER]
        )
        
        assert admin_success is True
        assert viewer_success is True
        
        # Admin should have all permissions
        assert Permission.ADMIN in admin_user.permissions
        assert Permission.READ in admin_user.permissions
        assert Permission.WRITE in admin_user.permissions
        
        # Viewer should only have read permission
        assert Permission.READ in viewer_user.permissions
        assert Permission.ADMIN not in viewer_user.permissions
        assert Permission.WRITE not in viewer_user.permissions
    
    async def test_security_quality_gates(self, quality_gates, temp_dir):
        """Test security quality gates framework."""
        # Create test Python file with security issues
        test_file = temp_dir / "test_security.py"
        test_file.write_text("""
import os
import subprocess

# Hardcoded secret (should be detected)
API_KEY = "sk-1234567890abcdef"
password = "hardcoded_password"

# Command injection vulnerability
def run_command(user_input):
    os.system(f"ls {user_input}")
    
# SQL injection pattern
def get_user(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return query
""")
        
        # Run quality gates
        results = await quality_gates.run_all_quality_gates([str(temp_dir)])
        
        # Should detect security issues
        total_issues = sum(len(result.issues) for result in results.values())
        assert total_issues > 0
        
        # Should detect critical issues (secrets)
        critical_issues = []
        for result in results.values():
            critical_issues.extend([issue for issue in result.issues 
                                  if issue.severity == SeverityLevel.CRITICAL])
        
        assert len(critical_issues) > 0
        
        # Check zero critical policy
        policy_ok, violations = await quality_gates.check_zero_critical_policy(results)
        assert policy_ok is False
        assert len(violations) > 0
    
    async def test_vulnerability_scanner(self, temp_dir):
        """Test vulnerability scanner functionality."""
        # Create config file
        config_file = temp_dir / "security_config.json"
        config = {
            "security_monitoring": {
                "monitoring_intervals": {"scan_interval_hours": 6},
                "automation": {"auto_create_issues": False}
            }
        }
        with open(config_file, 'w') as f:
            json.dump(config, f)
        
        # Change to temp directory for scanner
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            
            scanner = VulnerabilityScanner(str(config_file))
            
            # Run manual scan
            report = await scanner.run_manual_scan(["secrets", "custom"])
            
            assert report is not None
            assert report.scan_id is not None
            assert isinstance(report.total_vulnerabilities, int)
            
            # Get security dashboard
            dashboard = await scanner.generate_security_dashboard()
            assert "status" in dashboard
            
        finally:
            os.chdir(original_cwd)
    
    async def test_enhanced_middleware_security(self, auth_service):
        """Test enhanced security middleware."""
        middleware = EnhancedSecurityMiddleware(auth_service, {
            "ip_blacklist": ["192.168.1.200/32"],
            "alert_thresholds": {"critical": 1, "high": 5}
        })
        
        # Test legitimate request
        request = ApiRequest(
            request_id="test-1",
            method="GET",
            path="/api/v1/agents",
            headers={"Authorization": "Bearer valid-token"},
            query_params={},
            body=None,
            client_ip="192.168.1.100",
            timestamp=datetime.now()
        )
        
        # Mock authentication for this test
        with patch.object(middleware, '_authenticate_request') as mock_auth:
            mock_auth.return_value = AuthResult(
                success=True,
                user_id="test_user",
                permissions=[Permission.READ]
            )
            
            allowed, error_response, auth_result = await middleware.process_request(request)
            
            # Should be allowed
            assert allowed is True
            assert error_response is None
            assert auth_result is not None
        
        # Test blacklisted IP
        blacklisted_request = ApiRequest(
            request_id="test-2",
            method="GET",
            path="/api/v1/agents",
            headers={},
            query_params={},
            body=None,
            client_ip="192.168.1.200",  # Blacklisted IP
            timestamp=datetime.now()
        )
        
        allowed, error_response, auth_result = await middleware.process_request(blacklisted_request)
        
        # Should be blocked
        assert allowed is False
        assert error_response is not None
        assert error_response.status_code == 403
        
        # Test malicious request
        malicious_request = ApiRequest(
            request_id="test-3",
            method="GET",
            path="/api/v1/agents",
            headers={},
            query_params={"q": "'; DROP TABLE users; --"},  # SQL injection
            body=None,
            client_ip="192.168.1.101",
            timestamp=datetime.now()
        )
        
        allowed, error_response, auth_result = await middleware.process_request(malicious_request)
        
        # Should be blocked
        assert allowed is False
        assert error_response is not None
        assert error_response.status_code == 400
    
    async def test_rate_limiting(self, auth_service):
        """Test rate limiting functionality."""
        middleware = EnhancedSecurityMiddleware(auth_service, {})
        
        # Create multiple requests from same IP
        requests = []
        for i in range(10):
            request = ApiRequest(
                request_id=f"test-{i}",
                method="POST",
                path="/api/v1/auth/login",
                headers={},
                query_params={},
                body='{"username": "test", "password": "test"}',
                client_ip="192.168.1.100",
                timestamp=datetime.now()
            )
            requests.append(request)
        
        # Process requests rapidly
        allowed_count = 0
        blocked_count = 0
        
        for request in requests:
            allowed, error_response, auth_result = await middleware.process_request(request)
            if allowed:
                allowed_count += 1
            else:
                blocked_count += 1
        
        # Some requests should be rate limited
        assert blocked_count > 0
        assert allowed_count > 0
        assert allowed_count + blocked_count == 10
    
    async def test_comprehensive_security_validation(self, auth_service, temp_dir):
        """Test comprehensive security validation across all components."""
        # This test validates the entire security framework working together
        
        # 1. Setup complete security environment
        config = {
            "bcrypt_rounds": 10,
            "jwt_secret": "comprehensive_test_secret_key_32_chars",
            "require_2fa": False,
            "max_failed_attempts": 3
        }
        
        # 2. Test user lifecycle
        # Create user
        success, message, user = await auth_service.create_user(
            username="comprehensive_user",
            email="comprehensive@example.com",
            password="ComprehensivePassword123!",
            roles=[UserRole.ADMIN],
            active=True
        )
        
        assert success is True
        assert user.user_id is not None
        
        # Authenticate user
        success, message, session = await auth_service.authenticate_user(
            username="comprehensive_user",
            password="ComprehensivePassword123!",
            client_ip="192.168.1.100",
            user_agent="Comprehensive Test"
        )
        
        assert success is True
        assert session.access_token is not None
        
        # 3. Test token security
        token_manager = auth_service.token_manager
        
        # Validate token
        auth_result = await token_manager.validate_token_secure(
            token=session.access_token,
            client_ip="192.168.1.100",
            required_permissions=[Permission.ADMIN]
        )
        
        assert auth_result.success is True
        assert auth_result.user_id == user.user_id
        
        # 4. Test security middleware
        middleware = EnhancedSecurityMiddleware(auth_service, {})
        
        # Test authorized request
        request = ApiRequest(
            request_id="comprehensive-test",
            method="GET",
            path="/api/v1/admin/users",
            headers={"Authorization": f"Bearer {session.access_token}"},
            query_params={},
            body=None,
            client_ip="192.168.1.100",
            timestamp=datetime.now()
        )
        
        allowed, error_response, auth_result = await middleware.process_request(request)
        
        assert allowed is True
        assert error_response is None
        assert auth_result.success is True
        
        # 5. Test quality gates with clean code
        clean_file = temp_dir / "clean_code.py"
        clean_file.write_text("""
# Clean, secure code
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def process_user_data(data: Dict[str, Any]) -> Dict[str, Any]:
    \"\"\"Process user data securely.\"\"\"
    if not isinstance(data, dict):
        raise ValueError("Invalid input data")
    
    # Sanitize and validate input
    processed_data = {}
    for key, value in data.items():
        if isinstance(value, str) and len(value) < 1000:
            processed_data[key] = value.strip()
    
    logger.info("User data processed successfully")
    return processed_data
""")
        
        # Create quality gates config
        config_file = temp_dir / "security_config.json"
        config = {
            "security_monitoring": {
                "thresholds": {"critical_threshold": 0},
                "scan_configuration": {
                    "bandit": {"enabled": True},
                    "custom_checks": {"enabled": True}
                }
            }
        }
        with open(config_file, 'w') as f:
            json.dump(config, f)
        
        quality_gates = SecurityQualityGates(str(config_file))
        results = await quality_gates.run_all_quality_gates([str(temp_dir)])
        
        # Clean code should pass security checks
        critical_issues = []
        for result in results.values():
            critical_issues.extend([issue for issue in result.issues 
                                  if issue.severity == SeverityLevel.CRITICAL])
        
        # Should have minimal or no critical issues from clean code
        assert len(critical_issues) == 0
        
        # Should be able to deploy
        can_deploy, message = await quality_gates.can_deploy(results)
        assert can_deploy is True
        
        # 6. Test session cleanup
        success, message = await auth_service.logout_user(session.access_token)
        assert success is True
        
        # Token should no longer be valid
        auth_result = await token_manager.validate_token_secure(
            token=session.access_token,
            client_ip="192.168.1.100"
        )
        
        assert auth_result.success is False
        
        print("✅ Comprehensive security validation completed successfully")
    
    async def test_zero_critical_policy_enforcement(self, quality_gates, temp_dir):
        """Test zero critical vulnerability policy enforcement."""
        # Create file with critical security issues
        critical_file = temp_dir / "critical_security_issues.py"
        critical_file.write_text("""
# Multiple critical security issues
SECRET_KEY = "hardcoded-secret-key"
DATABASE_PASSWORD = "admin123"
API_TOKEN = "sk-1234567890abcdef"

import os
import subprocess

def dangerous_function(user_input):
    # Command injection
    os.system(f"rm -rf {user_input}")
    # SQL injection
    query = f"DELETE FROM users WHERE id = {user_input}"
    return query
""")
        
        # Run quality gates
        results = await quality_gates.run_all_quality_gates([str(temp_dir)])
        
        # Should detect multiple critical issues
        critical_issues = []
        for result in results.values():
            critical_issues.extend([issue for issue in result.issues 
                                  if issue.severity == SeverityLevel.CRITICAL])
        
        assert len(critical_issues) >= 3  # At least 3 hardcoded secrets
        
        # Zero critical policy should fail
        policy_ok, violations = await quality_gates.check_zero_critical_policy(results)
        assert policy_ok is False
        assert len(violations) >= 3
        
        # Deployment should be blocked
        can_deploy, message = await quality_gates.can_deploy(results)
        assert can_deploy is False
        assert "critical" in message.lower()
    
    async def test_security_monitoring_and_alerting(self, auth_service):
        """Test security monitoring and alerting functionality."""
        middleware = EnhancedSecurityMiddleware(auth_service, {
            "alert_thresholds": {"critical": 1, "high": 3}
        })
        
        # Generate security events
        events = []
        
        # Simulate multiple failed authentication attempts
        for i in range(5):
            request = ApiRequest(
                request_id=f"failed-auth-{i}",
                method="POST",
                path="/api/v1/auth/login",
                headers={},
                query_params={},
                body='{"username": "attacker", "password": "wrong"}',
                client_ip="192.168.1.200",
                timestamp=datetime.now()
            )
            
            allowed, error_response, auth_result = await middleware.process_request(request)
            assert allowed is False  # Should be blocked
        
        # Check security dashboard
        dashboard = await middleware.get_security_dashboard()
        
        assert dashboard["recent_activity"]["total_events"] > 0
        assert dashboard["threat_intelligence"]["top_threat_ips"]
        
        # Check that threat score increased for attacking IP
        threat_ips = dict(dashboard["threat_intelligence"]["top_threat_ips"])
        assert "192.168.1.200" in threat_ips
        assert threat_ips["192.168.1.200"] > 0
    
    async def test_bcrypt_security_features(self, auth_service):
        """Test bcrypt security features."""
        # Test password hashing
        password = "TestPassword123!"
        
        # Create user to test bcrypt hashing
        success, message, user = await auth_service.create_user(
            username="bcryptuser",
            email="bcrypt@example.com",
            password=password,
            roles=[UserRole.VIEWER]
        )
        
        assert success is True
        assert user.password_hash.startswith("$2b$")  # bcrypt format
        
        # Test that same password produces different hashes (salt)
        success2, message2, user2 = await auth_service.create_user(
            username="bcryptuser2",
            email="bcrypt2@example.com",
            password=password,
            roles=[UserRole.VIEWER]
        )
        
        assert success2 is True
        assert user.password_hash != user2.password_hash  # Different salts
        
        # Test authentication with bcrypt
        success, message, session = await auth_service.authenticate_user(
            username="bcryptuser",
            password=password,
            client_ip="192.168.1.100",
            user_agent="Bcrypt Test"
        )
        
        assert success is True
        
        # Test failed authentication
        success, message, session = await auth_service.authenticate_user(
            username="bcryptuser",
            password="WrongPassword",
            client_ip="192.168.1.100",
            user_agent="Bcrypt Test"
        )
        
        assert success is False


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])