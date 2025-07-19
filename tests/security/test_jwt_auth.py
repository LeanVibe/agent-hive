#!/usr/bin/env python3
"""
Comprehensive tests for JWT Authentication Integration

Tests cover JWT token generation, validation, refresh, integration
with API Gateway, and security features.
"""

import asyncio
import pytest
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any

import jwt
from jwt.exceptions import ExpiredSignatureError

from config.auth_models import Permission, AuthResult
from security.auth_service import AuthenticationService, UserRole
from security.token_manager import SecureTokenManager, TokenType, TokenStatus
from external_api.jwt_integration import JwtIntegrationService, JwtValidationResult
from external_api.api_gateway import ApiGateway
from external_api.models import ApiRequest, ApiResponse


class TestJWTIntegration:
    """Test JWT integration functionality."""
    
    @pytest.fixture
    def config(self):
        """Test configuration."""
        return {
            "jwt_secret": "test-secret-key-for-jwt-testing",
            "jwt_algorithm": "HS256",
            "token_expiry_minutes": 15,
            "rate_limit_requests_per_hour": 1000,
            "require_https": False,  # Disabled for testing
            "auto_refresh_threshold_hours": 1,
            "protected_endpoints": ["/api/v1/agents", "/api/v1/tasks"],
            "public_endpoints": ["/health", "/metrics", "/api/v1/auth"],
            "max_tokens_per_user": 10,
            "suspicious_activity_threshold": 100,
            "bcrypt_rounds": 4  # Lower for faster tests
        }
    
    @pytest.fixture
    async def jwt_service(self, config):
        """JWT integration service instance."""
        return JwtIntegrationService(config)
    
    @pytest.fixture
    async def api_gateway(self, config):
        """API Gateway instance."""
        gateway_config = {
            "gateway": {
                "host": "localhost",
                "port": 8081,
                "auth_required": True
            },
            "jwt": config,
            "auth": config
        }
        return ApiGateway(gateway_config)
    
    @pytest.fixture
    async def test_user(self, jwt_service):
        """Create test user."""
        auth_service = jwt_service.auth_service
        success, message, user = await auth_service.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPassword123!",
            roles=[UserRole.DEVELOPER]
        )
        assert success
        return user
    
    @pytest.fixture
    def sample_request(self):
        """Sample API request."""
        return ApiRequest(
            method="GET",
            path="/api/v1/agents",
            headers={"User-Agent": "Test-Client/1.0"},
            query_params={},
            body=None,
            timestamp=datetime.utcnow(),
            request_id=str(uuid.uuid4()),
            client_ip="127.0.0.1"
        )


class TestTokenGeneration(TestJWTIntegration):
    """Test JWT token generation."""
    
    async def test_create_token_pair(self, jwt_service):
        """Test creating access and refresh token pair."""
        token_manager = jwt_service.token_manager
        
        # Create token pair
        access_token, access_id, refresh_token, refresh_id = await token_manager.create_token_pair(
            user_id="test-user-123",
            permissions=[Permission.READ, Permission.WRITE]
        )
        
        # Verify tokens are different
        assert access_token != refresh_token
        assert access_id != refresh_id
        
        # Verify access token payload
        access_payload = jwt.decode(access_token, jwt_service.config["jwt_secret"], algorithms=["HS256"])
        assert access_payload["user_id"] == "test-user-123"
        assert access_payload["token_type"] == "access"
        assert "read" in access_payload["permissions"]
        assert "write" in access_payload["permissions"]
        
        # Verify refresh token payload
        refresh_payload = jwt.decode(refresh_token, jwt_service.config["jwt_secret"], algorithms=["HS256"])
        assert refresh_payload["user_id"] == "test-user-123"
        assert refresh_payload["token_type"] == "refresh"
    
    async def test_token_expiration(self, jwt_service):
        """Test token expiration handling."""
        token_manager = jwt_service.token_manager
        
        # Create short-lived token
        token, token_id = await token_manager.create_secure_token(
            user_id="test-user",
            token_type=TokenType.ACCESS,
            permissions=[Permission.READ],
            expires_in_hours=0.001  # 3.6 seconds
        )
        
        # Token should be valid initially
        result = await token_manager.validate_token_secure(token)
        assert result.success
        
        # Wait for expiration
        await asyncio.sleep(4)
        
        # Token should be expired
        result = await token_manager.validate_token_secure(token)
        assert not result.success
        assert "expired" in result.error.lower()


