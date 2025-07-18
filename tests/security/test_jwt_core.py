#!/usr/bin/env python3
"""
JWT Core Tests

Tests for essential JWT token operations.
"""

import pytest
import asyncio
from datetime import datetime, timedelta

from security.jwt_core import JWTCore, TokenType, TokenStatus
from external_api.auth_middleware import Permission


class TestJWTCore:
    """Test suite for JWT core functionality."""
    
    @pytest.fixture
    def jwt_config(self):
        """JWT configuration."""
        return {
            "jwt_secret": "test_secret_key",
            "jwt_algorithm": "HS256",
            "token_expiry_hours": 1
        }
    
    @pytest.fixture
    def jwt_core(self, jwt_config):
        """JWT core instance."""
        return JWTCore(jwt_config)
    
    async def test_token_creation(self, jwt_core):
        """Test token creation."""
        token, token_id = await jwt_core.create_token(
            user_id="test_user",
            token_type=TokenType.ACCESS,
            permissions=[Permission.READ]
        )
        
        assert token is not None
        assert token_id is not None
        assert token_id in jwt_core.tokens
    
    async def test_token_validation(self, jwt_core):
        """Test token validation."""
        # Create token
        token, token_id = await jwt_core.create_token(
            user_id="test_user",
            token_type=TokenType.ACCESS,
            permissions=[Permission.READ, Permission.WRITE]
        )
        
        # Validate with correct permissions
        result = await jwt_core.validate_token(token, [Permission.READ])
        assert result.success is True
        assert result.user_id == "test_user"
        assert Permission.READ in result.permissions
    
    async def test_permission_check(self, jwt_core):
        """Test permission validation."""
        # Create token with READ only
        token, token_id = await jwt_core.create_token(
            user_id="test_user",
            token_type=TokenType.ACCESS,
            permissions=[Permission.READ]
        )
        
        # Should fail for WRITE permission
        result = await jwt_core.validate_token(token, [Permission.WRITE])
        assert result.success is False
        assert "insufficient permissions" in result.error.lower()
    
    async def test_token_revocation(self, jwt_core):
        """Test token revocation."""
        # Create token
        token, token_id = await jwt_core.create_token(
            user_id="test_user",
            token_type=TokenType.ACCESS,
            permissions=[Permission.READ]
        )
        
        # Revoke token
        revoked = await jwt_core.revoke_token(token_id)
        assert revoked is True
        
        # Should fail validation
        result = await jwt_core.validate_token(token)
        assert result.success is False
        assert "revoked" in result.error.lower()
    
    async def test_user_token_revocation(self, jwt_core):
        """Test revoking all user tokens."""
        # Create multiple tokens
        tokens = []
        for i in range(3):
            token, token_id = await jwt_core.create_token(
                user_id="test_user",
                token_type=TokenType.ACCESS,
                permissions=[Permission.READ]
            )
            tokens.append((token, token_id))
        
        # Revoke all except first
        revoked_count = await jwt_core.revoke_user_tokens(
            user_id="test_user",
            exclude_token_id=tokens[0][1]
        )
        
        assert revoked_count == 2
        
        # First should work, others should fail
        result = await jwt_core.validate_token(tokens[0][0])
        assert result.success is True
        
        result = await jwt_core.validate_token(tokens[1][0])
        assert result.success is False
    
    async def test_token_expiration(self, jwt_core):
        """Test token expiration."""
        # Create short-lived token
        token, token_id = await jwt_core.create_token(
            user_id="test_user",
            token_type=TokenType.ACCESS,
            permissions=[Permission.READ],
            expires_in_hours=0.0001
        )
        
        # Should work initially
        result = await jwt_core.validate_token(token)
        assert result.success is True
        
        # Wait for expiration
        await asyncio.sleep(0.5)
        
        # Should fail after expiration
        result = await jwt_core.validate_token(token)
        assert result.success is False
        assert "expired" in result.error.lower()
    
    async def test_invalid_tokens(self, jwt_core):
        """Test invalid token handling."""
        # Invalid token
        result = await jwt_core.validate_token("invalid")
        assert result.success is False
        
        # Malformed JWT
        result = await jwt_core.validate_token("header.payload.signature")
        assert result.success is False
    
    async def test_token_counting(self, jwt_core):
        """Test token counting."""
        # Create tokens
        await jwt_core.create_token("user1", TokenType.ACCESS, [Permission.READ])
        await jwt_core.create_token("user2", TokenType.ACCESS, [Permission.READ])
        
        # Check counts
        total_count = jwt_core.get_active_count()
        assert total_count == 2
        
        user_count = jwt_core.get_active_count("user1")
        assert user_count == 1
    
    async def test_cleanup_expired(self, jwt_core):
        """Test expired token cleanup."""
        # Create expired token
        token, token_id = await jwt_core.create_token(
            user_id="test_user",
            token_type=TokenType.ACCESS,
            permissions=[Permission.READ],
            expires_in_hours=0.0001
        )
        
        # Wait for expiration
        await asyncio.sleep(0.5)
        
        # Cleanup
        expired_count = jwt_core.cleanup_expired()
        assert expired_count == 1
        
        # Token should be expired
        token_data = jwt_core.tokens[token_id]
        assert token_data.status == TokenStatus.EXPIRED