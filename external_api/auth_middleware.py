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
from config.security_config import get_auth_config, get_security_config


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
<<<<<<< HEAD

||||||| 64640d5
        
=======
        
        # Configure password context with security settings
        bcrypt_rounds = config.get("bcrypt_rounds", 12)
        global pwd_context
        pwd_context = CryptContext(
            schemes=["bcrypt"], 
            deprecated="auto",
            bcrypt__rounds=bcrypt_rounds
        )
        
>>>>>>> new-work/security-Jul-17-0944
        # Storage for authentication data
        self.api_keys: Dict[str, Dict[str, Any]] = {}
        self.jwt_tokens: Dict[str, Dict[str, Any]] = {}
        self.oauth_tokens: Dict[str, Dict[str, Any]] = {}
        self.signing_secrets: Dict[str, str] = {}
        self.basic_auth_users: Dict[str, Dict[str, Any]] = {}
<<<<<<< HEAD

||||||| 64640d5
        
=======
        self.user_lockouts: Dict[str, Dict[str, Any]] = {}  # Track account lockouts
        self.password_history: Dict[str, List[str]] = {}  # Track password history
        
>>>>>>> new-work/security-Jul-17-0944
        # Rate limiting for auth attempts
        self.auth_attempts: Dict[str, List[float]] = {}
        self.max_auth_attempts = config.get("max_auth_attempts", 5)
        self.auth_window = config.get("auth_window_minutes", 15) * 60
<<<<<<< HEAD

||||||| 64640d5
        
=======
        
        # Password policy settings
        self.password_config = config.get("password_config", {})
        self.lockout_attempts = self.password_config.get("lockout_attempts", 5)
        self.lockout_duration = self.password_config.get("lockout_duration_minutes", 30) * 60
        self.password_history_count = self.password_config.get("password_history_count", 5)
        
>>>>>>> new-work/security-Jul-17-0944
        # Role-based access control
        self.roles: Dict[str, List[Permission]] = {
            "admin": [Permission.READ, Permission.WRITE, Permission.ADMIN, Permission.EXECUTE],
            "user": [Permission.READ, Permission.WRITE],
            "readonly": [Permission.READ]
        }

        # Path-based permissions
        self.path_permissions: Dict[str, List[Permission]] = {}

        logger.info(f"AuthenticationMiddleware initialized with methods: {self.enabled_methods}")
<<<<<<< HEAD

||||||| 64640d5
    
=======
    
    @classmethod
    def create_with_secure_config(cls) -> 'AuthenticationMiddleware':
        """Create AuthenticationMiddleware with secure configuration from environment."""
        config = get_auth_config()
        middleware = cls(config)
        
        # Validate configuration
        from config.security_config import security_config_manager
        validation_result = security_config_manager.validate_config()
        
        if not validation_result["valid"]:
            logger.warning("Security configuration validation failed:")
            for issue in validation_result["issues"]:
                logger.warning(f"  - {issue}")
        
        return middleware
    
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        return pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)
    
>>>>>>> new-work/security-Jul-17-0944
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
<<<<<<< HEAD

            # Check expiration
            if payload.get("exp") and payload["exp"] < time.time():
                return AuthResult(success=False, error="JWT token has expired")

||||||| 64640d5
            
            # Check expiration
            if payload.get("exp") and payload["exp"] < time.time():
                return AuthResult(success=False, error="JWT token has expired")
            
=======
            
>>>>>>> new-work/security-Jul-17-0944
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
<<<<<<< HEAD

            # Verify password (in production, use proper password hashing)
            if user_data.get("password") != password:
||||||| 64640d5
            
            # Verify password (in production, use proper password hashing)
            if user_data.get("password") != password:
=======
            
            # Check if account is locked
            if self.is_account_locked(username):
                return AuthResult(success=False, error="Account is temporarily locked due to too many failed attempts")
            
            # Verify password using bcrypt
            if not self.verify_password(password, user_data.get("password", "")):
                self.record_failed_login(username)
>>>>>>> new-work/security-Jul-17-0944
                return AuthResult(success=False, error="Invalid username or password")

            # Check if account is active
            if not user_data.get("active", True):
                return AuthResult(success=False, error="Account is deactivated")
