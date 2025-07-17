"""
Enhanced Database Models for RBAC Framework Integration

Extends the security agent's database models to support the comprehensive RBAC framework
with ResourceType/ActionType granular permissions, hierarchical roles, and permission scopes.
"""

import uuid
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Set

from sqlalchemy import (
    Column, String, Integer, DateTime, Boolean, Text, JSON, 
    ForeignKey, Table, Index, UniqueConstraint, Enum as SQLEnum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Session
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import enum

# Import Security Agent's base models
import sys
sys.path.append('../security-Jul-17-0944')
from external_api.database_models import Base, User as SecurityUser, Role as SecurityRole, PermissionModel

# Import our RBAC enums
from .rbac_framework import ResourceType, ActionType, PermissionScope

# Extend the base from security agent
Base = Base


class ResourceTypeEnum(enum.Enum):
    """Database enum for ResourceType."""
    API_ENDPOINT = "api_endpoint"
    DATABASE = "database"
    FILE_SYSTEM = "file_system"
    SERVICE = "service"
    AGENT = "agent"
    WORKFLOW = "workflow"
    MONITORING = "monitoring"
    CONFIGURATION = "configuration"


class ActionTypeEnum(enum.Enum):
    """Database enum for ActionType."""
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


class PermissionScopeEnum(enum.Enum):
    """Database enum for PermissionScope."""
    GLOBAL = "global"
    ORGANIZATION = "organization"
    PROJECT = "project"
    RESOURCE = "resource"
    INSTANCE = "instance"


# Association tables for many-to-many relationships
role_hierarchy = Table(
    'role_hierarchy',
    Base.metadata,
    Column('parent_role_id', UUID(as_uuid=True), ForeignKey('enhanced_roles.id'), primary_key=True),
    Column('child_role_id', UUID(as_uuid=True), ForeignKey('enhanced_roles.id'), primary_key=True)
)

user_direct_permissions = Table(
    'user_direct_permissions',
    Base.metadata,
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id'), primary_key=True),
    Column('permission_id', UUID(as_uuid=True), ForeignKey('enhanced_permissions.id'), primary_key=True)
)

enhanced_role_permissions = Table(
    'enhanced_role_permissions',
    Base.metadata,
    Column('role_id', UUID(as_uuid=True), ForeignKey('enhanced_roles.id'), primary_key=True),
    Column('permission_id', UUID(as_uuid=True), ForeignKey('enhanced_permissions.id'), primary_key=True)
)


class EnhancedRole(Base):
    """Enhanced Role model with hierarchy support."""
    
    __tablename__ = 'enhanced_roles'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False)
    display_name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    
    # Role status
    is_active = Column(Boolean, default=True, nullable=False)
    is_system = Column(Boolean, default=False, nullable=False)
    
    # Hierarchy metadata
    hierarchy_level = Column(Integer, default=0)  # For optimization
    hierarchy_path = Column(String(500), nullable=True)  # Materialized path
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Metadata
    metadata = Column(JSON, nullable=True)
    
    # Relationships
    users = relationship("SecurityUser", secondary="user_roles", back_populates="roles")
    permissions = relationship("EnhancedPermission", secondary=enhanced_role_permissions, back_populates="roles")
    
    # Hierarchy relationships
    parent_roles = relationship(
        "EnhancedRole",
        secondary=role_hierarchy,
        primaryjoin=id == role_hierarchy.c.child_role_id,
        secondaryjoin=id == role_hierarchy.c.parent_role_id,
        backref="child_roles"
    )
    
    # Indexes
    __table_args__ = (
        Index('idx_enhanced_roles_name', 'name'),
        Index('idx_enhanced_roles_active', 'is_active'),
        Index('idx_enhanced_roles_system', 'is_system'),
        Index('idx_enhanced_roles_hierarchy_level', 'hierarchy_level'),
        Index('idx_enhanced_roles_hierarchy_path', 'hierarchy_path'),
    )
    
    def __repr__(self):
        return f"<EnhancedRole(id={self.id}, name='{self.name}')>"
    
    def get_all_permissions(self, session: Session) -> List['EnhancedPermission']:
        """Get all permissions including inherited ones."""
        permissions = set(self.permissions)
        
        # Get permissions from parent roles
        for parent in self.parent_roles:
            permissions.update(parent.get_all_permissions(session))
        
        return list(permissions)
    
    def get_hierarchy_roles(self, session: Session) -> Set['EnhancedRole']:
        """Get all roles in the hierarchy."""
        roles = {self}
        
        for parent in self.parent_roles:
            roles.update(parent.get_hierarchy_roles(session))
        
        return roles
    
    def update_hierarchy_path(self, session: Session) -> None:
        """Update materialized path for hierarchy optimization."""
        if not self.parent_roles:
            self.hierarchy_path = self.name
            self.hierarchy_level = 0
        else:
            # Use the shortest path to root
            min_level = float('inf')
            best_path = ""
            
            for parent in self.parent_roles:
                if parent.hierarchy_level < min_level:
                    min_level = parent.hierarchy_level
                    best_path = f"{parent.hierarchy_path}.{self.name}"
            
            self.hierarchy_path = best_path
            self.hierarchy_level = min_level + 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': str(self.id),
            'name': self.name,
            'display_name': self.display_name,
            'description': self.description,
            'is_active': self.is_active,
            'is_system': self.is_system,
            'hierarchy_level': self.hierarchy_level,
            'hierarchy_path': self.hierarchy_path,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'metadata': self.metadata or {}
        }


