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

    Failure-count-based rate limiting: Only failed authentication attempts
    increment the in-memory attempt counter. Successful authentications do not
    count toward the limit to avoid throttling valid traffic during bursts.
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
        # Derived config
        self.max_auth_attempts = int(config.get("max_auth_attempts", 5))
        self.auth_window = int(config.get("auth_window_minutes", 15)) * 60

        # In-memory stores expected by tests
        self.api_keys: Dict[str, Dict[str, Any]] = {}
        self.basic_auth_users: Dict[str, Dict[str, Any]] = {}
        self.jwt_tokens: Dict[str, Dict[str, Any]] = {}
        self.oauth_tokens: Dict[str, Dict[str, Any]] = {}
        self.signing_secrets: Dict[str, str] = {}
        self.auth_attempts: Dict[str, List[float]] = {}

        # Role and path permissions stores
        self.roles: Dict[str, List[Permission]] = {
            "admin": [Permission.READ, Permission.WRITE, Permission.ADMIN, Permission.EXECUTE],
            "user": [Permission.READ, Permission.WRITE],
            "readonly": [Permission.READ],
        }
        self.path_permissions: Dict[str, List[Permission]] = {}

        logger.info("AuthenticationMiddleware initialized")

    def create_api_key(self, user_id: str, permissions: List[Permission], expires_in_hours: int = 24) -> str:
        key = uuid.uuid4().hex
        self.api_keys[key] = {
            "user_id": user_id,
            "permissions": permissions,
            "active": True,
            "usage_count": 0,
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(hours=expires_in_hours)).isoformat(),
        }
        return key

    def revoke_api_key(self, api_key: str) -> bool:
        if api_key in self.api_keys:
            self.api_keys[api_key]["active"] = False
            return True
        return False

    def _hash_password(self, password: str) -> str:
        return pwd_context.hash(password)

    def verify_password(self, password: str, hashed: str) -> bool:
        try:
            return pwd_context.verify(password, hashed)
        except Exception:
            return False

    def create_basic_auth_user(self, username: str, password: str, permissions: List[Permission], active: bool = True) -> Tuple[bool, List[str]]:
        issues: List[str] = []
        if not username or not password:
            issues.append("username/password required")
            return False, issues
        self.basic_auth_users[username] = {
            "password": self._hash_password(password),
            "permissions": permissions,
            "active": active,
            "login_count": 0,
            "last_login": None,
            "updated_at": None,
        }
        return True, issues

    def update_basic_auth_user(self, username: str, password: Optional[str] = None,
                               permissions: Optional[List[Permission]] = None,
                               active: Optional[bool] = None) -> bool:
        if username not in self.basic_auth_users:
            return False
        user = self.basic_auth_users[username]
        if password is not None:
            user["password"] = self._hash_password(password)
        if permissions is not None:
            user["permissions"] = permissions
        if active is not None:
            user["active"] = active
        user["updated_at"] = datetime.now().isoformat()
        return True

    def create_jwt_token(self, user_id: str, permissions: List[Permission], expires_in_hours: int = 1) -> str:
        payload = {
            "sub": user_id,
            "permissions": [p.value for p in permissions],
            "exp": datetime.utcnow() + timedelta(hours=expires_in_hours),
            "type": "access",
        }
        token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        self.jwt_tokens[token] = {"user_id": user_id, "permissions": permissions}
        return token

    def create_rbac_jwt_token(self, user_id: str, roles: List[str], permissions: List[Permission],
                               user_metadata: Optional[Dict[str, Any]] = None, expires_in_hours: int = 1) -> str:
        payload = {
            "sub": user_id,
            "roles": roles,
            "rbac": {"roles": roles},
            "user_metadata": user_metadata or {},
            "permissions": [p.value for p in permissions],
            "exp": datetime.utcnow() + timedelta(hours=expires_in_hours),
            "type": "access",
        }
        token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        self.jwt_tokens[token] = {"user_id": user_id, "roles": roles, "permissions": permissions}
        return token

    def extract_rbac_info_from_token(self, token: str) -> Optional[Dict[str, Any]]:
        try:
            data = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            return data
        except Exception:
            return None

    def refresh_jwt_token(self, token: str) -> Optional[str]:
        info = self.jwt_tokens.get(token)
        if not info:
            return None
        return self.create_jwt_token(info.get("user_id", ""), info.get("permissions", []))

    def is_jwt_token_blacklisted(self, token: str) -> bool:
        # Simple in-memory blacklist concept: if not present we consider it not blacklisted
        return False

    async def authenticate_request(self, request: ApiRequest) -> AuthResult:
        """Authenticate an ApiRequest using enabled methods in order.

        Rate limiting only applies to FAILED attempts. Successful authentications
        do not count toward the limit to support concurrent valid traffic.
        """
        # Check failed-attempts rate limit per client IP
        now = time.time()
        failed_attempts = self.auth_attempts.setdefault(request.client_ip, [])
        failed_attempts = [t for t in failed_attempts if now - t <= self.auth_window]
        if len(failed_attempts) >= self.max_auth_attempts:
            return AuthResult(success=False, error="Too many authentication attempts")
        # store back trimmed list
        self.auth_attempts[request.client_ip] = failed_attempts

        # API Key
        if AuthMethod.API_KEY in self.enabled_methods:
            api_key = request.headers.get("X-API-Key")
            if api_key and api_key in self.api_keys:
                key_data = self.api_keys[api_key]
                if key_data.get("active", False):
                    key_data["usage_count"] = key_data.get("usage_count", 0) + 1
                    return AuthResult(success=True, user_id=key_data["user_id"], permissions=key_data["permissions"], metadata={})

        # BASIC
        if AuthMethod.BASIC in self.enabled_methods:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Basic "):
                try:
                    import base64
                    decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
                    username, password = decoded.split(":", 1)
                    user = self.basic_auth_users.get(username)
                    if user and user.get("active") and self.verify_password(password, user["password"]):
                        user["login_count"] = user.get("login_count", 0) + 1
                        user["last_login"] = datetime.now().isoformat()
                        return AuthResult(success=True, user_id=username, permissions=user["permissions"], metadata={"basic_auth": True})
                except Exception:
                    pass

        # JWT / OAuth2 (share Bearer header)
        bearer = request.headers.get("Authorization", "")
        if bearer.startswith("Bearer "):
            token = bearer[7:]
            if AuthMethod.JWT in self.enabled_methods:
                try:
                    data = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
                    perms = [Permission(p) if isinstance(p, str) else p for p in data.get("permissions", [])]
                    return AuthResult(success=True, user_id=data.get("sub"), permissions=perms, metadata={"jwt": True})
                except Exception:
                    pass
            if AuthMethod.OAUTH2 in self.enabled_methods:
                token_data = self.oauth_tokens.get(token)
                if token_data:
                    try:
                        exp = datetime.fromisoformat(token_data["expires_at"])
                        if exp > datetime.now():
                            return AuthResult(success=True, user_id=token_data["user_id"], permissions=token_data["permissions"], metadata={"oauth2": True})
                    except Exception:
                        pass

        # Signature method
        if AuthMethod.SIGNATURE in self.enabled_methods:
            client_id = request.headers.get("X-Client-ID")
            signature = request.headers.get("X-Signature")
            if client_id and signature and client_id in self.signing_secrets:
                expected = self._generate_signature(client_id, request)
                if hmac.compare_digest(signature, expected):
                    return AuthResult(success=True, user_id=client_id, permissions=[Permission.READ], metadata={"client_id": client_id})

        # Record failed attempt for rate limiting
        failed_attempts = self.auth_attempts.setdefault(request.client_ip, [])
        failed_attempts.append(time.time())
        self.auth_attempts[request.client_ip] = failed_attempts
        return AuthResult(success=False, error="Authentication failed")

    def _generate_signature(self, client_id: str, request: ApiRequest) -> str:
        secret = self.signing_secrets.get(client_id, "")
        msg = f"{request.method}:{request.path}:{request.request_id}".encode("utf-8")
        return hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()