"""
Database Models for LeanVibe Agent Hive External API

Provides SQLAlchemy models for users, roles, permissions, and audit logging
supporting the RBAC framework and authentication systems.
"""

import uuid
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Set
from enum import Enum

from sqlalchemy import (
    Column, String, Integer, DateTime, Boolean, Text, JSON,
    ForeignKey, Table, Index, UniqueConstraint, Enum as SQLEnum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Session
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

# Create the base class for all models
Base = declarative_base()


class ResourceType(Enum):
    """Enum for resource types in the RBAC system."""
    API_ENDPOINT = "api_endpoint"
    DATABASE = "database"
    FILE_SYSTEM = "file_system"
    SERVICE = "service"
    AGENT = "agent"
    WORKFLOW = "workflow"
    MONITORING = "monitoring"
    CONFIGURATION = "configuration"


class ActionType(Enum):
    """Enum for action types in the RBAC system."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    ADMIN = "admin"
    CONFIGURE = "configure"
    MONITOR = "monitor"
    DEPLOY = "deploy"
    SCALE = "scale"


class PermissionScope(Enum):
    """Enum for permission scopes in the RBAC system."""
    GLOBAL = "global"
    ORGANIZATION = "organization"
    PROJECT = "project"
    RESOURCE = "resource"
    INSTANCE = "instance"


# Association tables for many-to-many relationships
user_roles = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id'), primary_key=True),
    Column('role_id', UUID(as_uuid=True), ForeignKey('roles.id'), primary_key=True)
)

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
    username = Column(String(80), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(200), nullable=True)
    
    # User status
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    user_metadata = Column(JSON, nullable=True)
    
    # Relationships
    roles = relationship("Role", secondary=user_roles, back_populates="users")
    jwt_tokens = relationship("JWTToken", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")
    
    # Indexes
    __table_args__ = (
        Index('idx_users_username', 'username'),
        Index('idx_users_email', 'email'),
        Index('idx_users_active', 'is_active'),
        Index('idx_users_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary."""
        return {
            'id': str(self.id),
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'is_active': self.is_active,
            'is_admin': self.is_admin,
            'is_verified': self.is_verified,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'metadata': self.user_metadata or {}
        }
    
    def has_role(self, role_name: str) -> bool:
        """Check if user has a specific role."""
        return any(role.name == role_name for role in self.roles)
    
    def has_permission(self, permission_name: str) -> bool:
        """Check if user has a specific permission through roles."""
        for role in self.roles:
            if role.has_permission(permission_name):
                return True
        return False


class Role(Base):
    """Role model for RBAC system."""
    
    __tablename__ = 'roles'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(80), unique=True, nullable=False)
    display_name = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    
    # Role status
    is_active = Column(Boolean, default=True, nullable=False)
    is_system = Column(Boolean, default=False, nullable=False)
    
    # Hierarchy support
    parent_role_names = Column(JSON, nullable=True)
    child_role_names = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Metadata
    role_metadata = Column(JSON, nullable=True)
    
    # Relationships
    users = relationship("User", secondary=user_roles, back_populates="roles")
    permissions = relationship("PermissionModel", secondary=role_permissions, back_populates="roles")
    
    # Indexes
    __table_args__ = (
        Index('idx_roles_name', 'name'),
        Index('idx_roles_active', 'is_active'),
        Index('idx_roles_system', 'is_system'),
    )
    
    def __repr__(self):
        return f"<Role(id={self.id}, name='{self.name}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert role to dictionary."""
        return {
            'id': str(self.id),
            'name': self.name,
            'display_name': self.display_name,
            'description': self.description,
            'is_active': self.is_active,
            'is_system': self.is_system,
            'parent_role_names': self.parent_role_names or [],
            'child_role_names': self.child_role_names or [],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'metadata': self.role_metadata or {}
        }
    
    def has_permission(self, permission_name: str) -> bool:
        """Check if role has a specific permission."""
        return any(perm.name == permission_name for perm in self.permissions)