class EnhancedPermission(Base):
    """Enhanced Permission model with granular resource control."""
    
    __tablename__ = 'enhanced_permissions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), unique=True, nullable=False)  # Generated from components
    display_name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    
    # Permission components
    resource_type = Column(SQLEnum(ResourceTypeEnum), nullable=False)
    action = Column(SQLEnum(ActionTypeEnum), nullable=False)
    scope = Column(SQLEnum(PermissionScopeEnum), nullable=False)
    resource_id = Column(String(100), nullable=True)  # Specific resource identifier
    
    # Conditions and constraints
    conditions = Column(JSON, nullable=True)  # Additional conditions
    constraints = Column(JSON, nullable=True)  # Resource constraints
    
    # Expiration
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Metadata
    metadata = Column(JSON, nullable=True)
    
    # Relationships
    roles = relationship("EnhancedRole", secondary=enhanced_role_permissions, back_populates="permissions")
    users = relationship("SecurityUser", secondary=user_direct_permissions, back_populates="direct_permissions")
    
    # Indexes
    __table_args__ = (
        Index('idx_enhanced_permissions_name', 'name'),
        Index('idx_enhanced_permissions_resource_type', 'resource_type'),
        Index('idx_enhanced_permissions_action', 'action'),
        Index('idx_enhanced_permissions_scope', 'scope'),
        Index('idx_enhanced_permissions_resource_id', 'resource_id'),
        Index('idx_enhanced_permissions_expires_at', 'expires_at'),
        Index('idx_enhanced_permissions_composite', 'resource_type', 'action', 'scope', 'resource_id'),
        UniqueConstraint('resource_type', 'action', 'scope', 'resource_id', 'conditions', name='uq_permission_components'),
    )
    
    def __repr__(self):
        return f"<EnhancedPermission(id={self.id}, name='{self.name}')>"
    
    def is_valid(self) -> bool:
        """Check if permission is still valid."""
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        return True
    
    def matches_request(self, resource_type: ResourceType, action: ActionType, 
                       resource_id: Optional[str] = None, 
                       context: Optional[Dict[str, Any]] = None) -> bool:
        """Check if this permission matches a request."""
        if not self.is_valid():
            return False
        
        # Check resource type
        if self.resource_type.value != resource_type.value:
            return False
        
        # Check action
        if self.action.value != action.value:
            return False
        
        # Check resource ID (wildcard or exact match)
        if self.resource_id and self.resource_id != "*" and self.resource_id != resource_id:
            return False
        
        # Check conditions
        if context and self.conditions:
            for condition_key, condition_value in self.conditions.items():
                if condition_key not in context or context[condition_key] != condition_value:
                    return False
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': str(self.id),
            'name': self.name,
            'display_name': self.display_name,
            'description': self.description,
            'resource_type': self.resource_type.value,
            'action': self.action.value,
            'scope': self.scope.value,
            'resource_id': self.resource_id,
            'conditions': self.conditions or {},
            'constraints': self.constraints or {},
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'metadata': self.metadata or {}
        }
    
    @classmethod
    def generate_name(cls, resource_type: ResourceType, action: ActionType, 
                     scope: PermissionScope, resource_id: Optional[str] = None) -> str:
        """Generate permission name from components."""
        parts = [resource_type.value, action.value, scope.value]
        if resource_id:
            parts.append(resource_id)
        return ":".join(parts)


