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
try:
    from config.security_config import get_auth_config, get_security_config
except ImportError:
    # Fallback for missing config module
    def get_auth_config():
        return {}
    def get_security_config():
        return {}


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
        
        # Configure password context with security settings
        bcrypt_rounds = config.get("bcrypt_rounds", 12)
        global pwd_context
        pwd_context = CryptContext(
            schemes=["bcrypt"], 
            deprecated="auto",
            bcrypt__rounds=bcrypt_rounds
        )
        
        # Storage for authentication data
        self.api_keys: Dict[str, Dict[str, Any]] = {}
        self.jwt_tokens: Dict[str, Dict[str, Any]] = {}
        self.oauth_tokens: Dict[str, Dict[str, Any]] = {}
        self.signing_secrets: Dict[str, str] = {}
        self.basic_auth_users: Dict[str, Dict[str, Any]] = {}
        self.user_lockouts: Dict[str, Dict[str, Any]] = {}  # Track account lockouts
        self.password_history: Dict[str, List[str]] = {}  # Track password history
        
        # Rate limiting for auth attempts
        self.auth_attempts: Dict[str, List[float]] = {}
        self.max_auth_attempts = config.get("max_auth_attempts", 5)
        self.auth_window = config.get("auth_window_minutes", 15) * 60
        
        # Password policy settings
        self.password_config = config.get("password_config", {})
        self.lockout_attempts = self.password_config.get("lockout_attempts", 5)
        self.lockout_duration = self.password_config.get("lockout_duration_minutes", 30) * 60
        self.password_history_count = self.password_config.get("password_history_count", 5)
        
        # Role-based access control
        self.roles: Dict[str, List[Permission]] = {
            "admin": [Permission.READ, Permission.WRITE, Permission.ADMIN, Permission.EXECUTE],
            "user": [Permission.READ, Permission.WRITE],
            "readonly": [Permission.READ]
        }

        # Path-based permissions
        self.path_permissions: Dict[str, List[Permission]] = {}

        logger.info(f"AuthenticationMiddleware initialized with methods: {self.enabled_methods}")
    
    @classmethod
    def create_with_secure_config(cls) -> 'AuthenticationMiddleware':
        """Create AuthenticationMiddleware with secure configuration from environment."""
        config = get_auth_config()
        middleware = cls(config)
        
        # Validate configuration
        try:
            from config.security_config import security_config_manager
            validation_result = security_config_manager.validate_config()
            
            if not validation_result["valid"]:
                logger.warning("Security configuration validation failed:")
                for issue in validation_result["issues"]:
                    logger.warning(f"  - {issue}")
        except ImportError:
            logger.info("Security configuration module not available, using defaults")
        
        return middleware
    
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        return pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)
    
    async def authenticate_request(self, request: ApiRequest) -> AuthResult:
        """
        Authenticate an API request using configured methods.

        Args:
            request: API request to authenticate

        Returns:
            Authentication result
        """
        # Check rate limiting for authentication attempts
        if not await self._check_auth_rate_limit(request.client_ip):
            return AuthResult(
                success=False,
                error="Too many authentication attempts. Please try again later."
            )

        # Try each enabled authentication method
        for method in self.enabled_methods:
            try:
                if method == AuthMethod.API_KEY:
                    result = await self._authenticate_api_key(request)
                elif method == AuthMethod.JWT:
                    result = await self._authenticate_jwt(request)
                elif method == AuthMethod.OAUTH2:
                    result = await self._authenticate_oauth2(request)
                elif method == AuthMethod.BASIC:
                    result = await self._authenticate_basic(request)
                elif method == AuthMethod.SIGNATURE:
                    result = await self._authenticate_signature(request)
                else:
                    continue

                if result.success:
                    # Check permissions for the requested path
                    if await self._check_path_permissions(request.path, result.permissions):
                        return result
                    else:
                        return AuthResult(
                            success=False,
                            error="Insufficient permissions for this endpoint"
                        )

            except Exception as e:
                logger.error(f"Authentication error with method {method}: {e}")
                continue

        # Record failed authentication attempt
        await self._record_auth_attempt(request.client_ip, False)

        return AuthResult(
            success=False,
            error="Authentication failed. Please check your credentials."
        )

    async def _authenticate_api_key(self, request: ApiRequest) -> AuthResult:
        """Authenticate using API key."""
        api_key = request.headers.get("X-API-Key") or request.headers.get("Authorization", "").replace("Bearer ", "")

        if not api_key:
            return AuthResult(success=False, error="API key not provided")

        if api_key not in self.api_keys:
            return AuthResult(success=False, error="Invalid API key")

        key_data = self.api_keys[api_key]

        # Check if key is active
        if not key_data.get("active", True):
            return AuthResult(success=False, error="API key is inactive")

        # Check expiration
        if key_data.get("expires_at"):
            expires_at = datetime.fromisoformat(key_data["expires_at"])
            if datetime.now() > expires_at:
                return AuthResult(success=False, error="API key has expired")

        # Update last used
        key_data["last_used"] = datetime.now().isoformat()
        key_data["usage_count"] = key_data.get("usage_count", 0) + 1

        return AuthResult(
            success=True,
            user_id=key_data.get("user_id"),
            permissions=key_data.get("permissions", []),
            metadata={"api_key": api_key, "key_data": key_data}
        )

    async def _authenticate_jwt(self, request: ApiRequest) -> AuthResult:
        """Authenticate using JWT token."""
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return AuthResult(success=False, error="JWT token not provided")

        token = auth_header[7:]  # Remove "Bearer " prefix

        try:
            # Decode JWT token (PyJWT handles expiration automatically)
            payload = await self._decode_jwt(token)
            
            # Check if token is blacklisted
            if token in self.jwt_tokens and self.jwt_tokens[token].get("blacklisted"):
                return AuthResult(success=False, error="JWT token is blacklisted")

            return AuthResult(
                success=True,
                user_id=payload.get("user_id"),
                permissions=payload.get("permissions", []),
                metadata={"jwt_payload": payload}
            )

        except Exception as e:
            logger.error(f"JWT authentication failed: {e}")
            return AuthResult(success=False, error="Invalid JWT token")

    async def _authenticate_oauth2(self, request: ApiRequest) -> AuthResult:
        """Authenticate using OAuth 2.0 token."""
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return AuthResult(success=False, error="OAuth token not provided")

        token = auth_header[7:]

        if token not in self.oauth_tokens:
            return AuthResult(success=False, error="Invalid OAuth token")

        token_data = self.oauth_tokens[token]

        # Check expiration
        if token_data.get("expires_at"):
            expires_at = datetime.fromisoformat(token_data["expires_at"])
            if datetime.now() > expires_at:
                return AuthResult(success=False, error="OAuth token has expired")

        return AuthResult(
            success=True,
            user_id=token_data.get("user_id"),
            permissions=token_data.get("permissions", []),
            metadata={"oauth_token": token, "token_data": token_data}
        )

    async def _authenticate_basic(self, request: ApiRequest) -> AuthResult:
        """Authenticate using basic authentication."""
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Basic "):
            return AuthResult(success=False, error="Basic auth credentials not provided")

        try:
            # Decode basic auth credentials
            import base64
            encoded_credentials = auth_header[6:]  # Remove "Basic " prefix
            decoded_credentials = base64.b64decode(encoded_credentials).decode('utf-8')

            if ':' not in decoded_credentials:
                return AuthResult(success=False, error="Invalid basic auth format")

            username, password = decoded_credentials.split(':', 1)

            # Check if user exists in basic auth users
            if username not in self.basic_auth_users:
                return AuthResult(success=False, error="Invalid username or password")

            user_data = self.basic_auth_users[username]
            
            # Check if account is locked
            if self.is_account_locked(username):
                return AuthResult(success=False, error="Account is temporarily locked due to too many failed attempts")
            
            # Verify password using bcrypt
            if not self.verify_password(password, user_data.get("password", "")):
                self.record_failed_login(username)
                return AuthResult(success=False, error="Invalid username or password")

            # Check if account is active
            if not user_data.get("active", True):
                return AuthResult(success=False, error="Account is deactivated")
            
            # Successful login - clear any lockout and update statistics
            self.record_successful_login(username)
            user_data["last_login"] = datetime.now().isoformat()
            user_data["login_count"] = user_data.get("login_count", 0) + 1
            user_data["failed_login_attempts"] = 0

            return AuthResult(
                success=True,
                user_id=username,
                permissions=user_data.get("permissions", []),
                metadata={"basic_auth": True, "username": username}
            )

        except Exception as e:
            logger.error(f"Basic authentication failed: {e}")
            return AuthResult(success=False, error="Invalid basic auth credentials")

    async def _authenticate_signature(self, request: ApiRequest) -> AuthResult:
        """Authenticate using request signature."""
        signature = request.headers.get("X-Signature")
        client_id = request.headers.get("X-Client-ID")

        if not signature or not client_id:
            return AuthResult(success=False, error="Signature authentication requires X-Signature and X-Client-ID headers")

        if client_id not in self.signing_secrets:
            return AuthResult(success=False, error="Unknown client ID")

        # Generate expected signature
        secret = self.signing_secrets[client_id]
        expected_signature = await self._generate_signature(request, secret)

        if not hmac.compare_digest(signature, expected_signature):
            return AuthResult(success=False, error="Invalid signature")

        return AuthResult(
            success=True,
            user_id=client_id,
            permissions=self.roles.get("user", []),
            metadata={"client_id": client_id}
        )

    async def _generate_signature(self, request: ApiRequest, secret: str) -> str:
        """Generate request signature."""
        # Create signature string
        signature_string = f"{request.method}{request.path}{request.body or ''}"

        # Generate HMAC signature
        signature = hmac.new(
            secret.encode(),
            signature_string.encode(),
            hashlib.sha256
        ).hexdigest()

        return signature

    async def _decode_jwt(self, token: str) -> Dict[str, Any]:
        """Decode JWT token using PyJWT."""
        try:
            # Decode and validate JWT token
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            return payload
        except ExpiredSignatureError:
            raise ValueError("JWT token has expired")
        except InvalidTokenError as e:
            raise ValueError(f"Invalid JWT token: {e}")

    async def _check_auth_rate_limit(self, client_ip: str) -> bool:
        """Check rate limit for authentication attempts."""
        current_time = time.time()
        window_start = current_time - self.auth_window

        if client_ip not in self.auth_attempts:
            self.auth_attempts[client_ip] = []

        # Clean old attempts
        self.auth_attempts[client_ip] = [
            attempt for attempt in self.auth_attempts[client_ip]
            if attempt > window_start
        ]

        # Check if under limit
        return len(self.auth_attempts[client_ip]) < self.max_auth_attempts

    async def _record_auth_attempt(self, client_ip: str, success: bool) -> None:
        """Record authentication attempt."""
        if not success:
            if client_ip not in self.auth_attempts:
                self.auth_attempts[client_ip] = []
            self.auth_attempts[client_ip].append(time.time())

    async def _check_path_permissions(self, path: str, user_permissions: List[Permission]) -> bool:
        """Check if user has permissions for the requested path."""
        if path not in self.path_permissions:
            return True  # No specific permissions required

        required_permissions = self.path_permissions[path]

        # Check if user has any of the required permissions
        for permission in required_permissions:
            if permission in user_permissions:
                return True

        return False

    # Management methods

    def create_api_key(self, user_id: str, permissions: List[Permission],
                      expires_in_hours: Optional[int] = None) -> str:
        """Create a new API key."""
        api_key = str(uuid.uuid4())

        key_data = {
            "user_id": user_id,
            "permissions": permissions,
            "created_at": datetime.now().isoformat(),
            "active": True,
            "usage_count": 0
        }

        if expires_in_hours:
            expires_at = datetime.now() + timedelta(hours=expires_in_hours)
            key_data["expires_at"] = expires_at.isoformat()

        self.api_keys[api_key] = key_data
        logger.info(f"Created API key for user {user_id}")

        return api_key

    def revoke_api_key(self, api_key: str) -> bool:
        """Revoke an API key."""
        if api_key in self.api_keys:
            self.api_keys[api_key]["active"] = False
            logger.info(f"Revoked API key: {api_key}")
            return True
        return False
    
    def is_account_locked(self, username: str) -> bool:
        """Check if user account is locked due to too many failed attempts."""
        if username not in self.user_lockouts:
            return False
        
        lockout_data = self.user_lockouts[username]
        lockout_time = datetime.fromisoformat(lockout_data["locked_at"])
        
        # Check if lockout has expired
        if (datetime.now() - lockout_time).total_seconds() > self.lockout_duration:
            # Lockout expired, remove it
            del self.user_lockouts[username]
            return False
        
        return True
    
    def record_failed_login(self, username: str):
        """Record a failed login attempt and lock account if needed."""
        if username not in self.user_lockouts:
            self.user_lockouts[username] = {
                "failed_attempts": 0,
                "locked_at": None
            }
        
        lockout_data = self.user_lockouts[username]
        lockout_data["failed_attempts"] += 1
        
        if lockout_data["failed_attempts"] >= self.lockout_attempts:
            lockout_data["locked_at"] = datetime.now().isoformat()
            logger.warning(f"Account locked for user {username} after {self.lockout_attempts} failed attempts")
    
    def record_successful_login(self, username: str):
        """Record successful login and clear any lockout."""
        if username in self.user_lockouts:
            del self.user_lockouts[username]
    
    def validate_password_policy(self, password: str) -> Tuple[bool, List[str]]:
        """Validate password against security policy."""
        try:
            from config.security_config import security_config_manager
            validation_result = security_config_manager.validate_password(password)
            return validation_result["valid"], validation_result["issues"]
        except ImportError:
            # Fallback validation - basic password requirements
            issues = []
            if len(password) < 8:
                issues.append("Password must be at least 8 characters long")
            if not any(c.isupper() for c in password):
                issues.append("Password must contain at least one uppercase letter")
            if not any(c.islower() for c in password):
                issues.append("Password must contain at least one lowercase letter")
            if not any(c.isdigit() for c in password):
                issues.append("Password must contain at least one number")
            
            return len(issues) == 0, issues
    
    def check_password_history(self, username: str, new_password: str) -> bool:
        """Check if password has been used recently."""
        if username not in self.password_history:
            return True  # No history, password is okay
        
        history = self.password_history[username]
        for old_password_hash in history:
            if self.verify_password(new_password, old_password_hash):
                return False  # Password was used recently
        
        return True
    
    def add_to_password_history(self, username: str, password_hash: str):
        """Add password hash to user's history."""
        if username not in self.password_history:
            self.password_history[username] = []
        
        history = self.password_history[username]
        history.append(password_hash)
        
        # Keep only the last N passwords
        if len(history) > self.password_history_count:
            history.pop(0)

    def create_basic_auth_user(self, username: str, password: str, permissions: List[Permission],
                              active: bool = True) -> Tuple[bool, List[str]]:
        """Create a basic auth user with bcrypt password hashing and policy validation."""
        # Validate password policy
        is_valid, issues = self.validate_password_policy(password)
        if not is_valid:
            return False, issues
        
        # Check password history (for existing users)
        if username in self.basic_auth_users:
            if not self.check_password_history(username, password):
                return False, ["Password has been used recently. Please choose a different password."]
        
        password_hash = self.hash_password(password)
        
        user_data = {
            "password": password_hash,  # Securely hash password
            "permissions": permissions,
            "active": active,
            "created_at": datetime.now().isoformat(),
            "last_login": None,
            "login_count": 0,
            "password_created_at": datetime.now().isoformat(),
            "failed_login_attempts": 0
        }

        self.basic_auth_users[username] = user_data
        
        # Add to password history
        self.add_to_password_history(username, password_hash)
        
        logger.info(f"Created basic auth user: {username}")
        
        return True, []

    def update_basic_auth_user(self, username: str, password: Optional[str] = None,
                              permissions: Optional[List[Permission]] = None,
                              active: Optional[bool] = None) -> bool:
        """Update a basic auth user."""
        if username not in self.basic_auth_users:
            return False

        user_data = self.basic_auth_users[username]

        if password is not None:
            user_data["password"] = self.hash_password(password)  # Securely hash password
            user_data["password_created_at"] = datetime.now().isoformat()

        if permissions is not None:
            user_data["permissions"] = permissions

        if active is not None:
            user_data["active"] = active

        user_data["updated_at"] = datetime.now().isoformat()
        logger.info(f"Updated basic auth user: {username}")

        return True

    def create_jwt_token(self, user_id: str, permissions: List[Permission],
                        expires_in_hours: Optional[int] = None) -> str:
        """Create a JWT token."""
        now = datetime.now()
        expiry_hours = expires_in_hours or self.token_expiry

        payload = {
            "user_id": user_id,
            "permissions": [p.value for p in permissions],
            "issued_at": now.isoformat(),
            "expires_at": (now + timedelta(hours=expiry_hours)).isoformat(),
            "exp": int((now + timedelta(hours=expiry_hours)).timestamp())
        }

        token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        
        # Store token metadata
        self.jwt_tokens[token] = {
            "user_id": user_id,
            "created_at": now.isoformat(),
            "expires_at": payload["expires_at"],
            "blacklisted": False
        }

        logger.info(f"Created JWT token for user {user_id}")
        return token

    def blacklist_jwt_token(self, token: str) -> bool:
        """Blacklist a JWT token."""
        if token in self.jwt_tokens:
            self.jwt_tokens[token]["blacklisted"] = True
            logger.info(f"Blacklisted JWT token")
            return True
        return False

    def create_oauth_token(self, user_id: str, permissions: List[Permission],
                          expires_in_hours: Optional[int] = None) -> str:
        """Create an OAuth 2.0 token."""
        token = str(uuid.uuid4())
        now = datetime.now()
        expiry_hours = expires_in_hours or self.token_expiry

        token_data = {
            "user_id": user_id,
            "permissions": permissions,
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(hours=expiry_hours)).isoformat(),
            "active": True
        }

        self.oauth_tokens[token] = token_data
        logger.info(f"Created OAuth token for user {user_id}")

        return token

    def revoke_oauth_token(self, token: str) -> bool:
        """Revoke an OAuth token."""
        if token in self.oauth_tokens:
            self.oauth_tokens[token]["active"] = False
            logger.info(f"Revoked OAuth token")
            return True
        return False

    def create_signing_secret(self, client_id: str) -> str:
        """Create a signing secret for signature authentication."""
        secret = str(uuid.uuid4())
        self.signing_secrets[client_id] = secret
        logger.info(f"Created signing secret for client {client_id}")
        return secret

    def revoke_signing_secret(self, client_id: str) -> bool:
        """Revoke a signing secret."""
        if client_id in self.signing_secrets:
            del self.signing_secrets[client_id]
            logger.info(f"Revoked signing secret for client {client_id}")
            return True
        return False

    def set_path_permissions(self, path: str, permissions: List[Permission]) -> None:
        """Set permissions required for a specific path."""
        self.path_permissions[path] = permissions
        logger.info(f"Set permissions for path {path}: {permissions}")

    def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user information from all authentication methods."""
        # Check API keys
        for api_key, key_data in self.api_keys.items():
            if key_data.get("user_id") == user_id:
                return {
                    "user_id": user_id,
                    "auth_method": "api_key",
                    "permissions": key_data.get("permissions", []),
                    "active": key_data.get("active", True),
                    "created_at": key_data.get("created_at"),
                    "last_used": key_data.get("last_used")
                }

        # Check basic auth users
        if user_id in self.basic_auth_users:
            user_data = self.basic_auth_users[user_id]
            return {
                "user_id": user_id,
                "auth_method": "basic",
                "permissions": user_data.get("permissions", []),
                "active": user_data.get("active", True),
                "created_at": user_data.get("created_at"),
                "last_login": user_data.get("last_login"),
                "login_count": user_data.get("login_count", 0)
            }

        return None

    def get_auth_stats(self) -> Dict[str, Any]:
        """Get authentication statistics."""
        return {
            "total_api_keys": len(self.api_keys),
            "active_api_keys": len([k for k in self.api_keys.values() if k.get("active", True)]),
            "total_basic_users": len(self.basic_auth_users),
            "active_basic_users": len([u for u in self.basic_auth_users.values() if u.get("active", True)]),
            "total_jwt_tokens": len(self.jwt_tokens),
            "active_jwt_tokens": len([t for t in self.jwt_tokens.values() if not t.get("blacklisted", False)]),
            "total_oauth_tokens": len(self.oauth_tokens),
            "active_oauth_tokens": len([t for t in self.oauth_tokens.values() if t.get("active", True)]),
            "locked_accounts": len(self.user_lockouts),
            "enabled_methods": [method.value for method in self.enabled_methods]
        }