<<<<<<< HEAD

            # Update login statistics
||||||| 64640d5
            
            # Update login statistics
=======
            
            # Successful login - clear any lockout and update statistics
            self.record_successful_login(username)
>>>>>>> new-work/security-Jul-17-0944
            user_data["last_login"] = datetime.now().isoformat()
            user_data["login_count"] = user_data.get("login_count", 0) + 1
<<<<<<< HEAD

||||||| 64640d5
            
=======
            user_data["failed_login_attempts"] = 0
            
>>>>>>> new-work/security-Jul-17-0944
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
<<<<<<< HEAD
            # Simple base64 decode for demo purposes
            import base64
            header, payload, signature = token.split('.')

            # Add padding if needed
            payload += '=' * (4 - len(payload) % 4)
            decoded_payload = base64.b64decode(payload)

            return json.loads(decoded_payload)
        except Exception as e:
||||||| 64640d5
            # Simple base64 decode for demo purposes
            import base64
            header, payload, signature = token.split('.')
            
            # Add padding if needed
            payload += '=' * (4 - len(payload) % 4)
            decoded_payload = base64.b64decode(payload)
            
            return json.loads(decoded_payload)
        except Exception as e:
=======
            # Decode and validate JWT token
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            return payload
        except ExpiredSignatureError:
            raise ValueError("JWT token has expired")
        except InvalidTokenError as e:
>>>>>>> new-work/security-Jul-17-0944
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
<<<<<<< HEAD

||||||| 64640d5
    
=======
    
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
        from config.security_config import security_config_manager
        
        validation_result = security_config_manager.validate_password(password)
        return validation_result["valid"], validation_result["issues"]
    
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
    
>>>>>>> new-work/security-Jul-17-0944
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
<<<<<<< HEAD

        return True

||||||| 64640d5
        
        return True
    
=======
        
        return True, []
    
>>>>>>> new-work/security-Jul-17-0944
    def update_basic_auth_user(self, username: str, password: Optional[str] = None,
                              permissions: Optional[List[Permission]] = None,
                              active: Optional[bool] = None) -> bool:
        """Update a basic auth user."""
        if username not in self.basic_auth_users:
            return False

        user_data = self.basic_auth_users[username]

        if password is not None:
<<<<<<< HEAD
            user_data["password"] = password  # In production: hash this!

||||||| 64640d5
            user_data["password"] = password  # In production: hash this!
        
=======
            user_data["password"] = self.hash_password(password)  # Securely hash password
        
>>>>>>> new-work/security-Jul-17-0944
        if permissions is not None:
            user_data["permissions"] = permissions

        if active is not None:
            user_data["active"] = active

        user_data["updated_at"] = datetime.now().isoformat()

        logger.info(f"Updated basic auth user: {username}")
        return True

    def delete_basic_auth_user(self, username: str) -> bool:
        """Delete a basic auth user."""
        if username in self.basic_auth_users:
            del self.basic_auth_users[username]
            logger.info(f"Deleted basic auth user: {username}")
            return True
        return False

    def create_jwt_token(self, user_id: str, permissions: List[Permission],
                        expires_in_hours: Optional[int] = None) -> str:
        """Create a JWT token using PyJWT."""
        current_time = datetime.utcnow()
        
        payload = {
            "user_id": user_id,
            "permissions": [p.value for p in permissions],
            "iat": current_time,
            "jti": str(uuid.uuid4())
        }

        if expires_in_hours:
<<<<<<< HEAD
            payload["exp"] = time.time() + (expires_in_hours * 3600)

        # In production, use proper JWT library
        import base64
        import json

        header = {"alg": self.jwt_algorithm, "typ": "JWT"}
        header_b64 = base64.b64encode(json.dumps(header).encode()).decode().rstrip('=')
        payload_b64 = base64.b64encode(json.dumps(payload).encode()).decode().rstrip('=')

        # Simple signature (use proper JWT library in production)
        signature = hashlib.sha256(f"{header_b64}.{payload_b64}.{self.jwt_secret}".encode()).hexdigest()

        token = f"{header_b64}.{payload_b64}.{signature}"

