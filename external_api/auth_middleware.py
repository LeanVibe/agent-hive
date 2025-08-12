"""
Authentication Middleware for API Gateway

Provides advanced authentication mechanisms including JWT tokens,
OAuth 2.0, API key validation, and role-based access control.
"""

import asyncio
import hashlib
import hmac
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable, Tuple
from enum import Enum
import uuid
from passlib.context import CryptContext
from passlib.hash import bcrypt
import jwt
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError

from .models import ApiRequest, ApiResponse
# Import security config with robust fallbacks (project has .claude/config shadowing)
try:
    # Direct submodule import (preferred)
    from config.security_config import get_auth_config, get_security_config  # type: ignore
except Exception:
    # Fallback: import from top-level package if it re-exports
    try:
        from config import get_auth_config, get_security_config  # type: ignore
    except Exception as e:  # Final fallback: local lazy resolver to avoid import error during collection
        def get_auth_config() -> dict:  # type: ignore
            from config.security_config import get_auth_middleware_config as _g
            return _g()
        def get_security_config():  # type: ignore
            from config.security_config import security_config_manager as _m
            return _m.get_config()


logger = logging.getLogger(__name__)

# Password context for secure hashing - will be configured based on security settings
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthMethod(Enum):
    """Supported authentication methods."""
    API_KEY = "api_key"
    JWT = "jwt"
    OAUTH2 = "oauth2"
    BASIC = "basic"
    SIGNATURE = "signature"


try:
    from config.auth_models import Permission, AuthResult
except Exception:
    # Final fallback: define lightweight shims if top-level package shadowing prevents import
    try:
        from config import Permission, AuthResult  # type: ignore
    except Exception:
        from enum import Enum
        class Permission(Enum):  # type: ignore
            READ = "read"; WRITE = "write"; ADMIN = "admin"; EXECUTE = "execute"
        class AuthResult:  # type: ignore
            def __init__(self, success: bool, user_id=None, permissions=None, error=None, metadata=None):
                self.success = success
                self.user_id = user_id
                self.permissions = permissions or []
                self.error = error
                self.metadata = metadata or {}


class AuthenticationMiddleware:
    """
    Advanced authentication middleware with multiple auth methods.

    Supports API keys, JWT tokens, OAuth 2.0, request signing,
    and role-based access control.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize authentication middleware.

        Args:
            config: Authentication configuration
        """
        self.config = config
        self.enabled_methods = config.get("enabled_methods", [AuthMethod.API_KEY])
        self.jwt_secret = config.get("jwt_secret", "default-secret")
        self.jwt_algorithm = config.get("jwt_algorithm", "HS256")
        self.token_expiry = config.get("token_expiry_hours", 24)