class TestTokenValidation(TestJWTIntegration):
    """Test JWT token validation."""
    
    async def test_valid_token_validation(self, jwt_service, test_user, sample_request):
        """Test validation of valid JWT token."""
        # Create session for user
        auth_service = jwt_service.auth_service
        success, message, session = await auth_service.authenticate_user(
            username="testuser",
            password="TestPassword123!",
            client_ip=sample_request.client_ip,
            user_agent="Test-Client"
        )
        assert success
        
        # Add token to request
        sample_request.headers["Authorization"] = f"Bearer {session.access_token}"
        
        # Validate request
        auth_success, metadata, error = await jwt_service.authenticate_request(
            request=sample_request,
            required_permissions=[Permission.READ]
        )
        
        assert auth_success
        assert metadata.validation_result == JwtValidationResult.VALID
        assert metadata.user_id == test_user.user_id
        assert Permission.READ in metadata.permissions
    
    async def test_invalid_token_validation(self, jwt_service, sample_request):
        """Test validation of invalid JWT token."""
        # Add invalid token to request
        sample_request.headers["Authorization"] = "Bearer invalid-token-string"
        
        # Validate request
        auth_success, metadata, error = await jwt_service.authenticate_request(
            request=sample_request
        )
        
        assert not auth_success
        assert metadata.validation_result == JwtValidationResult.INVALID
        assert error.status_code == 401
    
    async def test_missing_token_validation(self, jwt_service, sample_request):
        """Test validation when no token is provided."""
        # Don't add any token to request
        
        # Validate request
        auth_success, metadata, error = await jwt_service.authenticate_request(
            request=sample_request
        )
        
        assert not auth_success
        assert metadata.validation_result == JwtValidationResult.INVALID
        assert "missing_token" in metadata.security_flags
    
    async def test_insufficient_permissions(self, jwt_service, test_user, sample_request):
        """Test validation with insufficient permissions."""
        # Create user with limited permissions
        auth_service = jwt_service.auth_service
        limited_user_success, _, limited_user = await auth_service.create_user(
            username="limiteduser",
            email="limited@example.com",
            password="TestPassword123!",
            roles=[UserRole.VIEWER]  # Only read permissions
        )
        assert limited_user_success
        
        # Authenticate limited user
        success, message, session = await auth_service.authenticate_user(
            username="limiteduser",
            password="TestPassword123!",
            client_ip=sample_request.client_ip,
            user_agent="Test-Client"
        )
        assert success
        
        # Add token to request
        sample_request.headers["Authorization"] = f"Bearer {session.access_token}"
        
        # Try to access endpoint requiring admin permissions
        auth_success, metadata, error = await jwt_service.authenticate_request(
            request=sample_request,
            required_permissions=[Permission.ADMIN]
        )
        
        assert not auth_success
        assert metadata.validation_result == JwtValidationResult.INSUFFICIENT_PERMISSIONS
        assert error.status_code == 403