class PermissionCache(Base):
    """Cache table for permission evaluation results."""
    
    __tablename__ = 'permission_cache'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cache_key = Column(String(500), unique=True, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    
    # Cached result
    allowed = Column(Boolean, nullable=False)
    permissions_used = Column(JSON, nullable=True)
    
    # Cache metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    hit_count = Column(Integer, default=0)
    
    # Relationships
    user = relationship("SecurityUser")
    
    # Indexes
    __table_args__ = (
        Index('idx_permission_cache_key', 'cache_key'),
        Index('idx_permission_cache_user_id', 'user_id'),
        Index('idx_permission_cache_expires_at', 'expires_at'),
    )
    
    def __repr__(self):
        return f"<PermissionCache(id={self.id}, key='{self.cache_key}')>"
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        return datetime.utcnow() > self.expires_at


class AuditLog(Base):
    """Audit log for authorization decisions."""
    
    __tablename__ = 'audit_logs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    
    # Request details
    resource_type = Column(SQLEnum(ResourceTypeEnum), nullable=False)
    action = Column(SQLEnum(ActionTypeEnum), nullable=False)
    resource_id = Column(String(100), nullable=True)
    
    # Authorization result
    authorized = Column(Boolean, nullable=False)
    reason = Column(Text, nullable=True)
    permissions_used = Column(JSON, nullable=True)
    
    # Context information
    client_ip = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    request_context = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("SecurityUser")
    
    # Indexes
    __table_args__ = (
        Index('idx_audit_logs_user_id', 'user_id'),
        Index('idx_audit_logs_resource_type', 'resource_type'),
        Index('idx_audit_logs_action', 'action'),
        Index('idx_audit_logs_authorized', 'authorized'),
        Index('idx_audit_logs_created_at', 'created_at'),
        Index('idx_audit_logs_composite', 'user_id', 'resource_type', 'action', 'created_at'),
    )
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, user_id={self.user_id}, authorized={self.authorized})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
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


# Extend the SecurityUser model with additional relationships
SecurityUser.direct_permissions = relationship(
    "EnhancedPermission", 
    secondary=user_direct_permissions, 
    back_populates="users"
)

SecurityUser.enhanced_roles = relationship(
    "EnhancedRole", 
    secondary="user_roles", 
    back_populates="users"
)


# Database utility functions
def create_enhanced_system_roles(session: Session) -> None:
    """Create enhanced system roles with hierarchy."""
    
    # Create system roles
    system_roles = [
        {
            "name": "super_admin",
            "display_name": "Super Administrator",
            "description": "Super administrator with all permissions",
            "is_system": True,
            "hierarchy_level": 0,
            "hierarchy_path": "super_admin"
        },
        {
            "name": "admin",
            "display_name": "Administrator",
            "description": "Administrator with most permissions",
            "is_system": True,
            "hierarchy_level": 1,
            "hierarchy_path": "super_admin.admin"
        },
        {
            "name": "developer",
            "display_name": "Developer",
            "description": "Developer with development permissions",
            "is_system": True,
            "hierarchy_level": 2,
            "hierarchy_path": "super_admin.admin.developer"
        },
        {
            "name": "operator",
            "display_name": "Operator",
            "description": "Operations team with deployment permissions",
            "is_system": True,
            "hierarchy_level": 2,
            "hierarchy_path": "super_admin.admin.operator"
        },
        {
            "name": "viewer",
            "display_name": "Viewer",
            "description": "Read-only access to most resources",
            "is_system": True,
            "hierarchy_level": 3,
            "hierarchy_path": "super_admin.admin.developer.viewer"
        }
    ]
    
    role_objects = {}
    
    for role_data in system_roles:
        existing_role = session.query(EnhancedRole).filter_by(name=role_data["name"]).first()
        if not existing_role:
            role = EnhancedRole(**role_data)
            session.add(role)
            session.flush()  # Get the ID
            role_objects[role_data["name"]] = role
        else:
            role_objects[role_data["name"]] = existing_role
    
    # Set up hierarchy
    role_objects["admin"].parent_roles = [role_objects["super_admin"]]
    role_objects["developer"].parent_roles = [role_objects["admin"]]
    role_objects["operator"].parent_roles = [role_objects["admin"]]
    role_objects["viewer"].parent_roles = [role_objects["developer"], role_objects["operator"]]
    
    session.commit()


