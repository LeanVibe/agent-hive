#!/usr/bin/env python3
"""
Comprehensive Security Tests for JWT Authentication System

Tests the complete integration of JWT authentication, bcrypt password hashing,
security middleware, and API gateway security features.
"""

import pytest
import asyncio
import time
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

# Import the security components
from external_api.auth_middleware import (
    AuthenticationMiddleware, 
    AuthMethod, 
    Permission, 
    AuthResult
)
from external_api.api_gateway import ApiGateway
from external_api.models import ApiRequest, ApiGatewayConfig
from config.security_config import SecurityConfigManager, SecurityLevel, PasswordConfig
from security.security_manager import SecurityManager, RiskLevel


class TestJWTSecuritySystem:
    """Test suite for JWT authentication and security features."""
    
    @pytest.fixture
    def security_config(self):
        """Create test security configuration."""
        return {
            "enabled_methods": [AuthMethod.JWT, AuthMethod.API_KEY, AuthMethod.BASIC],
            "jwt_secret": "test_secret_key_32_characters_long",
            "jwt_algorithm": "HS256",
            "token_expiry_hours": 24,
            "max_auth_attempts": 5,
            "auth_window_minutes": 15,
            "bcrypt_rounds": 12,
            "password_config": {
                "min_length": 12,
                "require_uppercase": True,
                "require_lowercase": True,
                "require_numbers": True,
                "require_special_chars": True,
                "lockout_attempts": 5,
                "lockout_duration_minutes": 30,
                "password_history_count": 5
            }
        }
    
    @pytest.fixture
    def auth_middleware(self, security_config):
        """Create authentication middleware instance."""
        return AuthenticationMiddleware(security_config)
    
    @pytest.fixture
    def api_gateway_config(self):
        """Create API gateway configuration."""
        return ApiGatewayConfig(
            host="localhost",
            port=8080,
            api_prefix="/api/v1",
            auth_required=True,
            rate_limit_requests=100,
            rate_limit_window=60,
            request_timeout=30,
            enable_cors=True,
            cors_origins=["*"],
            api_key_header="X-API-Key"
        )
    
    @pytest.fixture
    def api_gateway(self, api_gateway_config, auth_middleware):
        """Create API gateway with auth middleware."""
        return ApiGateway(api_gateway_config, auth_middleware=auth_middleware)
    
    @pytest.fixture
    def security_manager(self):
        """Create security manager instance."""
        config = {
            'enabled': True,
            'command_validator': {'enabled': True},
            'input_sanitizer': {'enabled': True, 'strict_mode': True}
        }
        return SecurityManager(config)

    async def test_jwt_token_creation_and_validation(self, auth_middleware):
        """Test JWT token creation and validation."""
        user_id = "test_user"
        permissions = [Permission.READ, Permission.WRITE]
        
        # Create JWT token
        token = auth_middleware.create_jwt_token(user_id, permissions, expires_in_hours=1)
        assert token is not None
        assert isinstance(token, str)
        
        # Validate token by decoding
        payload = await auth_middleware._decode_jwt(token)
        assert payload["user_id"] == user_id
        assert Permission.READ.value in payload["permissions"]
        assert Permission.WRITE.value in payload["permissions"]
        
        # Check token expiration
        assert "exp" in payload
        assert "iat" in payload
        assert "jti" in payload

    async def test_rbac_jwt_token_creation(self, auth_middleware):
        """Test RBAC JWT token creation with role information."""
        user_id = "admin_user"
        roles = ["admin", "developer"]
        permissions = [Permission.ADMIN, Permission.EXECUTE]
        user_metadata = {"department": "engineering", "level": "senior"}
        
        # Create RBAC JWT token
        token = auth_middleware.create_rbac_jwt_token(
            user_id=user_id,
            roles=roles,
            permissions=permissions,
            user_metadata=user_metadata,
            expires_in_hours=2
        )
        
        assert token is not None
        
        # Extract RBAC information
        rbac_info = auth_middleware.extract_rbac_info_from_token(token)
        assert rbac_info is not None
        assert rbac_info["user_id"] == user_id
        assert rbac_info["roles"] == roles
        assert rbac_info["user_metadata"] == user_metadata
        assert rbac_info["token_type"] == "access"
        assert "rbac" in rbac_info

    async def test_jwt_token_blacklisting(self, auth_middleware):
        """Test JWT token blacklisting functionality."""
        user_id = "test_user"
        permissions = [Permission.READ]
        
        # Create token
        token = auth_middleware.create_jwt_token(user_id, permissions)
        
        # Verify token is valid initially
        payload = await auth_middleware._decode_jwt(token)
        assert payload["user_id"] == user_id
        
        # Blacklist token
        success = auth_middleware.blacklist_jwt_token(token)
        assert success is True
        
        # Verify blacklisted token is rejected
        mock_request = Mock()
        mock_request.headers = {"Authorization": f"Bearer {token}"}
        
        auth_result = await auth_middleware._authenticate_jwt(mock_request)
        assert auth_result.success is False
        assert "blacklisted" in auth_result.error

    async def test_jwt_token_refresh(self, auth_middleware):
        """Test JWT token refresh functionality."""
        user_id = "test_user"
        permissions = [Permission.READ, Permission.WRITE]
        
        # Create initial token
        old_token = auth_middleware.create_jwt_token(user_id, permissions)
        
        # Refresh token
        new_token = auth_middleware.refresh_jwt_token(old_token)
        assert new_token is not None
        assert new_token != old_token
        
        # Verify old token is blacklisted
        assert auth_middleware.jwt_tokens[old_token]["blacklisted"] is True
        
        # Verify new token is valid
        payload = await auth_middleware._decode_jwt(new_token)
        assert payload["user_id"] == user_id

    async def test_bcrypt_password_hashing(self, auth_middleware):
        """Test bcrypt password hashing and verification."""
        password = "SecurePassword123!"
        
        # Hash password
        hashed = auth_middleware.hash_password(password)
        assert hashed is not None
        assert hashed != password
        assert hashed.startswith("$2b$")  # bcrypt format
        
        # Verify correct password
        assert auth_middleware.verify_password(password, hashed) is True
        
        # Verify incorrect password
        assert auth_middleware.verify_password("WrongPassword", hashed) is False

    async def test_password_policy_validation(self, auth_middleware):
        """Test password policy validation."""
        # Test valid password
        valid_password = "SecurePass123!"
        is_valid, issues = auth_middleware.validate_password_policy(valid_password)
        assert is_valid is True
        assert len(issues) == 0
        
        # Test weak passwords
        weak_passwords = [
            "short",  # Too short
            "nouppercase123!",  # No uppercase
            "NOLOWERCASE123!",  # No lowercase
            "NoNumbers!",  # No numbers
            "NoSpecialChars123",  # No special characters
            "Password123!",  # Contains "password"
        ]
        
        for weak_pass in weak_passwords:
            is_valid, issues = auth_middleware.validate_password_policy(weak_pass)
            assert is_valid is False
            assert len(issues) > 0

    async def test_account_lockout_mechanism(self, auth_middleware):
        """Test account lockout after failed login attempts."""
        username = "test_user"
        correct_password = "SecurePassword123!"
        wrong_password = "WrongPassword"
        
        # Create user
        success, issues = auth_middleware.create_basic_auth_user(
            username, correct_password, [Permission.READ]
        )
        assert success is True
        
        # Simulate failed login attempts
        for i in range(5):
            mock_request = Mock()
            mock_request.headers = {
                "Authorization": f"Basic {self._encode_basic_auth(username, wrong_password)}"
            }
            
            result = await auth_middleware._authenticate_basic(mock_request)
            assert result.success is False
        
        # Account should now be locked
        assert auth_middleware.is_account_locked(username) is True
        
        # Even correct password should fail while locked
        mock_request = Mock()
        mock_request.headers = {
            "Authorization": f"Basic {self._encode_basic_auth(username, correct_password)}"
        }
        
        result = await auth_middleware._authenticate_basic(mock_request)
        assert result.success is False
        assert "locked" in result.error.lower()

    def _encode_basic_auth(self, username: str, password: str) -> str:
        """Helper to encode basic auth credentials."""
        import base64
        credentials = f"{username}:{password}"
        return base64.b64encode(credentials.encode()).decode()

    async def test_password_history_tracking(self, auth_middleware):
        """Test password history tracking and reuse prevention."""
        username = "test_user"
        password1 = "FirstPassword123!"
        password2 = "SecondPassword456!"
        
        # Create user with first password
        success, issues = auth_middleware.create_basic_auth_user(
            username, password1, [Permission.READ]
        )
        assert success is True
        
        # Try to reuse first password - should fail
        success, issues = auth_middleware.create_basic_auth_user(
            username, password1, [Permission.READ]
        )
        assert success is False
        assert any("recently" in issue for issue in issues)
        
        # Use different password - should succeed
        success, issues = auth_middleware.create_basic_auth_user(
            username, password2, [Permission.READ]
        )
        assert success is True

    async def test_secure_api_key_generation(self, auth_middleware):
        """Test secure API key generation with advanced features."""
        user_id = "test_user"
        permissions = [Permission.READ, Permission.WRITE]
        description = "Test API key"
        rate_limit = 60  # 60 requests per minute
        ip_whitelist = ["192.168.1.100", "10.0.0.50"]
        
        # Create secure API key
        api_key = auth_middleware.create_secure_api_key(
            user_id=user_id,
            permissions=permissions,
            description=description,
            rate_limit=rate_limit,
            ip_whitelist=ip_whitelist,
            expires_in_hours=24
        )
        
        assert api_key is not None
        assert api_key.startswith("ahk_")  # Correct prefix
        assert len(api_key) > 32  # Sufficient length
        
        # Verify key data
        key_data = auth_middleware.api_keys[api_key]
        assert key_data["user_id"] == user_id
        assert key_data["description"] == description
        assert key_data["rate_limit"] == rate_limit
        assert key_data["ip_whitelist"] == ip_whitelist
        assert key_data["security_features"]["secure_generation"] is True

    async def test_api_key_ip_whitelisting(self, auth_middleware):
        """Test API key IP whitelisting functionality."""
        user_id = "test_user"
        permissions = [Permission.READ]
        ip_whitelist = ["192.168.1.100"]
        
        # Create API key with IP whitelist
        api_key = auth_middleware.create_secure_api_key(
            user_id=user_id,
            permissions=permissions,
            ip_whitelist=ip_whitelist
        )
        
        # Test with whitelisted IP
        is_valid, message = auth_middleware.validate_api_key_security(
            api_key, client_ip="192.168.1.100"
        )
        assert is_valid is True
        
        # Test with non-whitelisted IP
        is_valid, message = auth_middleware.validate_api_key_security(
            api_key, client_ip="192.168.1.200"
        )
        assert is_valid is False
        assert "not authorized" in message

    async def test_api_gateway_authentication_integration(self, api_gateway, auth_middleware):
        """Test API gateway authentication integration."""
        # Create test user and API key
        user_id = "gateway_test_user"
        permissions = [Permission.READ, Permission.WRITE]
        
        # Create JWT token
        jwt_token = auth_middleware.create_jwt_token(user_id, permissions)
        
        # Create test request with JWT token
        request = ApiRequest(
            request_id=str(uuid.uuid4()),
            method="GET",
            path="/api/v1/agents",
            headers={"Authorization": f"Bearer {jwt_token}"},
            query_params={},
            body=None,
            client_ip="192.168.1.100",
            timestamp=datetime.now()
        )
        
        # Test authentication through gateway
        auth_result = await api_gateway._authenticate_request(request)
        assert auth_result["success"] is True
        assert auth_result["user_id"] == user_id

    async def test_security_headers_in_responses(self, api_gateway):
        """Test security headers are properly added to responses."""
        security_headers = api_gateway._get_security_headers()
        
        # Verify all expected security headers are present
        expected_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options", 
            "X-XSS-Protection",
            "Strict-Transport-Security",
            "Content-Security-Policy",
            "Referrer-Policy"
        ]
        
        for header in expected_headers:
            assert header in security_headers
            assert security_headers[header] is not None

    async def test_protected_path_authentication(self, api_gateway):
        """Test that protected paths require authentication."""
        protected_paths = [
            "/api/v1/agents",
            "/api/v1/orchestration",
            "/api/v1/admin",
            "/api/v1/configuration"
        ]
        
        for path in protected_paths:
            assert api_gateway._requires_authentication(path) is True
        
        # Test non-protected paths
        non_protected_paths = [
            "/api/v1/health",
            "/api/v1/status",
            "/api/v1/metrics"
        ]
        
        for path in non_protected_paths:
            assert api_gateway._requires_authentication(path) is False

    async def test_token_cleanup_mechanism(self, auth_middleware):
        """Test automatic token cleanup."""
        user_id = "cleanup_test_user"
        permissions = [Permission.READ]
        
        # Create expired token (simulate by creating and blacklisting)
        token1 = auth_middleware.create_jwt_token(user_id, permissions)
        auth_middleware.blacklist_jwt_token(token1)
        
        # Simulate old blacklisted token
        auth_middleware.jwt_tokens[token1]["created_at"] = (
            datetime.now() - timedelta(days=2)
        ).isoformat()
        
        # Create valid token
        token2 = auth_middleware.create_jwt_token(user_id, permissions)
        
        # Run cleanup
        cleaned_count = auth_middleware.cleanup_expired_tokens()
        
        # Old blacklisted token should be removed, valid token should remain
        assert token1 not in auth_middleware.jwt_tokens
        assert token2 in auth_middleware.jwt_tokens
        assert cleaned_count >= 1

    async def test_comprehensive_security_validation(self, security_manager):
        """Test comprehensive security validation."""
        agent_id = "test_agent"
        session_id = "test_session"
        user_id = "test_user"
        
        # Test safe command
        is_valid, reason, risk_level = security_manager.validate_operation(
            "ls -la", agent_id, session_id, user_id
        )
        assert is_valid is True
        assert risk_level == RiskLevel.LOW
        
        # Test dangerous command
        is_valid, reason, risk_level = security_manager.validate_operation(
            "rm -rf /", agent_id, session_id, user_id
        )
        assert is_valid is False
        assert risk_level == RiskLevel.CRITICAL
        
        # Test input sanitization
        malicious_input = "<script>alert('xss')</script>"
        sanitized = security_manager.sanitize_input(malicious_input, "html")
        assert "<script>" not in sanitized
        assert "alert" not in sanitized

    async def test_auth_statistics_and_monitoring(self, auth_middleware):
        """Test authentication statistics and monitoring."""
        # Create some test data
        user_id = "stats_test_user"
        permissions = [Permission.READ]
        
        # Create API key
        api_key = auth_middleware.create_api_key(user_id, permissions)
        
        # Create JWT token
        jwt_token = auth_middleware.create_jwt_token(user_id, permissions)
        
        # Create basic auth user
        auth_middleware.create_basic_auth_user("stats_user", "SecurePass123!", permissions)
        
        # Get statistics
        stats = auth_middleware.get_auth_stats()
        
        # Verify statistics
        assert stats["total_api_keys"] >= 1
        assert stats["active_api_keys"] >= 1
        assert stats["total_jwt_tokens"] >= 1
        assert stats["basic_auth_users"] >= 1
        assert stats["security_features"]["auto_cleanup_enabled"] is True
        assert stats["security_features"]["rate_limiting_enabled"] is True
        assert stats["security_features"]["rbac_support"] is True

    async def test_security_config_validation(self):
        """Test security configuration validation."""
        config_manager = SecurityConfigManager(SecurityLevel.PRODUCTION)
        
        # Test configuration validation
        validation_result = config_manager.validate_config()
        
        # Check that validation provides meaningful feedback
        assert "valid" in validation_result
        assert "issues" in validation_result
        assert "config" in validation_result
        
        # Test password validation
        strong_password = "VerySecurePassword123!"
        password_result = config_manager.validate_password(strong_password)
        assert password_result["valid"] is True
        assert password_result["strength_score"] > 70

    async def test_concurrent_authentication_performance(self, auth_middleware):
        """Test authentication performance under concurrent load."""
        user_id = "perf_test_user"
        permissions = [Permission.READ]
        
        # Create JWT token for testing
        jwt_token = auth_middleware.create_jwt_token(user_id, permissions)
        
        async def authenticate_request():
            mock_request = Mock()
            mock_request.headers = {"Authorization": f"Bearer {jwt_token}"}
            mock_request.client_ip = "192.168.1.100"
            
            return await auth_middleware._authenticate_jwt(mock_request)
        
        # Run concurrent authentication requests
        start_time = time.time()
        tasks = [authenticate_request() for _ in range(100)]
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # Verify all requests succeeded
        for result in results:
            assert result.success is True
            assert result.user_id == user_id
        
        # Verify reasonable performance (should complete in under 2 seconds)
        total_time = end_time - start_time
        assert total_time < 2.0
        
        print(f"100 concurrent authentications completed in {total_time:.3f}s")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])