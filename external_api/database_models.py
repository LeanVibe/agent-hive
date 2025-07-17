"""
Database models for authentication and user management.

Provides SQLAlchemy models for persistent storage of users, API keys, and JWT tokens.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import uuid
import json

from sqlalchemy import (
    Column, String, Integer, DateTime, Boolean, Text, JSON, 
    ForeignKey, Table, Index, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Session
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from .auth_middleware import Permission

Base = declarative_base()


# Association table for user roles
user_roles = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id'), primary_key=True),
    Column('role_id', UUID(as_uuid=True), ForeignKey('roles.id'), primary_key=True)
)


# Association table for role permissions
role_permissions = Table(
    'role_permissions',
    Base.metadata,
    Column('role_id', UUID(as_uuid=True), ForeignKey('roles.id'), primary_key=True),
    Column('permission_id', UUID(as_uuid=True), ForeignKey('permissions.id'), primary_key=True)
)


class User(Base):
    """User model for authentication and authorization."""
    
    __tablename__ = 'users'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    
    # Account status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Authentication stats
    login_count = Column(Integer, default=0)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    
    # Profile information
    profile_data = Column(JSON, nullable=True)  # Store additional profile data
    
    # Relationships
    roles = relationship("Role", secondary=user_roles, back_populates="users")
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    jwt_tokens = relationship("JWTToken", back_populates="user", cascade="all, delete-orphan")
    login_sessions = relationship("LoginSession", back_populates="user", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_users_email', 'email'),
        Index('idx_users_username', 'username'),
        Index('idx_users_active', 'is_active'),
        Index('idx_users_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary."""
        return {
            'id': str(self.id),
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'is_active': self.is_active,
            'is_verified': self.is_verified,
            'is_superuser': self.is_superuser,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'login_count': self.login_count,
            'roles': [role.name for role in self.roles],
            'profile_data': self.profile_data or {}
        }


class Role(Base):
    """Role model for role-based access control."""
    
    __tablename__ = 'roles'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False)
    display_name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    
    # Role status
    is_active = Column(Boolean, default=True, nullable=False)
    is_system = Column(Boolean, default=False, nullable=False)  # System roles cannot be deleted
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    users = relationship("User", secondary=user_roles, back_populates="roles")
    permissions = relationship("PermissionModel", secondary=role_permissions, back_populates="roles")
    
    def __repr__(self):
        return f"<Role(id={self.id}, name='{self.name}')>"


class PermissionModel(Base):
    """Permission model for granular access control."""
    
    __tablename__ = 'permissions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False)
    display_name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    resource = Column(String(100), nullable=True)  # Resource this permission applies to
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")
    
    def __repr__(self):
        return f"<Permission(id={self.id}, name='{self.name}')>"


