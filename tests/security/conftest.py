"""
Security Test Configuration

Provides pytest fixtures and configuration for security testing,
including mock authentication services and test data.
"""

import pytest
import sys
import os
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock

# Ensure we can import from project root
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Change working directory to project root to help with imports
original_cwd = os.getcwd()
os.chdir(project_root)

try:
    # Try to import existing modules, skip if not available
    pass
    # from config.security_config import SecurityConfigManager, SecurityLevel
    # from config.auth_models import Permission
    # from security.auth_service import AuthenticationService, UserRole
finally:
    # Restore original working directory
    os.chdir(original_cwd)


@pytest.fixture
def security_config() -> Dict[str, Any]:
    """Provide test security configuration."""
    return {
        "bcrypt_rounds": 4,  # Low for testing
        "jwt_secret": "test-secret-key-32-characters-long",
        "jwt_algorithm": "HS256",
        "token_expiry_minutes": 15,
        "max_failed_attempts": 3,
        "lockout_duration_minutes": 5,
        "session_timeout_minutes": 30,
        "password_expiry_days": 90,
        "require_2fa": False
    }


@pytest.fixture
def security_config_manager():
    """Provide test security configuration manager."""
    # Return mock for now since SecurityConfigManager is not available
    return Mock()


@pytest.fixture
def auth_service(security_config):
    """Provide test authentication service."""
    # Return mock for now since AuthenticationService is not available  
    return Mock()


@pytest.fixture
def test_user_credentials() -> Dict[str, Any]:
    """Provide test user credentials."""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "TestPassword123!",
        "roles": ["developer"],
        "permissions": ["read", "write"]
    }


@pytest.fixture
def mock_client_info() -> Dict[str, str]:
    """Provide mock client information."""
    return {
        "ip_address": "127.0.0.1",
        "user_agent": "pytest-test-agent/1.0"
    }