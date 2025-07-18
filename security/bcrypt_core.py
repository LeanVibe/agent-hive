#!/usr/bin/env python3
"""
bcrypt Core Authentication

Essential bcrypt password hashing and user authentication.
Focused implementation for Agent Hive security.
"""

import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass

from passlib.context import CryptContext
from passlib.hash import bcrypt

from external_api.auth_middleware import Permission


logger = logging.getLogger(__name__)


class UserRole(Enum):
    """User roles."""
    ADMIN = "admin"
    DEVELOPER = "developer"
    OPERATOR = "operator"
    VIEWER = "viewer"


@dataclass
class User:
    """User model."""
    user_id: str
    username: str
    email: str
    password_hash: str
    roles: List[UserRole]
    permissions: List[Permission]
    created_at: datetime
    last_login: Optional[datetime] = None
    failed_attempts: int = 0
    locked_until: Optional[datetime] = None
    active: bool = True


class BcryptCore:
    """
    bcrypt core authentication with password hashing.
    
    Features:
    - bcrypt password hashing with configurable rounds
    - User creation and authentication
    - Account lockout protection
    - Role-based permissions
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize bcrypt core."""
        self.config = config or {}
        
        # Initialize bcrypt context
        self.pwd_context = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto",
            bcrypt__rounds=self.config.get("bcrypt_rounds", 12)
        )
        
        # User storage
        self.users: Dict[str, User] = {}
        
        # Settings
        self.max_failed_attempts = self.config.get("max_failed_attempts", 5)
        self.lockout_minutes = self.config.get("lockout_minutes", 30)
        
        # Role permissions
        self.role_permissions = {
            UserRole.ADMIN: [Permission.READ, Permission.WRITE, Permission.ADMIN, Permission.EXECUTE],
            UserRole.DEVELOPER: [Permission.READ, Permission.WRITE, Permission.EXECUTE],
            UserRole.OPERATOR: [Permission.READ, Permission.WRITE],
            UserRole.VIEWER: [Permission.READ]
        }
        
        logger.info("bcrypt Core initialized")
    
    async def create_user(self, username: str, email: str, password: str,
                         roles: List[UserRole]) -> Tuple[bool, str, Optional[User]]:
        """
        Create user with bcrypt password hashing.
        
        Returns:
            Tuple of (success, message, user)
        """
        try:
            # Validate input
            if not username or not email or not password:
                return False, "Missing required fields", None
            
            # Check if user exists
            if self._user_exists(username, email):
                return False, "User already exists", None
            
            # Validate password
            if not self._validate_password(password):
                return False, "Password too weak", None
            
            # Hash password with bcrypt
            password_hash = self.pwd_context.hash(password)
            
            # Calculate permissions
            permissions = self._get_permissions(roles)
            
            # Create user
            user_id = str(uuid.uuid4())
            user = User(
                user_id=user_id,
                username=username,
                email=email,
                password_hash=password_hash,
                roles=roles,
                permissions=permissions,
                created_at=datetime.utcnow()
            )
            
            # Store user
            self.users[user_id] = user
            
            logger.info(f"Created user: {username}")
            return True, "User created successfully", user
            
        except Exception as e:
            logger.error(f"User creation failed: {e}")
            return False, f"Creation failed: {e}", None
    
    async def authenticate_user(self, username: str, password: str) -> Tuple[bool, str, Optional[User]]:
        """
        Authenticate user with bcrypt verification.
        
        Returns:
            Tuple of (success, message, user)
        """
        try:
            # Find user
            user = self._find_user_by_username(username)
            if not user:
                return False, "Invalid credentials", None
            
            # Check if locked
            if self._is_locked(user):
                return False, "Account locked", None
            
            # Check if active
            if not user.active:
                return False, "Account inactive", None
            
            # Verify password with bcrypt
            if not self.pwd_context.verify(password, user.password_hash):
                self._record_failed_attempt(user)
                return False, "Invalid credentials", None
            
            # Success - reset failed attempts
            user.failed_attempts = 0
            user.locked_until = None
            user.last_login = datetime.utcnow()
            
            logger.info(f"User authenticated: {username}")
            return True, "Authentication successful", user
            
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False, "Authentication error", None
    
    async def change_password(self, user_id: str, current_password: str, new_password: str) -> Tuple[bool, str]:
        """
        Change user password with bcrypt rehashing.
        
        Returns:
            Tuple of (success, message)
        """
        try:
            # Get user
            user = self.users.get(user_id)
            if not user:
                return False, "User not found"
            
            # Verify current password
            if not self.pwd_context.verify(current_password, user.password_hash):
                return False, "Current password incorrect"
            
            # Validate new password
            if not self._validate_password(new_password):
                return False, "New password too weak"
            
            # Hash new password
            new_hash = self.pwd_context.hash(new_password)
            
            # Update user
            user.password_hash = new_hash
            user.failed_attempts = 0
            user.locked_until = None
            
            logger.info(f"Password changed for user: {user_id}")
            return True, "Password changed successfully"
            
        except Exception as e:
            logger.error(f"Password change failed: {e}")
            return False, "Password change failed"
    
    def _user_exists(self, username: str, email: str) -> bool:
        """Check if user exists."""
        return any(u.username == username or u.email == email for u in self.users.values())
    
    def _find_user_by_username(self, username: str) -> Optional[User]:
        """Find user by username."""
        return next((u for u in self.users.values() if u.username == username), None)
    
    def _validate_password(self, password: str) -> bool:
        """Validate password strength."""
        return (len(password) >= 8 and 
                any(c.isalpha() for c in password) and 
                any(c.isdigit() for c in password))
    
    def _get_permissions(self, roles: List[UserRole]) -> List[Permission]:
        """Get permissions from roles."""
        permissions = set()
        for role in roles:
            permissions.update(self.role_permissions.get(role, []))
        return list(permissions)
    
    def _is_locked(self, user: User) -> bool:
        """Check if user is locked."""
        if user.locked_until and datetime.utcnow() < user.locked_until:
            return True
        
        # Auto-unlock if expired
        if user.locked_until and datetime.utcnow() >= user.locked_until:
            user.locked_until = None
            user.failed_attempts = 0
        
        return False
    
    def _record_failed_attempt(self, user: User) -> None:
        """Record failed login attempt."""
        user.failed_attempts += 1
        
        if user.failed_attempts >= self.max_failed_attempts:
            user.locked_until = datetime.utcnow() + timedelta(minutes=self.lockout_minutes)
            logger.warning(f"Account locked: {user.username}")
    
    def get_user_count(self) -> int:
        """Get total user count."""
        return len(self.users)
    
    def get_active_user_count(self) -> int:
        """Get active user count."""
        return sum(1 for u in self.users.values() if u.active)
    
    def verify_password_hash(self, password: str, hash_value: str) -> bool:
        """Verify password against hash."""
        return self.pwd_context.verify(password, hash_value)
    
    def hash_password(self, password: str) -> str:
        """Hash password with bcrypt."""
        return self.pwd_context.hash(password)