class PermissionModel(Base):
    """Permission model for RBAC system."""
    
    __tablename__ = 'permissions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), unique=True, nullable=False)
    display_name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    
    # Permission components
    resource_type = Column(SQLEnum(ResourceType), nullable=False)
    action_type = Column(SQLEnum(ActionType), nullable=False)
    scope = Column(SQLEnum(PermissionScope), nullable=False)
    resource_id = Column(String(100), nullable=True)
    
    # Conditions and constraints
    conditions = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Metadata
    permission_metadata = Column(JSON, nullable=True)
    
    # Relationships
    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")
    
    # Indexes
    __table_args__ = (
        Index('idx_permissions_name', 'name'),
        Index('idx_permissions_resource_type', 'resource_type'),
        Index('idx_permissions_action_type', 'action_type'),
        Index('idx_permissions_scope', 'scope'),
        Index('idx_permissions_composite', 'resource_type', 'action_type', 'scope'),
    )
    
    def __repr__(self):
        return f"<PermissionModel(id={self.id}, name='{self.name}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert permission to dictionary."""
        return {
            'id': str(self.id),
            'name': self.name,
            'display_name': self.display_name,
            'description': self.description,
            'resource_type': self.resource_type.value,
            'action_type': self.action_type.value,
            'scope': self.scope.value,
            'resource_id': self.resource_id,
            'conditions': self.conditions or {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'metadata': self.permission_metadata or {}
        }
    
    def to_rbac_permission(self):
        """Convert to RBAC framework permission object."""
        from .rbac_framework import Permission
        return Permission(
            resource_type=self.resource_type,
            action=self.action_type,
            scope=self.scope,
            resource_id=self.resource_id,
            conditions=self.conditions or {}
        )


class JWTToken(Base):
    """JWT Token model for authentication."""
    
    __tablename__ = 'jwt_tokens'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    token_hash = Column(String(255), nullable=False)
    token_type = Column(String(50), default='access', nullable=False)  # access, refresh
    
    # Token metadata
    client_id = Column(String(100), nullable=True)
    client_ip = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    # Token lifecycle
    issued_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    is_revoked = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="jwt_tokens")
    
    # Indexes
    __table_args__ = (
        Index('idx_jwt_tokens_user_id', 'user_id'),
        Index('idx_jwt_tokens_token_hash', 'token_hash'),
        Index('idx_jwt_tokens_expires_at', 'expires_at'),
        Index('idx_jwt_tokens_is_revoked', 'is_revoked'),
    )
    
    def __repr__(self):
        return f"<JWTToken(id={self.id}, user_id={self.user_id}, type='{self.token_type}')>"
    
    def is_valid(self) -> bool:
        """Check if token is valid (not expired and not revoked)."""
        if self.is_revoked or self.revoked_at:
            return False
        if datetime.utcnow() > self.expires_at:
            return False
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert token to dictionary."""
        return {
            'id': str(self.id),
            'user_id': str(self.user_id),
            'token_type': self.token_type,
            'client_id': self.client_id,
            'client_ip': self.client_ip,
            'issued_at': self.issued_at.isoformat() if self.issued_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'revoked_at': self.revoked_at.isoformat() if self.revoked_at else None,
            'is_revoked': self.is_revoked,
            'is_valid': self.is_valid()
        }


class AuditLog(Base):
    """Audit log model for tracking authorization decisions."""
    
    __tablename__ = 'audit_logs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    
    # Request details
    resource_type = Column(SQLEnum(ResourceType), nullable=False)
    action = Column(SQLEnum(ActionType), nullable=False)
    resource_id = Column(String(100), nullable=True)
    
    # Authorization result
    authorized = Column(Boolean, nullable=False)
    reason = Column(Text, nullable=True)
    permissions_used = Column(JSON, nullable=True)
    
    # Context information
    client_ip = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    request_context = Column(JSON, nullable=True)
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")
    
    # Indexes
    __table_args__ = (
        Index('idx_audit_logs_user_id', 'user_id'),
        Index('idx_audit_logs_resource_type', 'resource_type'),
        Index('idx_audit_logs_action', 'action'),
        Index('idx_audit_logs_authorized', 'authorized'),
        Index('idx_audit_logs_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, user_id={self.user_id}, authorized={self.authorized})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert audit log to dictionary."""
        return {
            'id': str(self.id),
            'user_id': str(self.user_id),
            'resource_type': self.resource_type.value,
            'action': self.action.value,
            'resource_id': self.resource_id,
            'authorized': self.authorized,
            'reason': self.reason,
            'permissions_used': self.permissions_used or [],
            'client_ip': self.client_ip,
            'user_agent': self.user_agent,
            'request_context': self.request_context or {},
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# Utility functions for setting up default RBAC
def create_default_roles(session: Session) -> None:
    """Create default system roles."""
    default_roles = [
        {
            'name': 'super_admin',
            'display_name': 'Super Administrator',
            'description': 'Super administrator with all permissions',
            'is_system': True
        },
        {
            'name': 'admin',
            'display_name': 'Administrator',
            'description': 'Administrator with most permissions',
            'is_system': True,
            'parent_role_names': ['super_admin']
        },
        {
            'name': 'developer',
            'display_name': 'Developer',
            'description': 'Developer with development permissions',
            'is_system': True,
            'parent_role_names': ['admin']
        },
        {
            'name': 'operator',
            'display_name': 'Operator',
            'description': 'Operations team with deployment permissions',
            'is_system': True,
            'parent_role_names': ['admin']
        },
        {
            'name': 'readonly',
            'display_name': 'Read Only',
            'description': 'Read-only access to resources',
            'is_system': True,
            'parent_role_names': ['developer', 'operator']
        }
    ]
    
    for role_data in default_roles:
        existing_role = session.query(Role).filter_by(name=role_data['name']).first()
        if not existing_role:
            role = Role(**role_data)
            session.add(role)
    
    session.commit()


def create_default_permissions(session: Session) -> None:
    """Create default system permissions."""
    permissions = []
    
    # Create comprehensive permissions for each resource type and action
    for resource_type in ResourceType:
        for action_type in ActionType:
            for scope in PermissionScope:
                permission_name = f"{resource_type.value}:{action_type.value}:{scope.value}"
                
                permissions.append({
                    'name': permission_name,
                    'display_name': f"{action_type.value.title()} {resource_type.value.replace('_', ' ').title()} ({scope.value.title()})",
                    'description': f"Permission to {action_type.value} {resource_type.value} at {scope.value} scope",
                    'resource_type': resource_type,
                    'action_type': action_type,
                    'scope': scope
                })
    
    # Create permissions in batches to avoid memory issues
    for perm_data in permissions:
        existing_perm = session.query(PermissionModel).filter_by(name=perm_data['name']).first()
        if not existing_perm:
            permission = PermissionModel(**perm_data)
            session.add(permission)
    
    session.commit()


def assign_default_role_permissions(session: Session) -> None:
    """Assign default permissions to roles."""
    # Super admin gets all permissions
    super_admin_role = session.query(Role).filter_by(name='super_admin').first()
    if super_admin_role:
        all_permissions = session.query(PermissionModel).all()
        super_admin_role.permissions = all_permissions
    
    # Admin gets most permissions (excluding super admin permissions)
    admin_role = session.query(Role).filter_by(name='admin').first()
    if admin_role:
        admin_permissions = session.query(PermissionModel).filter(
            PermissionModel.action_type.in_([ActionType.CREATE, ActionType.READ, ActionType.UPDATE, ActionType.DELETE])
        ).all()
        admin_role.permissions = admin_permissions
    
    # Developer gets development-related permissions
    developer_role = session.query(Role).filter_by(name='developer').first()
    if developer_role:
        dev_permissions = session.query(PermissionModel).filter(
            PermissionModel.resource_type.in_([ResourceType.API_ENDPOINT, ResourceType.SERVICE, ResourceType.AGENT]),
            PermissionModel.action_type.in_([ActionType.READ, ActionType.UPDATE, ActionType.EXECUTE])
        ).all()
        developer_role.permissions = dev_permissions
    
    # Operator gets deployment and monitoring permissions
    operator_role = session.query(Role).filter_by(name='operator').first()
    if operator_role:
        op_permissions = session.query(PermissionModel).filter(
            PermissionModel.resource_type.in_([ResourceType.SERVICE, ResourceType.MONITORING]),
            PermissionModel.action_type.in_([ActionType.DEPLOY, ActionType.MONITOR, ActionType.SCALE])
        ).all()
        operator_role.permissions = op_permissions
    
    # Read-only gets read permissions
    readonly_role = session.query(Role).filter_by(name='readonly').first()
    if readonly_role:
        read_permissions = session.query(PermissionModel).filter(
            PermissionModel.action_type == ActionType.READ
        ).all()
        readonly_role.permissions = read_permissions
    
    session.commit()


def setup_default_rbac(session: Session) -> None:
    """Set up default RBAC system with roles and permissions."""
    create_default_roles(session)
    create_default_permissions(session)
    assign_default_role_permissions(session)
    
    print("Default RBAC system setup completed!")
    print(f"Created roles: {session.query(Role).count()}")
    print(f"Created permissions: {session.query(PermissionModel).count()}")


# Cleanup functions
def cleanup_expired_tokens(session: Session) -> int:
    """Clean up expired JWT tokens."""
    expired_count = session.query(JWTToken).filter(
        JWTToken.expires_at < datetime.utcnow()
    ).delete()
    
    session.commit()
    return expired_count


def cleanup_old_audit_logs(session: Session, days: int = 90) -> int:
    """Clean up old audit logs."""
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    deleted_count = session.query(AuditLog).filter(
        AuditLog.created_at < cutoff_date
    ).delete()
    
    session.commit()
    return deleted_count