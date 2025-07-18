"""
Authentication Middleware for API Gateway

Provides basic authentication mechanisms for external API access.
"""

import logging
from typing import Dict, Any, Optional, List
from enum import Enum

from .models import ApiRequest

logger = logging.getLogger(__name__)


class AuthMethod(Enum):
    """Supported authentication methods."""
    API_KEY = "api_key"
    JWT = "jwt"
    OAUTH2 = "oauth2"
    BASIC = "basic"
    SIGNATURE = "signature"


class Permission(Enum):
    """System permissions."""
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    EXECUTE = "execute"


class AuthResult:
    """Authentication result."""

    def __init__(self, success: bool, user_id: Optional[str] = None,
                 permissions: Optional[List[Permission]] = None,
                 error: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        self.success = success
        self.user_id = user_id
        self.permissions = permissions or []
        self.error = error
        self.metadata = metadata or {}


class AuthenticationMiddleware:
    """Basic authentication middleware."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize authentication middleware."""
        self.config = config
        self.api_keys: Dict[str, Dict[str, Any]] = {}
        logger.info("AuthenticationMiddleware initialized")

    async def authenticate_request(self, request: ApiRequest) -> AuthResult:
        """Authenticate an API request."""
        # Basic API key authentication
        api_key = request.headers.get("X-API-Key") or request.headers.get("Authorization", "").replace("Bearer ", "")
        
        if not api_key:
            return AuthResult(success=False, error="API key required")
        
        # Security fix: Reject if no API keys are configured
        if not self.api_keys:
            logger.warning("No API keys configured - rejecting all requests")
            return AuthResult(success=False, error="Authentication not configured")
        
        if api_key not in self.api_keys:
            return AuthResult(success=False, error="Invalid API key")
        
        key_data = self.api_keys[api_key]
        if not key_data.get("active", True):
            return AuthResult(success=False, error="API key is inactive")
        
        return AuthResult(
            success=True,
            user_id=key_data.get("user_id"),
            permissions=[Permission.READ, Permission.WRITE]
        )

    def register_api_key(self, api_key: str, user_id: str, active: bool = True):
        """Register an API key."""
        self.api_keys[api_key] = {
            "user_id": user_id,
            "active": active,
            "permissions": ["read", "write"]
        }
        logger.info(f"Registered API key for user {user_id}")