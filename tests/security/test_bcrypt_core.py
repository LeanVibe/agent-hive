#!/usr/bin/env python3
"""
bcrypt Core Tests

Tests for essential bcrypt functionality.
"""

import pytest
from datetime import datetime, timedelta

from security.bcrypt_core import BcryptCore, UserRole, User
from external_api.auth_middleware import Permission


class TestBcryptCore:
    """Test suite for bcrypt core functionality."""
    
    @pytest.fixture
    def bcrypt_config(self):
        """bcrypt configuration."""
        return {
            "bcrypt_rounds": 10,  # Lower for testing
            "max_failed_attempts": 3,
            "lockout_minutes": 5
        }
    
    @pytest.fixture
    def bcrypt_core(self, bcrypt_config):
        """bcrypt core instance."""
        return BcryptCore(bcrypt_config)
    
    async def test_user_creation(self, bcrypt_core):
        """Test user creation with bcrypt."""
        success, message, user = await bcrypt_core.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123",
            roles=[UserRole.DEVELOPER]
        )
        
        assert success is True
        assert user is not None
        assert user.username == "testuser"
        assert user.password_hash.startswith("$2b$")
        assert Permission.READ in user.permissions
        assert Permission.WRITE in user.permissions
    
    async def test_password_policy(self, bcrypt_core):
        """Test password policy validation."""
        # Weak password
        success, message, user = await bcrypt_core.create_user(
            username="weak",
            email="weak@example.com",
            password="weak",
            roles=[UserRole.VIEWER]
        )
        
        assert success is False
        assert "weak" in message.lower()
        
        # Strong password
        success, message, user = await bcrypt_core.create_user(
            username="strong",
            email="strong@example.com",
            password="StrongPass123",
            roles=[UserRole.VIEWER]
        )
        
        assert success is True
    
    async def test_authentication(self, bcrypt_core):
        """Test user authentication."""
        # Create user
        await bcrypt_core.create_user(
            username="authuser",
            email="auth@example.com",
            password="AuthPass123",
            roles=[UserRole.OPERATOR]
        )
        
        # Authenticate successfully
        success, message, user = await bcrypt_core.authenticate_user(
            username="authuser",
            password="AuthPass123"
        )
        
        assert success is True
        assert user is not None
        assert user.username == "authuser"
        
        # Authenticate with wrong password
        success, message, user = await bcrypt_core.authenticate_user(
            username="authuser",
            password="WrongPassword"
        )
        
        assert success is False
        assert user is None
    
    async def test_account_lockout(self, bcrypt_core):
        """Test account lockout mechanism."""
        # Create user
        await bcrypt_core.create_user(
            username="lockuser",
            email="lock@example.com",
            password="LockPass123",
            roles=[UserRole.VIEWER]
        )
        
        # Multiple failed attempts
        for i in range(3):
            success, message, user = await bcrypt_core.authenticate_user(
                username="lockuser",
                password="WrongPassword"
            )
            assert success is False
        
        # Should be locked now
        success, message, user = await bcrypt_core.authenticate_user(
            username="lockuser",
            password="LockPass123"  # Correct password
        )
        
        assert success is False
        assert "locked" in message.lower()
    
    async def test_password_change(self, bcrypt_core):
        """Test password change."""
        # Create user
        success, message, user = await bcrypt_core.create_user(
            username="changeuser",
            email="change@example.com",
            password="OldPass123",
            roles=[UserRole.DEVELOPER]
        )
        
        assert success is True
        
        # Change password
        success, message = await bcrypt_core.change_password(
            user_id=user.user_id,
            current_password="OldPass123",
            new_password="NewPass456"
        )
        
        assert success is True
        
        # Test with new password
        success, message, auth_user = await bcrypt_core.authenticate_user(
            username="changeuser",
            password="NewPass456"
        )
        
        assert success is True
    
    async def test_role_permissions(self, bcrypt_core):
        """Test role-based permissions."""
        # Admin user
        success, message, admin = await bcrypt_core.create_user(
            username="admin",
            email="admin@example.com",
            password="AdminPass123",
            roles=[UserRole.ADMIN]
        )
        
        assert success is True
        assert Permission.ADMIN in admin.permissions
        assert Permission.READ in admin.permissions
        
        # Viewer user
        success, message, viewer = await bcrypt_core.create_user(
            username="viewer",
            email="viewer@example.com",
            password="ViewerPass123",
            roles=[UserRole.VIEWER]
        )
        
        assert success is True
        assert Permission.READ in viewer.permissions
        assert Permission.ADMIN not in viewer.permissions
    
    async def test_bcrypt_hashing(self, bcrypt_core):
        """Test bcrypt hashing features."""
        password = "TestPassword123"
        
        # Hash password
        hash1 = bcrypt_core.hash_password(password)
        hash2 = bcrypt_core.hash_password(password)
        
        # Should be different (salt)
        assert hash1 != hash2
        assert hash1.startswith("$2b$")
        assert hash2.startswith("$2b$")
        
        # Should verify correctly
        assert bcrypt_core.verify_password_hash(password, hash1) is True
        assert bcrypt_core.verify_password_hash(password, hash2) is True
        assert bcrypt_core.verify_password_hash("wrong", hash1) is False
    
    async def test_user_counting(self, bcrypt_core):
        """Test user counting."""
        # Create users
        await bcrypt_core.create_user("user1", "user1@example.com", "Pass123", [UserRole.VIEWER])
        await bcrypt_core.create_user("user2", "user2@example.com", "Pass123", [UserRole.VIEWER])
        
        # Check counts
        assert bcrypt_core.get_user_count() == 2
        assert bcrypt_core.get_active_user_count() == 2