||||||| 64640d5
            payload["exp"] = time.time() + (expires_in_hours * 3600)
        
        # In production, use proper JWT library
        import base64
        import json
        
        header = {"alg": self.jwt_algorithm, "typ": "JWT"}
        header_b64 = base64.b64encode(json.dumps(header).encode()).decode().rstrip('=')
        payload_b64 = base64.b64encode(json.dumps(payload).encode()).decode().rstrip('=')
        
        # Simple signature (use proper JWT library in production)
        signature = hashlib.sha256(f"{header_b64}.{payload_b64}.{self.jwt_secret}".encode()).hexdigest()
        
        token = f"{header_b64}.{payload_b64}.{signature}"
        
=======
            payload["exp"] = current_time + timedelta(hours=expires_in_hours)
        else:
            payload["exp"] = current_time + timedelta(hours=self.token_expiry)
        
        # Create JWT token using PyJWT
        token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        
        # Store token metadata for blacklisting
>>>>>>> new-work/security-Jul-17-0944
        self.jwt_tokens[token] = {
            "user_id": user_id,
            "created_at": current_time.isoformat(),
            "blacklisted": False
        }
<<<<<<< HEAD

        logger.info(f"Created JWT token for user {user_id}")
||||||| 64640d5
        
        logger.info(f"Created JWT token for user {user_id}")
=======
        
        logger.info(f"Created JWT token for user {user_id} (expires: {payload['exp']})")
        return token
    
    def create_rbac_jwt_token(self, user_id: str, roles: List[str], permissions: List[Permission], 
                             user_metadata: Optional[Dict[str, Any]] = None,
                             expires_in_hours: Optional[int] = None) -> str:
        """Create a JWT token with RBAC role information for authorization pipeline."""
        current_time = datetime.utcnow()
        
        payload = {
            "user_id": user_id,
            "roles": roles,  # Role names for RBAC authorization
            "permissions": [p.value for p in permissions],
            "iat": current_time,
            "jti": str(uuid.uuid4()),
            "token_type": "access",
            "scope": "api",
            "issuer": "agent-hive-security",
            "audience": "agent-hive-services"
        }
        
        # Add user metadata if provided
        if user_metadata:
            payload["user_metadata"] = user_metadata
        
        # Add RBAC-specific claims
        payload["rbac"] = {
            "roles": roles,
            "permissions": [
                {
                    "resource_type": getattr(p, 'resource_type', 'unknown'),
                    "action": getattr(p, 'action', p.value),
                    "scope": getattr(p, 'scope', 'global')
                } for p in permissions
            ],
            "version": "1.0"
        }
        
        if expires_in_hours:
            payload["exp"] = current_time + timedelta(hours=expires_in_hours)
        else:
            payload["exp"] = current_time + timedelta(hours=self.token_expiry)
        
        # Create JWT token using PyJWT
        token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        
        # Store token metadata for blacklisting
        self.jwt_tokens[token] = {
            "user_id": user_id,
            "roles": roles,
            "created_at": current_time.isoformat(),
            "blacklisted": False,
            "token_type": "rbac_access"
        }
        
        logger.info(f"Created RBAC JWT token for user {user_id} with roles {roles} (expires: {payload['exp']})")
>>>>>>> new-work/security-Jul-17-0944
        return token

    def blacklist_jwt_token(self, token: str) -> bool:
        """Blacklist a JWT token."""
        if token in self.jwt_tokens:
            self.jwt_tokens[token]["blacklisted"] = True
            logger.info(f"Blacklisted JWT token")
            return True
        return False
<<<<<<< HEAD

||||||| 64640d5
    
