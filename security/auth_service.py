#!/usr/bin/env python3
"""
User Authentication Service

Comprehensive authentication service with bcrypt integration, session management,
and advanced security features for the Agent Hive platform.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass

from passlib.context import CryptContext
import jwt

from config.auth_models import Permission, AuthResult
from security.token_manager import SecureTokenManager, TokenType
from config.security_config import get_security_config, SecurityConfigManager


logger = logging.getLogger(__name__)


class UserRole(Enum):
    """User roles for RBAC."""
    ADMIN = "admin"
    DEVELOPER = "developer"
    OPERATOR = "operator"
    VIEWER = "viewer"
    AGENT = "agent"


class SessionStatus(Enum):
    """User session status."""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    LOCKED = "locked"


@dataclass
class User:
    """User data model."""
    user_id: str
    username: str
    email: str
    password_hash: str
    roles: List[UserRole]
    permissions: List[Permission]
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    login_count: int = 0
    failed_login_attempts: int = 0
    account_locked_until: Optional[datetime] = None
    password_expires_at: Optional[datetime] = None
    two_factor_enabled: bool = False
    two_factor_secret: Optional[str] = None
    active: bool = True
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class UserSession:
    """User session model."""
    session_id: str
    user_id: str
    created_at: datetime
    last_activity: datetime
    expires_at: datetime
    status: SessionStatus
    ip_address: str
    user_agent: str
    access_token: str
    refresh_token: Optional[str] = None
    device_fingerprint: Optional[str] = None
    location: Optional[str] = None


class AuthenticationService:
    """
    Comprehensive authentication service with advanced security features.
    
    Features:
    - bcrypt password hashing with configurable work factors
    - JWT token management with refresh tokens
    - Session management and tracking
    - Account lockout and security policies
    - Two-factor authentication support
    - Role-based access control (RBAC)
    - Security event logging and monitoring
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize authentication service."""
        self.config = config or self._get_default_config()
        
        # Initialize password context with secure configuration
        self.pwd_context = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto",
            bcrypt__rounds=self.config.get("bcrypt_rounds", 12)
        )
        
        # Initialize token manager
        self.token_manager = SecureTokenManager(self.config)
        
        # Initialize data storage (in production, this would be a database)
        self.users: Dict[str, User] = {}
        self.sessions: Dict[str, UserSession] = {}
        self.security_events: List[Dict[str, Any]] = []
        
        # Security configuration
        self.max_failed_attempts = self.config.get("max_failed_attempts", 5)
        self.lockout_duration = self.config.get("lockout_duration_minutes", 30) * 60
        self.session_timeout = self.config.get("session_timeout_minutes", 30) * 60
        self.password_expiry_days = self.config.get("password_expiry_days", 90)
        self.require_2fa = self.config.get("require_2fa", False)
        
        # Role permission mappings
        self.role_permissions = {
            UserRole.ADMIN: [Permission.READ, Permission.WRITE, Permission.ADMIN, Permission.EXECUTE],
            UserRole.DEVELOPER: [Permission.READ, Permission.WRITE, Permission.EXECUTE],
            UserRole.OPERATOR: [Permission.READ, Permission.WRITE],
            UserRole.VIEWER: [Permission.READ],
            UserRole.AGENT: [Permission.READ, Permission.WRITE, Permission.EXECUTE]
        }
        
        # Start cleanup tasks
        self._start_cleanup_tasks()
        
        logger.info("AuthenticationService initialized with bcrypt integration")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default authentication configuration."""
        try:
            security_config = get_security_config()
            return {
                "bcrypt_rounds": security_config.password.bcrypt_rounds,
                "jwt_secret": security_config.jwt.secret_key,
                "jwt_algorithm": security_config.jwt.algorithm,
                "token_expiry_minutes": security_config.jwt.access_token_expire_minutes,
                "max_failed_attempts": security_config.password.lockout_attempts,
                "lockout_duration_minutes": security_config.password.lockout_duration_minutes,
                "session_timeout_minutes": security_config.session_timeout_minutes,
                "password_expiry_days": security_config.password.max_password_age_days,
                "require_2fa": security_config.enable_2fa
            }
        except Exception as e:
            logger.warning(f"Could not load security config: {e}, using defaults")
            return {
                "bcrypt_rounds": 12,
                "jwt_secret": "default-secret-change-in-production",
                "jwt_algorithm": "HS256",
                "token_expiry_minutes": 15,
                "max_failed_attempts": 5,
                "lockout_duration_minutes": 30,
                "session_timeout_minutes": 30,
                "password_expiry_days": 90,
                "require_2fa": False
            }
    
    async def create_user(self, username: str, email: str, password: str,
                         roles: List[UserRole], active: bool = True,
                         metadata: Optional[Dict[str, Any]] = None) -> Tuple[bool, str, Optional[User]]:
        """
        Create a new user with secure password hashing.
        
        Returns:
            Tuple of (success, message, user_object)
        """
        try:
            # Validate input
            if not username or not email or not password:
                return False, "Username, email, and password are required", None
            
            # Check if user already exists
            if await self._user_exists(username, email):
                return False, "User with this username or email already exists", None
            
            # Validate password policy
            is_valid, policy_issues = await self._validate_password_policy(password)
            if not is_valid:
                return False, f"Password policy violation: {'; '.join(policy_issues)}", None
            
            # Hash password with bcrypt
            password_hash = self.pwd_context.hash(password)
            
            # Calculate permissions from roles
            permissions = self._calculate_permissions_from_roles(roles)
            
            # Create user
            user_id = str(uuid.uuid4())
            current_time = datetime.utcnow()
            
            user = User(
                user_id=user_id,
                username=username,
                email=email,
                password_hash=password_hash,
                roles=roles,
                permissions=permissions,
                created_at=current_time,
                updated_at=current_time,
                password_expires_at=current_time + timedelta(days=self.password_expiry_days),
                active=active,
                metadata=metadata or {}
            )
            
            # Store user
            self.users[user_id] = user
            
            # Log security event
            await self._log_security_event({
                "event_type": "user_created",
                "user_id": user_id,
                "username": username,
                "roles": [role.value for role in roles],
                "timestamp": current_time.isoformat()
            })
            
            logger.info(f"Created user: {username} ({user_id})")
            return True, "User created successfully", user
            
        except Exception as e:
            logger.error(f"Failed to create user {username}: {e}")
            return False, f"Failed to create user: {e}", None
    
    async def authenticate_user(self, username: str, password: str,
                               client_ip: str, user_agent: str,
                               two_factor_code: Optional[str] = None) -> Tuple[bool, str, Optional[UserSession]]:
        """
        Authenticate user with comprehensive security checks.
        
        Returns:
            Tuple of (success, message, session_object)
        """
        try:
            # Find user by username
            user = await self._find_user_by_username(username)
            if not user:
                await self._log_security_event({
                    "event_type": "login_failed",
                    "username": username,
                    "reason": "user_not_found",
                    "client_ip": client_ip,
                    "timestamp": datetime.utcnow().isoformat()
                })
                return False, "Invalid credentials", None
            
            # Check if account is locked
            if await self._is_account_locked(user):
                await self._log_security_event({
                    "event_type": "login_blocked",
                    "user_id": user.user_id,
                    "username": username,
                    "reason": "account_locked",
                    "client_ip": client_ip,
                    "timestamp": datetime.utcnow().isoformat()
                })
                return False, "Account is temporarily locked due to too many failed attempts", None
            
            # Check if account is active
            if not user.active:
                return False, "Account is deactivated", None
            
            # Verify password
            if not self.pwd_context.verify(password, user.password_hash):
                await self._record_failed_login(user, client_ip)
                return False, "Invalid credentials", None
            
            # Check password expiration
            if user.password_expires_at and datetime.utcnow() > user.password_expires_at:
                return False, "Password has expired. Please reset your password.", None
            
            # Two-factor authentication check
            if self.require_2fa or user.two_factor_enabled:
                if not two_factor_code:
                    return False, "Two-factor authentication code required", None
                
                if not await self._verify_2fa_code(user, two_factor_code):
                    await self._record_failed_login(user, client_ip, "invalid_2fa")
                    return False, "Invalid two-factor authentication code", None
            
            # Authentication successful - create session
            session = await self._create_user_session(user, client_ip, user_agent)
            
            # Update user login statistics
            await self._record_successful_login(user, client_ip)
            
            logger.info(f"User authenticated: {username} ({user.user_id})")
            return True, "Authentication successful", session
            
        except Exception as e:
            logger.error(f"Authentication error for user {username}: {e}")
            return False, "Authentication failed due to system error", None
    
    async def refresh_session(self, refresh_token: str, client_ip: str) -> Tuple[bool, str, Optional[UserSession]]:
        """Refresh user session with new tokens."""
        try:
            # Find session by refresh token
            session = await self._find_session_by_refresh_token(refresh_token)
            if not session:
                return False, "Invalid refresh token", None
            
            # Check session status
            if session.status != SessionStatus.ACTIVE:
                return False, f"Session is {session.status.value}", None
            
            # Check session expiration
            if datetime.utcnow() > session.expires_at:
                session.status = SessionStatus.EXPIRED
                return False, "Session has expired", None
            
            # Get user
            user = self.users.get(session.user_id)
            if not user or not user.active:
                return False, "User account is not active", None
            
            # Create new tokens
            new_access_token, new_token_id = await self.token_manager.create_secure_token(
                user_id=user.user_id,
                token_type=TokenType.ACCESS,
                permissions=user.permissions,
                expires_in_hours=self.config.get("token_expiry_minutes", 15) / 60
            )
            
            # Update session
            session.access_token = new_access_token
            session.last_activity = datetime.utcnow()
            
            # Extend session expiration
            session.expires_at = datetime.utcnow() + timedelta(seconds=self.session_timeout)
            
            # Log security event
            await self._log_security_event({
                "event_type": "session_refreshed",
                "user_id": user.user_id,
                "session_id": session.session_id,
                "client_ip": client_ip,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            return True, "Session refreshed successfully", session
            
        except Exception as e:
            logger.error(f"Session refresh failed: {e}")
            return False, "Session refresh failed", None
    
    async def logout_user(self, access_token: str) -> Tuple[bool, str]:
        """Logout user and invalidate session."""
        try:
            # Find session by access token
            session = await self._find_session_by_access_token(access_token)
            if not session:
                return False, "Session not found"
            
            # Revoke session
            session.status = SessionStatus.REVOKED
            
            # Revoke tokens
            await self.token_manager.revoke_token(
                self._extract_token_id_from_token(access_token),
                reason="user_logout"
            )
            
            # Log security event
            await self._log_security_event({
                "event_type": "user_logout",
                "user_id": session.user_id,
                "session_id": session.session_id,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            logger.info(f"User logged out: {session.user_id}")
            return True, "Logout successful"
            
        except Exception as e:
            logger.error(f"Logout failed: {e}")
            return False, "Logout failed"
    
    async def validate_session(self, access_token: str, client_ip: str,
                              required_permissions: Optional[List[Permission]] = None) -> AuthResult:
        """Validate user session and permissions."""
        try:
            # Validate token using token manager
            token_result = await self.token_manager.validate_token_secure(
                token=access_token,
                required_permissions=required_permissions,
                client_ip=client_ip
            )
            
            if not token_result.success:
                return token_result
            
            # Find session
            session = await self._find_session_by_access_token(access_token)
            if not session:
                return AuthResult(success=False, error="Session not found")
            
            # Check session status
            if session.status != SessionStatus.ACTIVE:
                return AuthResult(success=False, error=f"Session is {session.status.value}")
            
            # Check session expiration
            if datetime.utcnow() > session.expires_at:
                session.status = SessionStatus.EXPIRED
                return AuthResult(success=False, error="Session has expired")
            
            # Update session activity
            session.last_activity = datetime.utcnow()
            
            # Get user
            user = self.users.get(session.user_id)
            if not user or not user.active:
                return AuthResult(success=False, error="User account is not active")
            
            # Enhanced result with session information
            enhanced_result = AuthResult(
                success=True,
                user_id=user.user_id,
                permissions=user.permissions,
                metadata={
                    **token_result.metadata,
                    "session_id": session.session_id,
                    "username": user.username,
                    "roles": [role.value for role in user.roles],
                    "last_activity": session.last_activity.isoformat(),
                    "session_expires_at": session.expires_at.isoformat()
                }
            )
            
            return enhanced_result
            
        except Exception as e:
            logger.error(f"Session validation failed: {e}")
            return AuthResult(success=False, error="Session validation failed")
    
    async def change_password(self, user_id: str, current_password: str,
                             new_password: str) -> Tuple[bool, str]:
        """Change user password with security validation."""
        try:
            # Get user
            user = self.users.get(user_id)
            if not user:
                return False, "User not found"
            
            # Verify current password
            if not self.pwd_context.verify(current_password, user.password_hash):
                await self._log_security_event({
                    "event_type": "password_change_failed",
                    "user_id": user_id,
                    "reason": "invalid_current_password",
                    "timestamp": datetime.utcnow().isoformat()
                })
                return False, "Current password is incorrect"
            
            # Validate new password policy
            is_valid, policy_issues = await self._validate_password_policy(new_password)
            if not is_valid:
                return False, f"Password policy violation: {'; '.join(policy_issues)}"
            
            # Check password history (prevent reuse)
            if await self._is_password_recently_used(user, new_password):
                return False, "Password has been used recently. Please choose a different password."
            
            # Hash new password
            new_password_hash = self.pwd_context.hash(new_password)
            
            # Update user
            user.password_hash = new_password_hash
            user.password_expires_at = datetime.utcnow() + timedelta(days=self.password_expiry_days)
            user.updated_at = datetime.utcnow()
            user.failed_login_attempts = 0  # Reset failed attempts
            user.account_locked_until = None  # Unlock account
            
            # Store password in history
            await self._add_password_to_history(user, new_password_hash)
            
            # Log security event
            await self._log_security_event({
                "event_type": "password_changed",
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            logger.info(f"Password changed for user: {user_id}")
            return True, "Password changed successfully"
            
        except Exception as e:
            logger.error(f"Password change failed for user {user_id}: {e}")
            return False, "Password change failed"
    
    async def enable_two_factor_auth(self, user_id: str) -> Tuple[bool, str, Optional[str]]:
        """Enable two-factor authentication for user."""
        try:
            # Get user
            user = self.users.get(user_id)
            if not user:
                return False, "User not found", None
            
            # Generate 2FA secret
            import pyotp
            secret = pyotp.random_base32()
            
            # Update user
            user.two_factor_secret = secret
            user.two_factor_enabled = True
            user.updated_at = datetime.utcnow()
            
            # Generate QR code URL for setup
            totp = pyotp.TOTP(secret)
            qr_url = totp.provisioning_uri(
                name=user.email,
                issuer_name="Agent Hive Security"
            )
            
            # Log security event
            await self._log_security_event({
                "event_type": "2fa_enabled",
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            logger.info(f"2FA enabled for user: {user_id}")
            return True, "Two-factor authentication enabled", qr_url
            
        except ImportError:
            return False, "Two-factor authentication not available (pyotp not installed)", None
        except Exception as e:
            logger.error(f"Failed to enable 2FA for user {user_id}: {e}")
            return False, "Failed to enable two-factor authentication", None
    
    async def disable_two_factor_auth(self, user_id: str, verification_code: str) -> Tuple[bool, str]:
        """Disable two-factor authentication for user."""
        try:
            # Get user
            user = self.users.get(user_id)
            if not user:
                return False, "User not found"
            
            # Verify 2FA code before disabling
            if not await self._verify_2fa_code(user, verification_code):
                return False, "Invalid verification code"
            
            # Disable 2FA
            user.two_factor_enabled = False
            user.two_factor_secret = None
            user.updated_at = datetime.utcnow()
            
            # Log security event
            await self._log_security_event({
                "event_type": "2fa_disabled",
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            logger.info(f"2FA disabled for user: {user_id}")
            return True, "Two-factor authentication disabled"
            
        except Exception as e:
            logger.error(f"Failed to disable 2FA for user {user_id}: {e}")
            return False, "Failed to disable two-factor authentication"
    
    async def get_user_sessions(self, user_id: str) -> List[UserSession]:
        """Get all active sessions for a user."""
        user_sessions = []
        for session in self.sessions.values():
            if (session.user_id == user_id and 
                session.status == SessionStatus.ACTIVE and
                datetime.utcnow() <= session.expires_at):
                user_sessions.append(session)
        
        return user_sessions
    
    async def revoke_user_sessions(self, user_id: str, exclude_session_id: Optional[str] = None) -> int:
        """Revoke all sessions for a user, optionally excluding one session."""
        revoked_count = 0
        
        for session in self.sessions.values():
            if (session.user_id == user_id and 
                session.status == SessionStatus.ACTIVE and
                session.session_id != exclude_session_id):
                
                session.status = SessionStatus.REVOKED
                
                # Revoke associated tokens
                try:
                    await self.token_manager.revoke_token(
                        self._extract_token_id_from_token(session.access_token),
                        reason="session_revoked"
                    )
                except:
                    pass  # Token may already be expired/invalid
                
                revoked_count += 1
        
        if revoked_count > 0:
            await self._log_security_event({
                "event_type": "sessions_revoked",
                "user_id": user_id,
                "revoked_count": revoked_count,
                "timestamp": datetime.utcnow().isoformat()
            })
        
        return revoked_count
    
    async def get_security_events(self, user_id: Optional[str] = None,
                                 event_types: Optional[List[str]] = None,
                                 limit: int = 100) -> List[Dict[str, Any]]:
        """Get security events, optionally filtered by user or event type."""
        filtered_events = self.security_events
        
        if user_id:
            filtered_events = [e for e in filtered_events if e.get("user_id") == user_id]
        
        if event_types:
            filtered_events = [e for e in filtered_events if e.get("event_type") in event_types]
        
        # Return most recent events first
        return sorted(filtered_events, key=lambda x: x.get("timestamp", ""), reverse=True)[:limit]
    
    # Private helper methods
    
    async def _user_exists(self, username: str, email: str) -> bool:
        """Check if user with username or email already exists."""
        for user in self.users.values():
            if user.username == username or user.email == email:
                return True
        return False
    
    async def _find_user_by_username(self, username: str) -> Optional[User]:
        """Find user by username."""
        for user in self.users.values():
            if user.username == username:
                return user
        return None
    
    async def _validate_password_policy(self, password: str) -> Tuple[bool, List[str]]:
        """Validate password against security policy."""
        config_manager = SecurityConfigManager()
        result = config_manager.validate_password(password)
        return result["valid"], result["issues"]
    
    def _calculate_permissions_from_roles(self, roles: List[UserRole]) -> List[Permission]:
        """Calculate effective permissions from user roles."""
        permissions = set()
        for role in roles:
            role_perms = self.role_permissions.get(role, [])
            permissions.update(role_perms)
        return list(permissions)
    
    async def _is_account_locked(self, user: User) -> bool:
        """Check if user account is locked."""
        if user.account_locked_until and datetime.utcnow() < user.account_locked_until:
            return True
        
        # Auto-unlock expired lockouts
        if user.account_locked_until and datetime.utcnow() >= user.account_locked_until:
            user.account_locked_until = None
            user.failed_login_attempts = 0
        
        return False
    
    async def _record_failed_login(self, user: User, client_ip: str, reason: str = "invalid_password") -> None:
        """Record failed login attempt and potentially lock account."""
        user.failed_login_attempts += 1
        
        if user.failed_login_attempts >= self.max_failed_attempts:
            user.account_locked_until = datetime.utcnow() + timedelta(seconds=self.lockout_duration)
            
            await self._log_security_event({
                "event_type": "account_locked",
                "user_id": user.user_id,
                "username": user.username,
                "failed_attempts": user.failed_login_attempts,
                "locked_until": user.account_locked_until.isoformat(),
                "client_ip": client_ip,
                "timestamp": datetime.utcnow().isoformat()
            })
        
        await self._log_security_event({
            "event_type": "login_failed",
            "user_id": user.user_id,
            "username": user.username,
            "reason": reason,
            "failed_attempts": user.failed_login_attempts,
            "client_ip": client_ip,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def _record_successful_login(self, user: User, client_ip: str) -> None:
        """Record successful login and reset failed attempts."""
        user.last_login = datetime.utcnow()
        user.login_count += 1
        user.failed_login_attempts = 0
        user.account_locked_until = None
        user.updated_at = datetime.utcnow()
        
        await self._log_security_event({
            "event_type": "login_successful",
            "user_id": user.user_id,
            "username": user.username,
            "login_count": user.login_count,
            "client_ip": client_ip,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def _create_user_session(self, user: User, client_ip: str, user_agent: str) -> UserSession:
        """Create a new user session with tokens."""
        session_id = str(uuid.uuid4())
        current_time = datetime.utcnow()
        
        # Create access token
        access_token, token_id = await self.token_manager.create_secure_token(
            user_id=user.user_id,
            token_type=TokenType.ACCESS,
            permissions=user.permissions,
            expires_in_hours=self.config.get("token_expiry_minutes", 15) / 60
        )
        
        # Create refresh token
        refresh_token, refresh_token_id = await self.token_manager.create_secure_token(
            user_id=user.user_id,
            token_type=TokenType.REFRESH,
            permissions=user.permissions,
            expires_in_hours=24 * 30  # 30 days
        )
        
        # Create session
        session = UserSession(
            session_id=session_id,
            user_id=user.user_id,
            created_at=current_time,
            last_activity=current_time,
            expires_at=current_time + timedelta(seconds=self.session_timeout),
            status=SessionStatus.ACTIVE,
            ip_address=client_ip,
            user_agent=user_agent,
            access_token=access_token,
            refresh_token=refresh_token
        )
        
        # Store session
        self.sessions[session_id] = session
        
        return session
    
    async def _verify_2fa_code(self, user: User, code: str) -> bool:
        """Verify two-factor authentication code."""
        if not user.two_factor_enabled or not user.two_factor_secret:
            return True  # 2FA not enabled
        
        try:
            import pyotp
            totp = pyotp.TOTP(user.two_factor_secret)
            return totp.verify(code, valid_window=1)
        except ImportError:
            logger.warning("pyotp not available for 2FA verification")
            return True  # Allow login if 2FA library not available
        except Exception as e:
            logger.error(f"2FA verification error: {e}")
            return False
    
    async def _find_session_by_access_token(self, access_token: str) -> Optional[UserSession]:
        """Find session by access token."""
        for session in self.sessions.values():
            if session.access_token == access_token:
                return session
        return None
    
    async def _find_session_by_refresh_token(self, refresh_token: str) -> Optional[UserSession]:
        """Find session by refresh token."""
        for session in self.sessions.values():
            if session.refresh_token == refresh_token:
                return session
        return None
    
    def _extract_token_id_from_token(self, token: str) -> str:
        """Extract token ID from JWT token."""
        try:
            payload = jwt.decode(token, options={"verify_signature": False})
            return payload.get("token_id", "")
        except Exception:
            return ""
    
    async def _is_password_recently_used(self, user: User, password: str) -> bool:
        """Check if password was recently used."""
        # This would typically check against password history in database
        # For now, just check against current password
        return self.pwd_context.verify(password, user.password_hash)
    
    async def _add_password_to_history(self, user: User, password_hash: str) -> None:
        """Add password hash to user's password history."""
        # In production, this would be stored in database
        if "password_history" not in user.metadata:
            user.metadata["password_history"] = []
        
        history = user.metadata["password_history"]
        history.append(password_hash)
        
        # Keep only last 5 passwords
        if len(history) > 5:
            history = history[-5:]
        
        user.metadata["password_history"] = history
    
    async def _log_security_event(self, event: Dict[str, Any]) -> None:
        """Log security event for monitoring and auditing."""
        event["event_id"] = str(uuid.uuid4())
        self.security_events.append(event)
        
        # Keep only last 10000 events to prevent memory issues
        if len(self.security_events) > 10000:
            self.security_events = self.security_events[-5000:]
    
    def _start_cleanup_tasks(self) -> None:
        """Start background cleanup tasks."""
        async def cleanup_expired_sessions():
            while True:
                try:
                    current_time = datetime.utcnow()
                    expired_count = 0
                    
                    for session in list(self.sessions.values()):
                        if current_time > session.expires_at and session.status == SessionStatus.ACTIVE:
                            session.status = SessionStatus.EXPIRED
                            expired_count += 1
                    
                    if expired_count > 0:
                        logger.info(f"Marked {expired_count} sessions as expired")
                    
                    await asyncio.sleep(3600)  # Run every hour
                    
                except Exception as e:
                    logger.error(f"Session cleanup error: {e}")
                    await asyncio.sleep(300)  # Wait 5 minutes on error
        
        # Start cleanup task only if event loop is running
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(cleanup_expired_sessions())
        except RuntimeError:
            # No event loop running, cleanup will be handled manually
            logger.info("No event loop running, session cleanup will be handled manually")
    
    async def get_authentication_stats(self) -> Dict[str, Any]:
        """Get authentication service statistics."""
        total_users = len(self.users)
        active_users = sum(1 for user in self.users.values() if user.active)
        total_sessions = len(self.sessions)
        active_sessions = sum(1 for session in self.sessions.values() 
                            if session.status == SessionStatus.ACTIVE and 
                            datetime.utcnow() <= session.expires_at)
        
        # Security event statistics
        event_counts = {}
        for event in self.security_events:
            event_type = event.get("event_type", "unknown")
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
        
        return {
            "users": {
                "total": total_users,
                "active": active_users,
                "with_2fa": sum(1 for user in self.users.values() if user.two_factor_enabled)
            },
            "sessions": {
                "total": total_sessions,
                "active": active_sessions,
                "expired": sum(1 for session in self.sessions.values() 
                             if session.status == SessionStatus.EXPIRED),
                "revoked": sum(1 for session in self.sessions.values() 
                             if session.status == SessionStatus.REVOKED)
            },
            "security_events": {
                "total": len(self.security_events),
                "by_type": event_counts
            },
            "configuration": {
                "bcrypt_rounds": self.config.get("bcrypt_rounds"),
                "session_timeout_minutes": self.session_timeout / 60,
                "max_failed_attempts": self.max_failed_attempts,
                "require_2fa": self.require_2fa,
                "password_expiry_days": self.password_expiry_days
            }
        }
    
    # RBAC Integration Methods
    
    async def create_user_with_rbac(self, username: str, email: str, password: str,
                                   role_ids: List[str], rbac_manager=None, created_by: str = "system",
                                   active: bool = True, metadata: Optional[Dict[str, Any]] = None) -> Tuple[bool, str, Optional[User]]:
        """
        Create user and assign RBAC roles in a single operation.
        
        Args:
            username: User's username
            email: User's email address
            password: User's password
            role_ids: List of role IDs to assign to user
            rbac_manager: RBAC manager instance for role assignment
            created_by: User who created this account
            active: Whether user account is active
            metadata: Additional user metadata
            
        Returns:
            Tuple of (success, message, user_object)
        """
        try:
            # Create user with basic roles first
            from security.auth_service import UserRole  # Import here to avoid circular imports
            success, message, user = await self.create_user(
                username=username,
                email=email,
                password=password,
                roles=[],  # Empty roles initially
                active=active,
                metadata=metadata
            )
            
            if not success:
                return False, message, None
            
            # Assign RBAC roles if manager provided
            if rbac_manager and role_ids:
                for role_id in role_ids:
                    assign_success, assign_message = await rbac_manager.assign_role_to_user(
                        user_id=user.user_id,
                        role_id=role_id,
                        assigned_by=created_by
                    )
                    
                    if not assign_success:
                        logger.warning(f"Failed to assign role {role_id} to user {user.user_id}: {assign_message}")
                        # Continue with other roles even if one fails
            
            # Log security event
            await self._log_security_event({
                "event_type": "user_created_with_rbac",
                "user_id": user.user_id,
                "username": username,
                "role_ids": role_ids,
                "created_by": created_by,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            logger.info(f"Created user with RBAC roles: {username} ({user.user_id})")
            return True, "User created with RBAC roles successfully", user
            
        except Exception as e:
            logger.error(f"Failed to create user with RBAC {username}: {e}")
            return False, f"Failed to create user with RBAC: {e}", None
    
    async def authenticate_with_rbac(self, username: str, password: str, client_ip: str, 
                                   user_agent: str, rbac_manager=None,
                                   two_factor_code: Optional[str] = None) -> Tuple[bool, str, Optional[UserSession], Optional[List[str]]]:
        """
        Authenticate user and return session with RBAC role information.
        
        Returns:
            Tuple of (success, message, session_object, user_role_ids)
        """
        try:
            # Standard authentication
            success, message, session = await self.authenticate_user(
                username=username,
                password=password,
                client_ip=client_ip,
                user_agent=user_agent,
                two_factor_code=two_factor_code
            )
            
            if not success:
                return False, message, None, None
            
            # Get user's RBAC roles if manager provided
            user_role_ids = []
            if rbac_manager:
                user_roles = await rbac_manager.get_user_roles(session.user_id)
                user_role_ids = [role.role_id for role in user_roles]
                
                # Add role information to session metadata
                if hasattr(session, 'metadata'):
                    session.metadata = session.metadata or {}
                else:
                    session.metadata = {}
                
                session.metadata['rbac_roles'] = user_role_ids
                session.metadata['rbac_role_names'] = [role.name for role in user_roles]
            
            return True, message, session, user_role_ids
            
        except Exception as e:
            logger.error(f"RBAC authentication error for user {username}: {e}")
            return False, "Authentication with RBAC failed", None, None
    
    async def validate_session_with_rbac(self, access_token: str, client_ip: str, rbac_manager=None,
                                       required_permissions: Optional[List] = None) -> AuthResult:
        """
        Validate session and check RBAC permissions if required.
        
        Args:
            access_token: User's access token
            client_ip: Client IP address
            rbac_manager: RBAC manager for permission checking
            required_permissions: List of permissions to validate
            
        Returns:
            Enhanced AuthResult with RBAC information
        """
        try:
            # Standard session validation
            auth_result = await self.validate_session(
                access_token=access_token,
                client_ip=client_ip,
                required_permissions=required_permissions
            )
            
            if not auth_result.success:
                return auth_result
            
            # Enhanced validation with RBAC if manager provided
            if rbac_manager:
                # Get user's current roles
                user_roles = await rbac_manager.get_user_roles(auth_result.user_id)
                role_names = [role.name for role in user_roles]
                
                # Get user's effective permissions
                user_permissions = await rbac_manager.get_user_permissions(auth_result.user_id)
                permission_values = [perm.value for perm in user_permissions]
                
                # Check required permissions if specified
                permission_checks = {}
                if required_permissions:
                    for permission in required_permissions:
                        check_result = await rbac_manager.check_permission(
                            auth_result.user_id, 
                            permission
                        )
                        permission_checks[permission.value] = {
                            "granted": check_result.granted,
                            "reason": check_result.reason
                        }
                
                # Enhance auth result with RBAC data
                enhanced_metadata = {
                    **auth_result.metadata,
                    "rbac": {
                        "roles": role_names,
                        "role_count": len(user_roles),
                        "permissions": permission_values,
                        "permission_count": len(user_permissions),
                        "permission_checks": permission_checks
                    }
                }
                
                return AuthResult(
                    success=auth_result.success,
                    user_id=auth_result.user_id,
                    permissions=auth_result.permissions,
                    error=auth_result.error,
                    metadata=enhanced_metadata
                )
            
            return auth_result
            
        except Exception as e:
            logger.error(f"RBAC session validation failed: {e}")
            return AuthResult(success=False, error=f"RBAC session validation failed: {e}")
    
    async def get_user_rbac_summary(self, user_id: str, rbac_manager=None) -> Dict[str, Any]:
        """
        Get comprehensive RBAC summary for a user.
        
        Args:
            user_id: User identifier
            rbac_manager: RBAC manager instance
            
        Returns:
            Dictionary with user's RBAC information
        """
        try:
            user = self.users.get(user_id)
            if not user:
                return {"error": "User not found"}
            
            summary = {
                "user_id": user_id,
                "username": user.username,
                "email": user.email,
                "active": user.active,
                "created_at": user.created_at.isoformat(),
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "login_count": user.login_count
            }
            
            if rbac_manager:
                # Get roles
                user_roles = await rbac_manager.get_user_roles(user_id)
                summary["roles"] = [
                    {
                        "role_id": role.role_id,
                        "name": role.name,
                        "type": role.role_type.value,
                        "description": role.description
                    }
                    for role in user_roles
                ]
                
                # Get permissions
                user_permissions = await rbac_manager.get_user_permissions(user_id)
                summary["permissions"] = [perm.value for perm in user_permissions]
                
                # Get role assignments
                assignments = rbac_manager.user_assignments.get(user_id, [])
                active_assignments = [
                    {
                        "assignment_id": assign.assignment_id,
                        "role_id": assign.role_id,
                        "assigned_by": assign.assigned_by,
                        "assigned_at": assign.assigned_at.isoformat(),
                        "expires_at": assign.expires_at.isoformat() if assign.expires_at else None,
                        "active": assign.active
                    }
                    for assign in assignments if assign.active
                ]
                summary["role_assignments"] = active_assignments
                
                summary["rbac_summary"] = {
                    "total_roles": len(user_roles),
                    "total_permissions": len(user_permissions),
                    "active_assignments": len(active_assignments)
                }
            else:
                summary["rbac_available"] = False
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get RBAC summary for user {user_id}: {e}")
            return {"error": f"Failed to get RBAC summary: {e}"}
    
    async def bulk_assign_roles(self, user_role_mapping: Dict[str, List[str]], 
                               rbac_manager=None, assigned_by: str = "system") -> Dict[str, Any]:
        """
        Assign roles to multiple users in bulk operation.
        
        Args:
            user_role_mapping: Dictionary mapping user_id to list of role_ids
            rbac_manager: RBAC manager instance
            assigned_by: User performing the bulk assignment
            
        Returns:
            Summary of bulk assignment results
        """
        try:
            if not rbac_manager:
                return {"error": "RBAC manager not available"}
            
            results = {
                "successful_assignments": 0,
                "failed_assignments": 0,
                "assignment_details": [],
                "errors": []
            }
            
            for user_id, role_ids in user_role_mapping.items():
                user_results = {
                    "user_id": user_id,
                    "roles_assigned": [],
                    "roles_failed": []
                }
                
                for role_id in role_ids:
                    success, message = await rbac_manager.assign_role_to_user(
                        user_id=user_id,
                        role_id=role_id,
                        assigned_by=assigned_by
                    )
                    
                    if success:
                        user_results["roles_assigned"].append(role_id)
                        results["successful_assignments"] += 1
                    else:
                        user_results["roles_failed"].append({"role_id": role_id, "error": message})
                        results["failed_assignments"] += 1
                
                results["assignment_details"].append(user_results)
            
            # Log bulk assignment event
            await self._log_security_event({
                "event_type": "bulk_role_assignment",
                "total_users": len(user_role_mapping),
                "successful_assignments": results["successful_assignments"],
                "failed_assignments": results["failed_assignments"],
                "assigned_by": assigned_by,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            return results
            
        except Exception as e:
            logger.error(f"Bulk role assignment failed: {e}")
            return {"error": f"Bulk role assignment failed: {e}"}
    
    async def sync_user_permissions_cache(self, user_id: str, rbac_manager=None) -> bool:
        """
        Synchronize user's permission cache with current RBAC state.
        
        Args:
            user_id: User identifier
            rbac_manager: RBAC manager instance
            
        Returns:
            Success status
        """
        try:
            if not rbac_manager:
                return False
            
            # Clear user's permission cache in RBAC manager
            await rbac_manager._clear_user_permission_cache(user_id)
            
            # Pre-warm cache with common permissions
            common_permissions = [
                # Add commonly checked permissions here
                # This would be configured based on your application needs
            ]
            
            for permission in common_permissions:
                await rbac_manager.check_permission(user_id, permission)
            
            logger.debug(f"Synchronized permission cache for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to sync permission cache for user {user_id}: {e}")
            return False