class TestTokenRefresh(TestJWTIntegration):
    """Test JWT token refresh functionality."""
    
    async def test_successful_token_refresh(self, jwt_service, test_user):
        """Test successful token refresh."""
        # Authenticate user to get tokens
        auth_service = jwt_service.auth_service
        success, message, session = await auth_service.authenticate_user(
            username="testuser",
            password="TestPassword123!",
            client_ip="127.0.0.1",
            user_agent="Test-Client"
        )
        assert success
        
        # Refresh token
        refresh_success, new_access_token, new_refresh_token = await jwt_service.refresh_token(
            refresh_token=session.refresh_token,
            client_ip="127.0.0.1"
        )
        
        assert refresh_success
        assert new_access_token is not None
        assert new_refresh_token is not None
        assert new_access_token != session.access_token
    
    async def test_refresh_with_invalid_token(self, jwt_service):
        """Test refresh with invalid refresh token."""
        refresh_success, new_access_token, new_refresh_token = await jwt_service.refresh_token(
            refresh_token="invalid-refresh-token",
            client_ip="127.0.0.1"
        )
        
        assert not refresh_success
        assert new_access_token is None
        assert new_refresh_token is None
    
    async def test_refresh_with_access_token(self, jwt_service, test_user):
        """Test that access tokens cannot be used for refresh."""
        # Authenticate user
        auth_service = jwt_service.auth_service
        success, message, session = await auth_service.authenticate_user(
            username="testuser",
            password="TestPassword123!",
            client_ip="127.0.0.1",
            user_agent="Test-Client"
        )
        assert success
        
        # Try to refresh using access token (should fail)
        refresh_success, new_access_token, new_refresh_token = await jwt_service.refresh_token(
            refresh_token=session.access_token,  # Using access token instead of refresh token
            client_ip="127.0.0.1"
        )
        
        assert not refresh_success


class TestAPIGatewayIntegration(TestJWTIntegration):
    """Test API Gateway JWT integration."""
    
    async def test_gateway_authentication_success(self, api_gateway, test_user, sample_request):
        """Test successful authentication through API Gateway."""
        # Authenticate user through gateway
        auth_response = await api_gateway.authenticate_user(
            username="testuser",
            password="TestPassword123!",
            client_ip=sample_request.client_ip
        )
        
        assert auth_response.status_code == 200
        assert "access_token" in auth_response.body
        assert "refresh_token" in auth_response.body
        
        # Use token in request
        access_token = auth_response.body["access_token"]
        sample_request.headers["Authorization"] = f"Bearer {access_token}"
        
        # Process request through gateway
        response = await api_gateway.process_request(sample_request)
        
        # Should succeed for protected endpoint (no specific handler, but auth should pass)
        assert response.status_code != 401  # Not unauthorized
    
    async def test_gateway_authentication_failure(self, api_gateway, sample_request):
        """Test authentication failure through API Gateway."""
        # Try to authenticate with wrong credentials
        auth_response = await api_gateway.authenticate_user(
            username="nonexistent",
            password="wrongpassword",
            client_ip=sample_request.client_ip
        )
        
        assert auth_response.status_code == 401
        assert "error" in auth_response.body
    
    async def test_gateway_token_refresh(self, api_gateway, test_user, sample_request):
        """Test token refresh through API Gateway."""
        # First authenticate
        auth_response = await api_gateway.authenticate_user(
            username="testuser",
            password="TestPassword123!",
            client_ip=sample_request.client_ip
        )
        assert auth_response.status_code == 200
        
        # Refresh token
        refresh_token = auth_response.body["refresh_token"]
        refresh_response = await api_gateway.refresh_user_token(
            refresh_token=refresh_token,
            client_ip=sample_request.client_ip
        )
        
        assert refresh_response.status_code == 200
        assert "access_token" in refresh_response.body
        assert "refresh_token" in refresh_response.body
    
    async def test_gateway_logout(self, api_gateway, test_user, sample_request):
        """Test user logout through API Gateway."""
        # First authenticate
        auth_response = await api_gateway.authenticate_user(
            username="testuser",
            password="TestPassword123!",
            client_ip=sample_request.client_ip
        )
        assert auth_response.status_code == 200
        
        # Logout
        access_token = auth_response.body["access_token"]
        logout_response = await api_gateway.logout_user(access_token)
        
        assert logout_response.status_code == 200
        assert logout_response.body["message"] == "Logout successful"