=======
    
    def refresh_jwt_token(self, token: str) -> Optional[str]:
        """Refresh a JWT token by creating a new one and blacklisting the old one."""
        try:
            # Decode the old token to get user information
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            
            # Check if token is blacklisted
            if token in self.jwt_tokens and self.jwt_tokens[token].get("blacklisted"):
                logger.warning("Attempted to refresh blacklisted token")
                return None
            
            # Extract user information
            user_id = payload.get("user_id")
            permissions = [Permission(p) for p in payload.get("permissions", [])]
            
            if not user_id:
                logger.error("Cannot refresh token: no user_id in payload")
                return None
            
            # Create new token
            new_token = self.create_jwt_token(user_id, permissions)
            
            # Blacklist the old token
            self.blacklist_jwt_token(token)
            
            logger.info(f"Refreshed JWT token for user {user_id}")
            return new_token
            
        except ExpiredSignatureError:
            logger.warning("Cannot refresh expired token")
            return None
        except InvalidTokenError as e:
            logger.error(f"Cannot refresh invalid token: {e}")
            return None
    
    def cleanup_expired_tokens(self) -> int:
        """Clean up expired and blacklisted tokens from memory."""
        current_time = datetime.utcnow()
        tokens_to_remove = []
        
        for token, token_data in self.jwt_tokens.items():
            try:
                # Try to decode token to check if it's expired
                jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
                
                # Also remove blacklisted tokens older than 24 hours
                if token_data.get("blacklisted"):
                    created_at = datetime.fromisoformat(token_data.get("created_at", current_time.isoformat()))
                    if (current_time - created_at).total_seconds() > 86400:  # 24 hours
                        tokens_to_remove.append(token)
                        
            except ExpiredSignatureError:
                # Token is expired, mark for removal
                tokens_to_remove.append(token)
            except InvalidTokenError:
                # Token is invalid, mark for removal
                tokens_to_remove.append(token)
        
        # Remove expired/invalid tokens
        for token in tokens_to_remove:
            del self.jwt_tokens[token]
        
        logger.info(f"Cleaned up {len(tokens_to_remove)} expired/invalid tokens")
        return len(tokens_to_remove)
    
    def extract_rbac_info_from_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Extract RBAC role and permission information from JWT token."""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            
            # Extract RBAC information
            rbac_info = {
                "user_id": payload.get("user_id"),
                "roles": payload.get("roles", []),
                "permissions": payload.get("permissions", []),
                "rbac": payload.get("rbac", {}),
                "token_type": payload.get("token_type", "access"),
                "scope": payload.get("scope", "api"),
                "user_metadata": payload.get("user_metadata", {}),
                "issued_at": payload.get("iat"),
                "expires_at": payload.get("exp"),
                "token_id": payload.get("jti")
            }
            
            return rbac_info
            
        except ExpiredSignatureError:
            logger.warning("Cannot extract RBAC info from expired token")
            return None
        except InvalidTokenError as e:
            logger.error(f"Cannot extract RBAC info from invalid token: {e}")
            return None
    
    def validate_rbac_access(self, token: str, required_resource_type: str, 
                           required_action: str, resource_id: Optional[str] = None) -> bool:
        """Validate RBAC access for a specific resource and action."""
        rbac_info = self.extract_rbac_info_from_token(token)
        
        if not rbac_info:
            return False
        
        # Check if token is blacklisted
        if token in self.jwt_tokens and self.jwt_tokens[token].get("blacklisted"):
            return False
        
        # Check RBAC permissions
        rbac_permissions = rbac_info.get("rbac", {}).get("permissions", [])
        
        for permission in rbac_permissions:
            if (permission.get("resource_type") == required_resource_type and
                permission.get("action") == required_action):
                
                # Check resource ID if specified
                if resource_id:
                    perm_resource_id = permission.get("resource_id")
                    if perm_resource_id and perm_resource_id != "*" and perm_resource_id != resource_id:
                        continue
                
                return True
        
        return False
    
>>>>>>> new-work/security-Jul-17-0944
    def set_path_permissions(self, path: str, permissions: List[Permission]) -> None:
        """Set required permissions for a path."""
        self.path_permissions[path] = permissions
        logger.info(f"Set permissions for path {path}: {permissions}")

    def add_signing_secret(self, client_id: str, secret: str) -> None:
        """Add signing secret for a client."""
        self.signing_secrets[client_id] = secret
        logger.info(f"Added signing secret for client {client_id}")
<<<<<<< HEAD

||||||| 64640d5
    
=======
    
    def schedule_token_cleanup(self, interval_hours: int = 1):
        """Schedule automatic token cleanup."""
        import threading
        import time
        
        def cleanup_worker():
            while True:
                try:
                    cleaned_count = self.cleanup_expired_tokens()
                    if cleaned_count > 0:
                        logger.info(f"Automatic cleanup removed {cleaned_count} tokens")
                    time.sleep(interval_hours * 3600)  # Convert hours to seconds
                except Exception as e:
                    logger.error(f"Token cleanup error: {e}")
                    time.sleep(300)  # Wait 5 minutes before retrying
        
        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()
        logger.info(f"Started automatic token cleanup with {interval_hours}h interval")
    
    def create_secure_api_key(self, user_id: str, permissions: List[Permission], 
                             description: str = "", rate_limit: Optional[int] = None,
                             ip_whitelist: Optional[List[str]] = None,
                             expires_in_hours: Optional[int] = None) -> str:
        """Create a secure API key with advanced security features."""
        # Generate cryptographically secure API key
        import secrets
        api_key = f"ahk_{secrets.token_urlsafe(32)}"  # agent-hive-key prefix
        
        key_data = {
            "user_id": user_id,
            "permissions": permissions,
            "description": description,
            "created_at": datetime.now().isoformat(),
            "active": True,
            "usage_count": 0,
            "last_used": None,
            "rate_limit": rate_limit,  # requests per minute
            "ip_whitelist": ip_whitelist or [],
            "security_features": {
                "secure_generation": True,
                "prefix": "ahk_",
                "entropy_bits": 256
            }
        }
        
        if expires_in_hours:
            expires_at = datetime.now() + timedelta(hours=expires_in_hours)
            key_data["expires_at"] = expires_at.isoformat()
        
        self.api_keys[api_key] = key_data
        logger.info(f"Created secure API key for user {user_id} with description: {description}")
        
        return api_key
    
    def validate_api_key_security(self, api_key: str, client_ip: str = None) -> Tuple[bool, str]:
        """Validate API key with enhanced security checks."""
        if api_key not in self.api_keys:
            return False, "API key not found"
        
        key_data = self.api_keys[api_key]
        
        # Check IP whitelist if configured
        if key_data.get("ip_whitelist") and client_ip:
            if client_ip not in key_data["ip_whitelist"]:
                logger.warning(f"API key access denied for IP {client_ip} (not in whitelist)")
                return False, "IP address not authorized for this API key"
        
        # Check rate limiting
        if key_data.get("rate_limit"):
            current_time = time.time()
            usage_window = key_data.get("rate_window", [])
            
            # Clean old usage records (keep only last minute)
            usage_window = [timestamp for timestamp in usage_window if current_time - timestamp < 60]
            
            if len(usage_window) >= key_data["rate_limit"]:
                return False, "Rate limit exceeded for API key"
            
            # Record current usage
            usage_window.append(current_time)
            key_data["rate_window"] = usage_window
        
        return True, "API key validation passed"
    
>>>>>>> new-work/security-Jul-17-0944
    def get_auth_stats(self) -> Dict[str, Any]:
        """Get authentication statistics."""
        current_time = datetime.now()
        
        # Calculate active tokens (not expired)
        active_jwt_count = 0
        for token in self.jwt_tokens:
            try:
                jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
                if not self.jwt_tokens[token].get("blacklisted", False):
                    active_jwt_count += 1
            except:
                pass
        
        return {
            "total_api_keys": len(self.api_keys),
            "active_api_keys": len([k for k in self.api_keys.values() if k.get("active", True)]),
            "total_jwt_tokens": len(self.jwt_tokens),
            "active_jwt_tokens": active_jwt_count,
            "blacklisted_jwt_tokens": len([t for t in self.jwt_tokens.values() if t.get("blacklisted", False)]),
            "oauth_tokens": len(self.oauth_tokens),
            "basic_auth_users": len(self.basic_auth_users),
            "signing_clients": len(self.signing_secrets),
            "protected_paths": len(self.path_permissions),
<<<<<<< HEAD
            "enabled_methods": [m.value for m in self.enabled_methods]
        }
||||||| 64640d5
            "enabled_methods": [m.value for m in self.enabled_methods]
        }
=======
            "enabled_methods": [m.value for m in self.enabled_methods],
            "security_features": {
                "auto_cleanup_enabled": True,
                "rate_limiting_enabled": True,
                "ip_whitelisting_enabled": True,
                "token_blacklisting_enabled": True,
                "rbac_support": True
            },
            "stats_generated_at": current_time.isoformat()
        }
>>>>>>> new-work/security-Jul-17-0944