def create_enhanced_system_permissions(session: Session) -> None:
    """Create enhanced system permissions."""
    
    # Create comprehensive permissions
    permissions = []
    
    # Super admin permissions
    for resource_type in ResourceTypeEnum:
        permissions.append({
            "resource_type": resource_type,
            "action": ActionTypeEnum.ADMIN,
            "scope": PermissionScopeEnum.GLOBAL,
            "name": f"{resource_type.value}:admin:global"
        })
    
    # Admin permissions
    for resource_type in ResourceTypeEnum:
        for action in [ActionTypeEnum.READ, ActionTypeEnum.UPDATE, ActionTypeEnum.CREATE]:
            permissions.append({
                "resource_type": resource_type,
                "action": action,
                "scope": PermissionScopeEnum.GLOBAL,
                "name": f"{resource_type.value}:{action.value}:global"
            })
    
    # Developer permissions
    for resource_type in [ResourceTypeEnum.API_ENDPOINT, ResourceTypeEnum.SERVICE, 
                         ResourceTypeEnum.AGENT, ResourceTypeEnum.WORKFLOW]:
        for action in [ActionTypeEnum.READ, ActionTypeEnum.UPDATE, ActionTypeEnum.EXECUTE]:
            permissions.append({
                "resource_type": resource_type,
                "action": action,
                "scope": PermissionScopeEnum.PROJECT,
                "name": f"{resource_type.value}:{action.value}:project"
            })
    
    # Operator permissions
    for resource_type in [ResourceTypeEnum.SERVICE, ResourceTypeEnum.MONITORING, 
                         ResourceTypeEnum.CONFIGURATION]:
        for action in [ActionTypeEnum.DEPLOY, ActionTypeEnum.SCALE, ActionTypeEnum.CONFIGURE]:
            permissions.append({
                "resource_type": resource_type,
                "action": action,
                "scope": PermissionScopeEnum.GLOBAL,
                "name": f"{resource_type.value}:{action.value}:global"
            })
    
    # Viewer permissions
    for resource_type in ResourceTypeEnum:
        permissions.append({
            "resource_type": resource_type,
            "action": ActionTypeEnum.READ,
            "scope": PermissionScopeEnum.PROJECT,
            "name": f"{resource_type.value}:read:project"
        })
    
    # Create permissions
    for perm_data in permissions:
        existing_perm = session.query(EnhancedPermission).filter_by(name=perm_data["name"]).first()
        if not existing_perm:
            permission = EnhancedPermission(**perm_data)
            session.add(permission)
    
    session.commit()


def setup_enhanced_rbac(session: Session) -> None:
    """Set up enhanced RBAC with roles and permissions."""
    create_enhanced_system_permissions(session)
    create_enhanced_system_roles(session)
    
    # Assign permissions to roles
    super_admin_role = session.query(EnhancedRole).filter_by(name="super_admin").first()
    admin_role = session.query(EnhancedRole).filter_by(name="admin").first()
    developer_role = session.query(EnhancedRole).filter_by(name="developer").first()
    operator_role = session.query(EnhancedRole).filter_by(name="operator").first()
    viewer_role = session.query(EnhancedRole).filter_by(name="viewer").first()
    
    # Super admin gets all admin permissions
    if super_admin_role:
        admin_perms = session.query(EnhancedPermission).filter(
            EnhancedPermission.action == ActionTypeEnum.ADMIN,
            EnhancedPermission.scope == PermissionScopeEnum.GLOBAL
        ).all()
        super_admin_role.permissions = admin_perms
    
    # Admin gets global read/update/create permissions
    if admin_role:
        admin_perms = session.query(EnhancedPermission).filter(
            EnhancedPermission.action.in_([ActionTypeEnum.READ, ActionTypeEnum.UPDATE, ActionTypeEnum.CREATE]),
            EnhancedPermission.scope == PermissionScopeEnum.GLOBAL
        ).all()
        admin_role.permissions = admin_perms
    
    # Developer gets project-level permissions
    if developer_role:
        dev_perms = session.query(EnhancedPermission).filter(
            EnhancedPermission.resource_type.in_([
                ResourceTypeEnum.API_ENDPOINT, ResourceTypeEnum.SERVICE,
                ResourceTypeEnum.AGENT, ResourceTypeEnum.WORKFLOW
            ]),
            EnhancedPermission.action.in_([ActionTypeEnum.READ, ActionTypeEnum.UPDATE, ActionTypeEnum.EXECUTE]),
            EnhancedPermission.scope == PermissionScopeEnum.PROJECT
        ).all()
        developer_role.permissions = dev_perms
    
    # Operator gets deployment and monitoring permissions
    if operator_role:
        op_perms = session.query(EnhancedPermission).filter(
            EnhancedPermission.resource_type.in_([
                ResourceTypeEnum.SERVICE, ResourceTypeEnum.MONITORING,
                ResourceTypeEnum.CONFIGURATION
            ]),
            EnhancedPermission.action.in_([ActionTypeEnum.DEPLOY, ActionTypeEnum.SCALE, ActionTypeEnum.CONFIGURE]),
            EnhancedPermission.scope == PermissionScopeEnum.GLOBAL
        ).all()
        operator_role.permissions = op_perms
    
    # Viewer gets read-only permissions
    if viewer_role:
        view_perms = session.query(EnhancedPermission).filter(
            EnhancedPermission.action == ActionTypeEnum.READ,
            EnhancedPermission.scope == PermissionScopeEnum.PROJECT
        ).all()
        viewer_role.permissions = view_perms
    
    session.commit()


def cleanup_expired_cache(session: Session) -> int:
    """Clean up expired cache entries."""
    expired_count = session.query(PermissionCache).filter(
        PermissionCache.expires_at < datetime.utcnow()
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