class TestSecurityFeatures(TestJWTIntegration):
    """Test security features of JWT authentication."""
    
    async def test_rate_limiting(self, jwt_service, sample_request):
        """Test rate limiting functionality."""
        # Configure low rate limit for testing
        jwt_service.rate_limit_requests = 2
        jwt_service.rate_limit_window = 60
        
        # First request should succeed
        auth_success1, metadata1, error1 = await jwt_service.authenticate_request(sample_request)
        
        # Second request should succeed
        sample_request.request_id = str(uuid.uuid4())  # New request ID
        auth_success2, metadata2, error2 = await jwt_service.authenticate_request(sample_request)
        
        # Third request should be rate limited
        sample_request.request_id = str(uuid.uuid4())  # New request ID
        auth_success3, metadata3, error3 = await jwt_service.authenticate_request(sample_request)
        
        # One of the requests should be rate limited
        assert not auth_success3
        assert metadata3.validation_result == JwtValidationResult.RATE_LIMITED
    
    async def test_suspicious_activity_detection(self, jwt_service, sample_request):
        """Test suspicious activity detection."""
        # Configure low threshold for testing
        jwt_service.suspicious_threshold = 2
        
        # Simulate rapid requests from same IP
        for i in range(3):
            sample_request.request_id = str(uuid.uuid4())
            sample_request.timestamp = datetime.utcnow()
            await jwt_service.authenticate_request(sample_request)
        
        # Check that suspicious activity was detected
        stats = await jwt_service.get_authentication_stats()
        events = jwt_service.security_events
        suspicious_events = [e for e in events if e.get("event_type") == "suspicious_activity_detected"]
        
        assert len(suspicious_events) > 0
    
    async def test_public_endpoint_access(self, jwt_service):
        """Test that public endpoints don't require authentication."""
        public_request = ApiRequest(
            method="GET",
            path="/health",  # Public endpoint
            headers={},
            query_params={},
            body=None,
            timestamp=datetime.utcnow(),
            request_id=str(uuid.uuid4()),
            client_ip="127.0.0.1"
        )
        
        auth_success, metadata, error = await jwt_service.authenticate_request(public_request)
        
        assert auth_success
        assert "public_endpoint" in metadata.security_flags
    
    async def test_token_revocation(self, jwt_service, test_user):
        """Test token revocation functionality."""
        # Authenticate user
        auth_service = jwt_service.auth_service
        success, message, session = await auth_service.authenticate_user(
            username="testuser",
            password="TestPassword123!",
            client_ip="127.0.0.1",
            user_agent="Test-Client"
        )
        assert success
        
        # Verify token is valid
        token_manager = jwt_service.token_manager
        result = await token_manager.validate_token_secure(session.access_token)
        assert result.success
        
        # Revoke token
        revoke_success = await jwt_service.revoke_token(session.access_token, "test_revocation")
        assert revoke_success
        
        # Verify token is no longer valid
        result = await token_manager.validate_token_secure(session.access_token)
        assert not result.success


class TestTokenHealth(TestJWTIntegration):
    """Test token health checking functionality."""
    
    async def test_healthy_token_check(self, jwt_service):
        """Test health check of healthy token."""
        token_manager = jwt_service.token_manager
        
        # Create fresh token
        token, token_id = await token_manager.create_secure_token(
            user_id="test-user",
            token_type=TokenType.ACCESS,
            permissions=[Permission.READ]
        )
        
        # Check token health
        health = await token_manager.check_token_health(token)
        
        assert health["healthy"]
        assert health["token_id"] == token_id
        assert health["age_hours"] < 1
        assert health["usage_count"] == 0
        assert len(health["warnings"]) == 0
    
    async def test_expired_token_health(self, jwt_service):
        """Test health check of expired token."""
        token_manager = jwt_service.token_manager
        
        # Create token that expires quickly
        token, token_id = await token_manager.create_secure_token(
            user_id="test-user",
            token_type=TokenType.ACCESS,
            permissions=[Permission.READ],
            expires_in_hours=0.001  # 3.6 seconds
        )
        
        # Wait for expiration
        await asyncio.sleep(4)
        
        # Check token health
        health = await token_manager.check_token_health(token)
        
        assert not health["healthy"]
        assert "expired" in health["error"].lower()
        assert "refresh token immediately" in health["recommendations"]