class APIKey(Base):
    """API key model for API authentication."""
    
    __tablename__ = 'api_keys'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key_hash = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)  # Human-readable name for the key
    description = Column(Text, nullable=True)
    
    # Key metadata
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    prefix = Column(String(10), nullable=False)  # First few characters for identification
    
    # Key status and permissions
    is_active = Column(Boolean, default=True, nullable=False)
    permissions = Column(JSON, nullable=True)  # Store specific permissions for this key
    
    # Usage tracking
    last_used = Column(DateTime(timezone=True), nullable=True)
    usage_count = Column(Integer, default=0)
    
    # Expiration
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="api_keys")
    
    # Indexes
    __table_args__ = (
        Index('idx_api_keys_hash', 'key_hash'),
        Index('idx_api_keys_user_id', 'user_id'),
        Index('idx_api_keys_active', 'is_active'),
        Index('idx_api_keys_expires_at', 'expires_at'),
    )
    
    def __repr__(self):
        return f"<APIKey(id={self.id}, name='{self.name}', prefix='{self.prefix}')>"
    
    def is_expired(self) -> bool:
        """Check if the API key is expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at


class JWTToken(Base):
    """JWT token model for token blacklisting and tracking."""
    
    __tablename__ = 'jwt_tokens'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token_hash = Column(String(255), unique=True, nullable=False, index=True)
    jti = Column(String(100), unique=True, nullable=False, index=True)  # JWT ID
    token_type = Column(String(20), nullable=False)  # 'access' or 'refresh'
    
    # Token metadata
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    
    # Token status
    is_blacklisted = Column(Boolean, default=False, nullable=False)
    blacklisted_at = Column(DateTime(timezone=True), nullable=True)
    blacklist_reason = Column(String(255), nullable=True)
    
    # Token lifecycle
    issued_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
    # Usage tracking
    last_used = Column(DateTime(timezone=True), nullable=True)
    usage_count = Column(Integer, default=0)
    
    # Client information
    client_ip = Column(String(45), nullable=True)  # IPv6 support
    user_agent = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="jwt_tokens")
    
    # Indexes
    __table_args__ = (
        Index('idx_jwt_tokens_hash', 'token_hash'),
        Index('idx_jwt_tokens_jti', 'jti'),
        Index('idx_jwt_tokens_user_id', 'user_id'),
        Index('idx_jwt_tokens_blacklisted', 'is_blacklisted'),
        Index('idx_jwt_tokens_expires_at', 'expires_at'),
        Index('idx_jwt_tokens_type', 'token_type'),
    )
    
    def __repr__(self):
        return f"<JWTToken(id={self.id}, jti='{self.jti}', type='{self.token_type}')>"
    
    def is_expired(self) -> bool:
        """Check if the JWT token is expired."""
        return datetime.utcnow() > self.expires_at
    
    def blacklist(self, reason: str = None) -> None:
        """Blacklist this token."""
        self.is_blacklisted = True
        self.blacklisted_at = datetime.utcnow()
        self.blacklist_reason = reason or "Manually blacklisted"


class LoginSession(Base):
    """Login session model for session management."""
    
    __tablename__ = 'login_sessions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    
    # Session metadata
    client_ip = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    # Session status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Session lifecycle
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    last_activity = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="login_sessions")
    
    # Indexes
    __table_args__ = (
        Index('idx_login_sessions_token', 'session_token'),
        Index('idx_login_sessions_user_id', 'user_id'),
        Index('idx_login_sessions_active', 'is_active'),
        Index('idx_login_sessions_expires_at', 'expires_at'),
    )
    
    def __repr__(self):
        return f"<LoginSession(id={self.id}, user_id={self.user_id})>"
    
    def is_expired(self) -> bool:
        """Check if the session is expired."""
        return datetime.utcnow() > self.expires_at
    
    def update_activity(self) -> None:
        """Update the last activity timestamp."""
        self.last_activity = datetime.utcnow()


# Database utility functions
def create_default_roles(session: Session) -> None:
    """Create default system roles."""
    default_roles = [
        {"name": "admin", "display_name": "Administrator", "description": "Full system access", "is_system": True},
        {"name": "user", "display_name": "User", "description": "Standard user access", "is_system": True},
        {"name": "readonly", "display_name": "Read Only", "description": "Read-only access", "is_system": True},
    ]
    
    for role_data in default_roles:
        existing_role = session.query(Role).filter_by(name=role_data["name"]).first()
        if not existing_role:
            role = Role(**role_data)
            session.add(role)
    
    session.commit()


def create_default_permissions(session: Session) -> None:
    """Create default system permissions."""
    default_permissions = [
        {"name": "read", "display_name": "Read", "description": "Read access to resources"},
        {"name": "write", "display_name": "Write", "description": "Write access to resources"},
        {"name": "admin", "display_name": "Admin", "description": "Administrative access"},
        {"name": "execute", "display_name": "Execute", "description": "Execute operations"},
    ]
    
    for perm_data in default_permissions:
        existing_perm = session.query(PermissionModel).filter_by(name=perm_data["name"]).first()
        if not existing_perm:
            permission = PermissionModel(**perm_data)
            session.add(permission)
    
    session.commit()


def setup_default_rbac(session: Session) -> None:
    """Set up default role-based access control."""
    create_default_permissions(session)
    create_default_roles(session)
    
    # Assign permissions to roles
    admin_role = session.query(Role).filter_by(name="admin").first()
    user_role = session.query(Role).filter_by(name="user").first()
    readonly_role = session.query(Role).filter_by(name="readonly").first()
    
    read_perm = session.query(PermissionModel).filter_by(name="read").first()
    write_perm = session.query(PermissionModel).filter_by(name="write").first()
    admin_perm = session.query(PermissionModel).filter_by(name="admin").first()
    execute_perm = session.query(PermissionModel).filter_by(name="execute").first()
    
    if admin_role and admin_perm and read_perm and write_perm and execute_perm:
        admin_role.permissions = [read_perm, write_perm, admin_perm, execute_perm]
    
    if user_role and read_perm and write_perm:
        user_role.permissions = [read_perm, write_perm]
    
    if readonly_role and read_perm:
        readonly_role.permissions = [read_perm]
    
    session.commit()