class TestErrorHandling(TestJWTIntegration):
    """Test error handling in JWT authentication."""
    
    async def test_malformed_token(self, jwt_service, sample_request):
        """Test handling of malformed JWT tokens."""
        # Add malformed token
        sample_request.headers["Authorization"] = "Bearer not.a.valid.jwt.token"
        
        auth_success, metadata, error = await jwt_service.authenticate_request(sample_request)
        
        assert not auth_success
        assert metadata.validation_result == JwtValidationResult.INVALID
        assert error.status_code == 401
    
    async def test_token_with_wrong_secret(self, jwt_service, sample_request):
        """Test token signed with wrong secret."""
        # Create token with different secret
        wrong_secret_token = jwt.encode(
            {
                "user_id": "test-user",
                "token_id": str(uuid.uuid4()),
                "permissions": ["read"],
                "exp": datetime.utcnow() + timedelta(hours=1),
                "iat": datetime.utcnow()
            },
            "wrong-secret",
            algorithm="HS256"
        )
        
        sample_request.headers["Authorization"] = f"Bearer {wrong_secret_token}"
        
        auth_success, metadata, error = await jwt_service.authenticate_request(sample_request)
        
        assert not auth_success
        assert metadata.validation_result == JwtValidationResult.INVALID


@pytest.mark.asyncio
async def test_full_authentication_flow():
    """Test complete authentication flow from user creation to API access."""
    config = {
        "jwt_secret": "test-secret-key",
        "jwt_algorithm": "HS256",
        "token_expiry_minutes": 15,
        "bcrypt_rounds": 4
    }
    
    # Initialize services
    jwt_service = JwtIntegrationService(config)
    auth_service = jwt_service.auth_service
    
    # Create user
    success, message, user = await auth_service.create_user(
        username="flowtest",
        email="flow@example.com",
        password="FlowTestPassword123!",
        roles=[UserRole.DEVELOPER]
    )
    assert success
    
    # Authenticate user
    success, message, session = await auth_service.authenticate_user(
        username="flowtest",
        password="FlowTestPassword123!",
        client_ip="127.0.0.1",
        user_agent="Test-Client"
    )
    assert success
    assert session is not None
    
    # Create API request with token
    request = ApiRequest(
        method="GET",
        path="/api/v1/agents",
        headers={"Authorization": f"Bearer {session.access_token}"},
        query_params={},
        body=None,
        timestamp=datetime.utcnow(),
        request_id=str(uuid.uuid4()),
        client_ip="127.0.0.1"
    )
    
    # Validate request
    auth_success, metadata, error = await jwt_service.authenticate_request(
        request=request,
        required_permissions=[Permission.READ]
    )
    
    assert auth_success
    assert metadata.validation_result == JwtValidationResult.VALID
    assert metadata.user_id == user.user_id
    
    # Refresh token
    refresh_success, new_access_token, new_refresh_token = await jwt_service.refresh_token(
        refresh_token=session.refresh_token,
        client_ip="127.0.0.1"
    )
    
    assert refresh_success
    assert new_access_token != session.access_token
    
    # Revoke old token
    revoke_success = await jwt_service.revoke_token(session.access_token)
    assert revoke_success
    
    # Verify old token is invalid
    old_token_request = request
    old_token_request.headers["Authorization"] = f"Bearer {session.access_token}"
    auth_success, metadata, error = await jwt_service.authenticate_request(old_token_request)
    assert not auth_success